"""Enhanced duplicate resolution — no deletions, safe browse suppression only."""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any

from app_skeleton.api.metadata_engine.constants import DUPLICATE_TYPES

_JUNK_RE = re.compile(r"(?:^|/)\.(?:DS_Store|localized)$|thumbs\.db$|~\$", re.I)
_TEMP_RE = re.compile(r"(?:^|/)(?:tmp|temp|cache|\.Trash)(?:/|$)", re.I)
_COPY_RE = re.compile(r"\bcopy\b|\(\d+\)|_v\d+|_old\b|_backup\b", re.I)


def _norm_name(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return re.sub(r"[^a-z0-9]+", "", stem.lower())


def _canonical_score(row: dict[str, Any]) -> int:
    path = (row.get("logical_path") or row.get("original_path") or "").lower()
    score = 0
    ext = row.get("extraction_status") or ""
    if ext in ("extracted", "eligible_text", "indexed"):
        score += 100
    elif ext == "metadata_only":
        score += 60
    md = row.get("metadata_json")
    if isinstance(md, dict) and (md.get("excerpt") or md.get("char_count", 0) > 0):
        score += 40
    score += int(float(row.get("assignment_confidence") or 0) * 20)
    score -= min(len(path) // 12, 30)
    if _JUNK_RE.search(path):
        score -= 300
    if _TEMP_RE.search(path):
        score -= 80
    if _COPY_RE.search(path):
        score -= 25
    if "/archive/" in path and score < 50:
        score -= 15
    if row.get("inventory_active") is False:
        score -= 50
    return score


def build_duplicate_groups(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build exact SHA256 groups + normalized filename groups."""
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_norm_name: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        digest = (row.get("checksum_sha256") or "").strip()
        if digest:
            by_hash[digest].append(row)
        nn = _norm_name(row.get("filename") or "")
        if nn and len(nn) >= 4:
            by_norm_name[nn].append(row)

    plans: list[dict[str, Any]] = []
    review_queue: list[dict[str, Any]] = []
    group_counter = 0

    for digest, group in by_hash.items():
        if len(group) < 2:
            continue
        group_counter += 1
        group_id = f"sha256_{digest[:16]}"
        canonical = max(group, key=lambda r: (_canonical_score(r), -(len(r.get("logical_path") or ""))))
        cid = canonical.get("asset_id")
        paths = [g.get("logical_path") for g in group]

        dup_type = "exact_duplicate"
        risk = "low"
        rec_action = "suppress_duplicates_from_browse"
        safe_suppress = True
        safe_delete = False

        if any(_JUNK_RE.search(p or "") for p in paths):
            dup_type = "system_artifact"
            rec_action = "hide_system_artifacts"
            safe_delete = True
        elif any(_COPY_RE.search(p or "") for p in paths):
            dup_type = "version_variant"
            rec_action = "review_before_suppress"
            safe_suppress = False
            risk = "medium"

        dup_ids = [g.get("asset_id") for g in group if g.get("asset_id") != cid]
        plan = {
            "duplicate_group_id": group_id,
            "canonical_asset_id": cid,
            "duplicate_asset_ids": dup_ids,
            "duplicate_type": dup_type,
            "duplicate_reason": f"{len(group)} files share SHA256 {digest[:12]}…",
            "recommended_action": rec_action,
            "safe_to_suppress_from_browse": safe_suppress,
            "safe_to_delete_after_human_review": safe_delete,
            "keep_reason": f"Best extraction/metadata in {canonical.get('logical_path')}",
            "risk_level": risk,
            "group_size": len(group),
        }
        plans.append(plan)
        if not safe_suppress or risk != "low":
            for d in dup_ids:
                review_queue.append({
                    "asset_id": d,
                    "duplicate_group_id": group_id,
                    "reason": plan["duplicate_reason"],
                    "recommended_action": rec_action,
                })

    # Normalized filename groups (different content)
    for nn, group in by_norm_name.items():
        hashes = {g.get("checksum_sha256") for g in group}
        if len(group) < 2 or len(hashes) == 1:
            continue
        group_counter += 1
        plans.append({
            "duplicate_group_id": f"name_{nn[:20]}",
            "canonical_asset_id": None,
            "duplicate_asset_ids": [g.get("asset_id") for g in group],
            "duplicate_type": "same_name_different_content",
            "duplicate_reason": f"Normalized filename '{nn}' matches {len(group)} distinct files",
            "recommended_action": "human_review",
            "safe_to_suppress_from_browse": False,
            "safe_to_delete_after_human_review": False,
            "keep_reason": "Content differs — not auto-suppressed",
            "risk_level": "high",
            "group_size": len(group),
        })

    return {
        "plans": plans,
        "review_queue": review_queue,
        "exact_groups": sum(1 for p in plans if p["duplicate_type"] == "exact_duplicate"),
        "normalized_name_groups": sum(1 for p in plans if p["duplicate_type"] == "same_name_different_content"),
    }


def plan_lookup_by_asset(plans: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for plan in plans:
        cid = plan.get("canonical_asset_id")
        if cid:
            out[cid] = plan
        for aid in plan.get("duplicate_asset_ids") or []:
            out[aid] = plan
    return out


def apply_duplicate_plan(row: dict[str, Any], plan_by_asset: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Attach duplicate metadata to a single row."""
    aid = row.get("asset_id")
    out: dict[str, Any] = {}
    plan = plan_by_asset.get(aid)
    if plan:
        if plan.get("canonical_asset_id") == aid:
            out.update({
                "duplicate_group_id": plan["duplicate_group_id"],
                "duplicate_type": plan["duplicate_type"],
                "duplicate_action_recommendation": plan["recommended_action"],
                "safe_to_hide_from_browse": False,
                "safe_to_delete_after_review": plan.get("safe_to_delete_after_human_review", False),
            })
        else:
            out.update({
                "duplicate_group_id": plan["duplicate_group_id"],
                "canonical_copy_asset_id": plan.get("canonical_asset_id"),
                "duplicate_type": plan["duplicate_type"],
                "duplicate_action_recommendation": plan["recommended_action"],
                "safe_to_hide_from_browse": plan.get("safe_to_suppress_from_browse", False),
                "safe_to_delete_after_review": plan.get("safe_to_delete_after_human_review", False),
            })

    stored = row.get("duplicate_status") or "unique"
    if stored == "duplicate":
        out.setdefault("duplicate_type", "exact_duplicate")
        out.setdefault("safe_to_hide_from_browse", True)
    elif stored == "canonical":
        out.setdefault("duplicate_type", "exact_duplicate")
    else:
        out.setdefault("duplicate_type", "not_duplicate")

    return out
