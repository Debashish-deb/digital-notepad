from omeia.security.permissions import (
    ensure_authenticated_for_rbac,
    ensure_project_access,
    filter_projects_for_user,
    require_role,
)
from omeia.security.auth import (
    optional_public_user,
    require_platform_user,
    resolve_researcher_id,
)
from omeia.api.platform_flags import project_rbac_enabled
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from omeia.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.get("/projects")
def get_projects(user: Optional[dict] = Depends(optional_public_user)) -> List[Dict[str, Any]]:
    projects = fetch_projects_unified()
    if not project_rbac_enabled():
        return projects
    user = ensure_authenticated_for_rbac(user)
    with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            return filter_projects_for_user(user, projects, cur)

@router.put("/projects/{project_code}")
def update_project(project_code: str, req: ProjectExtensionUpdate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (project_code,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = row[0]
                ensure_project_access(user, project_code, cur=cur)

                # Make sure row exists in project_extension
                cur.execute("INSERT INTO platform.project_extension (project_id) VALUES (%s) ON CONFLICT DO NOTHING;", (pid,))

                # Build update query
                fields = []
                params = []
                for k, v in req.model_dump(exclude_unset=True).items():
                    fields.append(f"{k} = %s")
                    params.append(v)
                params.append(pid)

                if fields:
                    query = f"UPDATE platform.project_extension SET {', '.join(fields)}, updated_at = now() WHERE project_id = %s;"
                    cur.execute(query, tuple(params))

                # Automatically append to the notebook system of record!
                author_id = resolve_researcher_id(cur, user)
                auto_log_notebook_entry(
                    conn, pid, author_id,
                    title=f"Project {project_code} parameters updated",
                    content=f"Researcher updated project extensions: {', '.join(fields)}",
                    entry_type="protocol_deviation_note"
                )
                conn.commit()
                return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/notebook")
def get_notebook(
    project_code: Optional[str] = None,
    user: Optional[dict] = Depends(optional_public_user),
) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                if project_rbac_enabled():
                    user = ensure_authenticated_for_rbac(user)
                    if project_code:
                        ensure_project_access(user, project_code, cur=cur)
                query = """
                    SELECT ne.entry_id, p.project_code, s.sample_code, ne.title, ne.pipeline_stage, ne.content, ne.conclusions, ne.issues_found, ne.next_steps, ne.tags, ne.entry_type, ne.visibility_level, ne.created_at, r.full_name,
                           (SELECT COUNT(*) FROM platform.notebook_revision nr WHERE nr.entry_id = ne.entry_id) as revision_count
                    FROM platform.notebook_entry ne
                    JOIN core.project p ON ne.project_id = p.project_id
                    LEFT JOIN core.sample s ON ne.sample_id = s.sample_id
                    JOIN platform.researcher r ON ne.author_id = r.researcher_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY ne.created_at DESC;"
                
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                if project_rbac_enabled() and user and not project_code:
                    allowed = filter_projects_for_user(
                        user,
                        [{"project_code": r[1]} for r in rows],
                        cur,
                    )
                    allowed_codes = {(p.get("project_code") or "").upper() for p in allowed}
                    rows = [r for r in rows if (r[1] or "").upper() in allowed_codes]
                result = []
                for r in rows:
                    result.append({
                        "entry_id": str(r[0]),
                        "project_code": r[1],
                        "sample_code": r[2],
                        "title": r[3],
                        "pipeline_stage": r[4],
                        "content": r[5],
                        "conclusions": r[6],
                        "issues_found": r[7],
                        "next_steps": r[8],
                        "tags": r[9],
                        "entry_type": r[10],
                        "visibility_level": r[11],
                        "created_at": r[12].isoformat(),
                        "author_name": r[13],
                        "version": r[14]
                    })
                return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/notebook/{entry_id}/revisions")
def get_notebook_revisions(entry_id: str) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT revision_id, revision_number, title, content, created_at
                    FROM platform.notebook_revision
                    WHERE entry_id = %s
                    ORDER BY revision_number DESC;
                """, (entry_id,))
                rows = cur.fetchall()
                return [{
                    "revision_id": str(r[0]),
                    "revision_number": r[1],
                    "title": r[2],
                    "content": r[3],
                    "created_at": r[4].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/notebook")
def create_notebook(req: NotebookEntryCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                p_row = cur.fetchone()
                if not p_row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = p_row[0]
                ensure_project_access(user, req.project_code, cur=cur)

                sid = None
                if req.sample_code:
                    cur.execute("SELECT sample_id FROM core.sample WHERE sample_code = %s;", (req.sample_code,))
                    s_row = cur.fetchone()
                    if s_row:
                        sid = s_row[0]

                author_id = resolve_researcher_id(cur, user)

                entry_id = auto_log_notebook_entry(
                    conn, pid, author_id, req.title, req.content,
                    req.entry_type, sid, req.pipeline_stage
                )

                # Set extra fields if passed
                if req.conclusions or req.issues_found or req.next_steps:
                    cur.execute("""
                        UPDATE platform.notebook_entry
                        SET conclusions = %s, issues_found = %s, next_steps = %s, tags = %s::text[]
                        WHERE entry_id = %s;
                    """, (req.conclusions, req.issues_found, req.next_steps, req.tags, entry_id))

                conn.commit()
                return {"status": "success", "entry_id": str(entry_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.put("/notebook/{entry_id}")
def update_notebook(entry_id: str, req: NotebookEntryUpdate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Get next version number
                cur.execute("SELECT COUNT(*) FROM platform.notebook_revision WHERE entry_id = %s;", (entry_id,))
                rev_count = cur.fetchone()[0]
                new_rev = rev_count + 1

                author_id = resolve_researcher_id(cur, user)

                # Update main table
                cur.execute("""
                    UPDATE platform.notebook_entry
                    SET title = %s, content = %s, conclusions = %s, issues_found = %s, next_steps = %s, tags = %s::text[], entry_type = %s, updated_at = now()
                    WHERE entry_id = %s;
                """, (req.title, req.content, req.conclusions, req.issues_found, req.next_steps, req.tags, req.entry_type, entry_id))

                # Insert revision record
                cur.execute("""
                    INSERT INTO platform.notebook_revision (entry_id, revision_number, title, content, conclusions, issues_found, next_steps, tags, author_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::text[], %s);
                """, (entry_id, new_rev, req.title, req.content, req.conclusions, req.issues_found, req.next_steps, req.tags, author_id))

                conn.commit()
                return {"status": "success", "revision_number": new_rev}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/notebook/{entry_id}/rollback")
def rollback_notebook(entry_id: str, revision_number: int = Query(...)) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, content, conclusions, issues_found, next_steps, tags
                    FROM platform.notebook_revision
                    WHERE entry_id = %s AND revision_number = %s;
                """, (entry_id, revision_number))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Revision not found")

                cur.execute("""
                    UPDATE platform.notebook_entry
                    SET title = %s, content = %s, conclusions = %s, issues_found = %s, next_steps = %s, tags = %s::text[], updated_at = now()
                    WHERE entry_id = %s;
                """, (row[0], row[1], row[2], row[3], row[4], row[5], entry_id))

                conn.commit()
                return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/decisions")
def get_decisions(
    project_code: Optional[str] = None,
    user: dict = Depends(require_platform_user),
) -> List[Dict[str, Any]]:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                if project_rbac_enabled() and project_code:
                    ensure_project_access(user, project_code, cur=cur)
                query = """
                    SELECT d.decision_id, p.project_code, d.title, d.decision_details, d.rationale, d.alternatives_considered, r.full_name, d.decision_date
                    FROM platform.decision_registry d
                    JOIN core.project p ON d.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON d.decided_by_id = r.researcher_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY d.decision_date DESC;"
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "decision_id": str(r[0]),
                    "project_code": r[1],
                    "title": r[2],
                    "decision_details": r[3],
                    "rationale": r[4],
                    "alternatives_considered": r[5],
                    "decider_name": r[6],
                    "decision_date": str(r[7])
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/decisions")
def create_decision(req: DecisionCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                pid_row = cur.fetchone()
                if not pid_row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = pid_row[0]
                ensure_project_access(user, req.project_code, cur=cur)
                rid = resolve_researcher_id(cur, user)

                cur.execute("""
                    INSERT INTO platform.decision_registry (project_id, title, decision_details, rationale, alternatives_considered, decided_by_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING decision_id;
                """, (pid, req.title, req.decision_details, req.rationale, req.alternatives_considered, rid))
                decision_id = cur.fetchone()[0]

                # Automatically log in the notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Decision Logged: {req.title}",
                    content=f"A formal research decision was committed.\nDetails: {req.decision_details}\nRationale: {req.rationale}",
                    entry_type="decision_note"
                )
                conn.commit()
                return {"status": "success", "decision_id": str(decision_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/wiki")
def get_wiki() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT w.wiki_id, w.title, w.slug, w.content, w.wiki_type, p.project_code, r.full_name, w.updated_at,
                           (SELECT COUNT(*) FROM platform.wiki_revision WHERE wiki_id = w.wiki_id) as rev_count
                    FROM platform.research_wiki w
                    LEFT JOIN core.project p ON w.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON w.created_by_id = r.researcher_id
                    ORDER BY w.updated_at DESC;
                """)
                rows = cur.fetchall()
                return [{
                    "wiki_id": str(r[0]),
                    "title": r[1],
                    "slug": r[2],
                    "content": r[3],
                    "wiki_type": r[4],
                    "project_code": r[5],
                    "author_name": r[6],
                    "updated_at": r[7].isoformat(),
                    "revision": r[8] if r[8] > 0 else 1
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/wiki")
def create_wiki_page(req: WikiPageCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pid = None
                if req.project_code:
                    cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                    p_row = cur.fetchone()
                    if not p_row:
                        raise HTTPException(status_code=404, detail="Project not found")
                    pid = p_row[0]
                    ensure_project_access(user, req.project_code, cur=cur)

                rid = resolve_researcher_id(cur, user)

                cur.execute("""
                    INSERT INTO platform.research_wiki (title, slug, content, wiki_type, project_id, created_by_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING wiki_id;
                """, (req.title, req.slug, req.content, req.wiki_type, pid, rid))
                wiki_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO platform.wiki_revision (wiki_id, revision_number, title, content, author_id)
                    VALUES (%s, 1, %s, %s, %s);
                """, (wiki_id, req.title, req.content, rid))

                conn.commit()
                return {"status": "success", "wiki_id": str(wiki_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.put("/wiki/{wiki_id}")
def update_wiki_page(wiki_id: str, req: WikiPageUpdate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Count current versions
                cur.execute("SELECT COUNT(*) FROM platform.wiki_revision WHERE wiki_id = %s;", (wiki_id,))
                count = cur.fetchone()[0]
                new_rev = count + 1

                rid = resolve_researcher_id(cur, user)

                cur.execute("""
                    UPDATE platform.research_wiki
                    SET title = %s, content = %s, wiki_type = %s, updated_at = now()
                    WHERE wiki_id = %s;
                """, (req.title, req.content, req.wiki_type, wiki_id))

                cur.execute("""
                    INSERT INTO platform.wiki_revision (wiki_id, revision_number, title, content, author_id)
                    VALUES (%s, %s, %s, %s, %s);
                """, (wiki_id, new_rev, req.title, req.content, rid))

                conn.commit()
                return {"status": "success", "revision_number": new_rev}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/notebook/search")
def search_notebook(
    q: str = Query(..., min_length=2),
    project_code: Optional[str] = Query(None),
    entry_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Full-text keyword search across notebook entries (title + content + tags)."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pattern = f"%{q}%"
                query = """
                    SELECT ne.entry_id, p.project_code, s.sample_code, ne.title,
                           ne.pipeline_stage, ne.content, ne.conclusions, ne.issues_found,
                           ne.next_steps, ne.tags, ne.entry_type, ne.visibility_level,
                           ne.created_at, r.full_name
                    FROM platform.notebook_entry ne
                    JOIN core.project p ON ne.project_id = p.project_id
                    LEFT JOIN core.sample s ON ne.sample_id = s.sample_id
                    JOIN platform.researcher r ON ne.author_id = r.researcher_id
                    WHERE (
                        ne.title ILIKE %s OR
                        ne.content ILIKE %s OR
                        ne.conclusions ILIKE %s OR
                        ne.issues_found ILIKE %s OR
                        ne.next_steps ILIKE %s OR
                        %s = ANY(ne.tags)
                    )
                """
                params: list = [pattern, pattern, pattern, pattern, pattern, q]
                if project_code:
                    query += " AND p.project_code = %s"
                    params.append(project_code)
                if entry_type:
                    query += " AND ne.entry_type = %s"
                    params.append(entry_type)
                query += " ORDER BY ne.created_at DESC LIMIT %s;"
                params.append(limit)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "entry_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "title": r[3],
                    "pipeline_stage": r[4],
                    "content": r[5],
                    "conclusions": r[6],
                    "issues_found": r[7],
                    "next_steps": r[8],
                    "tags": r[9],
                    "entry_type": r[10],
                    "visibility_level": r[11],
                    "created_at": r[12].isoformat(),
                    "author_name": r[13],
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/notebook/{entry_id}")
def delete_notebook_entry(entry_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Permanently delete a notebook entry and all its revisions."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM platform.notebook_entry WHERE entry_id = %s RETURNING entry_id;", (entry_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Notebook entry not found")
                conn.commit()
                return {"status": "success", "deleted_entry_id": str(row[0])}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/wiki/{wiki_id}/revisions")
def get_wiki_revisions(wiki_id: str) -> List[Dict[str, Any]]:
    """Fetch full version history for a wiki page."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT wr.revision_id, wr.revision_number, wr.title, wr.content, wr.created_at,
                           r.full_name
                    FROM platform.wiki_revision wr
                    LEFT JOIN platform.researcher r ON wr.author_id = r.researcher_id
                    WHERE wr.wiki_id = %s
                    ORDER BY wr.revision_number DESC;
                """, (wiki_id,))
                rows = cur.fetchall()
                return [{
                    "revision_id": str(r[0]),
                    "revision_number": r[1],
                    "title": r[2],
                    "content": r[3],
                    "created_at": r[4].isoformat(),
                    "author_name": r[5],
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/wiki/{wiki_id}/rollback")
def rollback_wiki(
    wiki_id: str,
    revision_number: int = Query(...),
    user: dict = Depends(require_platform_user),
) -> dict:
    """Restore a wiki page to a specific previous revision."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, content
                    FROM platform.wiki_revision
                    WHERE wiki_id = %s AND revision_number = %s;
                """, (wiki_id, revision_number))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Wiki revision not found")

                # Count current revisions to assign next number
                cur.execute("SELECT COUNT(*) FROM platform.wiki_revision WHERE wiki_id = %s;", (wiki_id,))
                next_rev = cur.fetchone()[0] + 1

                rid = resolve_researcher_id(cur, user)

                # Apply rollback to main table
                cur.execute("""
                    UPDATE platform.research_wiki
                    SET title = %s, content = %s, updated_at = now()
                    WHERE wiki_id = %s;
                """, (row[0], row[1], wiki_id))

                # Record rollback as new revision for full auditability
                cur.execute("""
                    INSERT INTO platform.wiki_revision (wiki_id, revision_number, title, content, author_id)
                    VALUES (%s, %s, %s, %s, %s);
                """, (wiki_id, next_rev, row[0], row[1], rid))

                conn.commit()
                return {"status": "success", "restored_revision": revision_number, "new_revision": next_rev}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/wiki/{wiki_id}")
def delete_wiki_page(wiki_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Permanently delete a wiki page and all its revisions."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM platform.research_wiki WHERE wiki_id = %s RETURNING wiki_id;", (wiki_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Wiki page not found")
                conn.commit()
                return {"status": "success", "deleted_wiki_id": str(row[0])}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/wiki/search")
def search_wiki(
    q: str = Query(..., min_length=2),
    wiki_type: Optional[str] = Query(None),
    project_code: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Full-text keyword search across wiki pages (title + content)."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pattern = f"%{q}%"
                query = """
                    SELECT w.wiki_id, w.title, w.slug, w.content, w.wiki_type,
                           p.project_code, r.full_name, w.updated_at
                    FROM platform.research_wiki w
                    LEFT JOIN core.project p ON w.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON w.created_by_id = r.researcher_id
                    WHERE (w.title ILIKE %s OR w.content ILIKE %s)
                """
                params: list = [pattern, pattern]
                if wiki_type:
                    query += " AND w.wiki_type = %s"
                    params.append(wiki_type)
                if project_code:
                    query += " AND p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY w.updated_at DESC LIMIT %s;"
                params.append(limit)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "wiki_id": str(r[0]),
                    "title": r[1],
                    "slug": r[2],
                    "content": r[3],
                    "wiki_type": r[4],
                    "project_code": r[5],
                    "author_name": r[6],
                    "updated_at": r[7].isoformat(),
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/decisions/search")
def search_decisions(
    q: str = Query(..., min_length=2),
    project_code: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Full-text keyword search across the decision registry."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pattern = f"%{q}%"
                query = """
                    SELECT d.decision_id, p.project_code, d.title, d.decision_details,
                           d.rationale, d.alternatives_considered, r.full_name, d.decision_date
                    FROM platform.decision_registry d
                    JOIN core.project p ON d.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON d.decided_by_id = r.researcher_id
                    WHERE (
                        d.title ILIKE %s OR
                        d.decision_details ILIKE %s OR
                        d.rationale ILIKE %s OR
                        d.alternatives_considered ILIKE %s
                    )
                """
                params: list = [pattern, pattern, pattern, pattern]
                if project_code:
                    query += " AND p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY d.decision_date DESC LIMIT %s;"
                params.append(limit)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "decision_id": str(r[0]),
                    "project_code": r[1],
                    "title": r[2],
                    "decision_details": r[3],
                    "rationale": r[4],
                    "alternatives_considered": r[5],
                    "decider_name": r[6],
                    "decision_date": str(r[7]),
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/decisions/{decision_id}")
def delete_decision(decision_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Permanently delete a decision registry entry."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM platform.decision_registry WHERE decision_id = %s RETURNING decision_id;", (decision_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Decision not found")
                conn.commit()
                return {"status": "success", "deleted_decision_id": str(row[0])}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Permanently delete a task."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM platform.task WHERE task_id = %s RETURNING task_id;", (task_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Task not found")
                conn.commit()
                return {"status": "success", "deleted_task_id": str(row[0])}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/platform/search")
def platform_search(
    response: Response,
    q: str = Query(..., min_length=2),
    project_code: Optional[str] = Query(None),
    include: str = Query("notebook,wiki,decisions,tasks", description="Comma-separated: notebook,wiki,decisions,tasks"),
    limit: int = Query(10, ge=1, le=50),
) -> Dict[str, Any]:
    """Unified full-text keyword search across notebook entries, wiki pages, and decisions.

    Proxies to SearchService.unified_search — legacy response shape preserved.
    """
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/platform/unified-search>; rel="successor-version"'

    targets = {t.strip().lower() for t in (include or "").split(",") if t.strip()}
    scope_parts: list[str] = []
    if "notebook" in targets:
        scope_parts.append("notebook")
    if "wiki" in targets:
        scope_parts.append("wiki")
    if "decisions" in targets:
        scope_parts.append("decision")
    if "tasks" in targets:
        scope_parts.append("task")
    scopes_str = ",".join(scope_parts) if scope_parts else "notebook,wiki,decision,task"

    try:
        from omeia.api.search_service import SearchService

        result = SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=llm_client).unified_search(
            q,
            scopes=scopes_str,
            project_code=project_code,
            mode="keyword",
            limit=limit,
        )
        out: Dict[str, Any] = {"query": q, "project_code": project_code}
        bucket_key = {"notebook": "notebook", "wiki": "wiki", "decision": "decisions", "task": "tasks"}
        grouped: dict[str, list] = {k: [] for k in ("notebook", "wiki", "decisions", "tasks")}

        for hit in result.hits:
            key = bucket_key.get(hit.bucket or "")
            if not key:
                continue
            meta = hit.metadata or {}
            if hit.bucket == "notebook":
                grouped[key].append({
                    "id": hit.id,
                    "entry_id": hit.id,
                    "project_code": hit.project_code,
                    "title": hit.title,
                    "excerpt": hit.snippet,
                    "content": hit.snippet,
                    "kind": meta.get("entry_type"),
                    "entry_type": meta.get("entry_type"),
                    "created_at": hit.created_at,
                })
            elif hit.bucket == "wiki":
                grouped[key].append({
                    "id": hit.id,
                    "wiki_id": hit.id,
                    "project_code": hit.project_code,
                    "title": hit.title,
                    "excerpt": hit.snippet,
                    "content": hit.snippet,
                    "kind": meta.get("wiki_type"),
                    "wiki_type": meta.get("wiki_type"),
                    "updated_at": hit.updated_at,
                    "revision": 1,
                })
            elif hit.bucket == "decision":
                grouped[key].append({
                    "id": hit.id,
                    "decision_id": hit.id,
                    "project_code": hit.project_code,
                    "title": hit.title,
                    "excerpt": hit.snippet,
                    "decision_details": hit.snippet,
                    "decision_date": meta.get("decision_date"),
                })
            elif hit.bucket == "task":
                grouped[key].append({
                    "id": hit.id,
                    "task_id": hit.id,
                    "project_code": hit.project_code,
                    "title": hit.title,
                    "description": hit.snippet,
                    "excerpt": hit.snippet,
                    "status": meta.get("status"),
                    "assignee": meta.get("assignee"),
                })

        for k in ("notebook", "wiki", "decisions", "tasks"):
            if k in targets:
                out[k] = grouped[k]
        out["total"] = sum(len(out.get(k) or []) for k in ("notebook", "wiki", "decisions", "tasks"))
        return out
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/folders")
def get_folders(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT f.folder_id, p.project_code, s.sample_code, f.folder_name, f.absolute_path, f.storage_system, f.data_type, f.file_count, f.total_size_bytes
                    FROM platform.folder_catalog f
                    JOIN core.project p ON f.project_id = p.project_id
                    LEFT JOIN core.sample s ON f.sample_id = s.sample_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "folder_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "folder_name": r[3],
                    "absolute_path": r[4],
                    "storage_system": r[5],
                    "data_type": r[6],
                    "file_count": r[7],
                    "total_size_bytes": r[8]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/datasets")
def get_datasets(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT d.dataset_id, p.project_code, s.sample_code, d.dataset_name, d.data_type, d.format, d.file_path, d.file_size_bytes, d.quality_status, d.notes
                    FROM platform.dataset_catalog d
                    JOIN core.project p ON d.project_id = p.project_id
                    LEFT JOIN core.sample s ON d.sample_id = s.sample_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "dataset_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "dataset_name": r[3],
                    "data_type": r[4],
                    "format": r[5],
                    "file_path": r[6],
                    "file_size": r[7],
                    "quality_status": r[8],
                    "notes": r[9]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/pipeline_runs")
def get_pipeline_runs(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT pr.run_id, p.project_code, s.sample_code, pr.pipeline_stage, pr.command_used, pr.script_path, pr.status, pr.error_summary, pr.qc_result, pr.created_at
                    FROM platform.pipeline_run pr
                    JOIN core.project p ON pr.project_id = p.project_id
                    LEFT JOIN core.sample s ON pr.sample_id = s.sample_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY pr.created_at DESC;"
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "run_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "pipeline_stage": r[3],
                    "command_used": r[4],
                    "script_path": r[5],
                    "status": r[6],
                    "error_summary": r[7],
                    "qc_result": r[8],
                    "created_at": r[9].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/tasks")
def get_tasks(
    project_code: Optional[str] = None,
    user: Optional[dict] = Depends(optional_public_user),
) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                if project_rbac_enabled():
                    user = ensure_authenticated_for_rbac(user)
                    if project_code:
                        ensure_project_access(user, project_code, cur=cur)
                query = """
                    SELECT t.task_id, p.project_code, s.sample_code, r.full_name, t.title, t.description, t.status, t.priority, t.due_date
                    FROM platform.task t
                    JOIN core.project p ON t.project_id = p.project_id
                    LEFT JOIN core.sample s ON t.sample_id = s.sample_id
                    LEFT JOIN platform.researcher r ON t.assigned_to = r.researcher_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                if project_rbac_enabled() and user and not project_code:
                    allowed = filter_projects_for_user(
                        user,
                        [{"project_code": r[1]} for r in rows],
                        cur,
                    )
                    allowed_codes = {(p.get("project_code") or "").upper() for p in allowed}
                    rows = [r for r in rows if (r[1] or "").upper() in allowed_codes]
                return [{
                    "task_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "assigned_to": r[3],
                    "title": r[4],
                    "description": r[5],
                    "status": r[6],
                    "priority": r[7],
                    "due_date": str(r[8]) if r[8] else None
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/tasks")
def create_task(req: TaskCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                pid_row = cur.fetchone()
                if not pid_row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = pid_row[0]
                ensure_project_access(user, req.project_code, cur=cur)

                sid = None
                if req.sample_code:
                    cur.execute("SELECT sample_id FROM core.sample WHERE sample_code = %s;", (req.sample_code,))
                    s_row = cur.fetchone()
                    if s_row:
                        sid = s_row[0]

                rid = resolve_researcher_id(cur, user)

                due = datetime.strptime(req.due_date, "%Y-%m-%d").date() if req.due_date else None

                cur.execute("""
                    INSERT INTO platform.task (project_id, sample_id, title, description, status, priority, due_date, assigned_to)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING task_id;
                """, (pid, sid, req.title, req.description, req.status, req.priority, due, rid))
                task_id = cur.fetchone()[0]

                assignee_name = user.get("email") or "researcher"
                # Automatically log in the notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Task Created: {req.title}",
                    content=f"Task assigned to {assignee_name}.\nDetails: {req.description or ''}\nStatus: {req.status}, Priority: {req.priority}",
                    entry_type="general_note",
                    sample_id=sid
                )
                conn.commit()
                return {"status": "success", "task_id": str(task_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.put("/tasks/{task_id}")
def update_task(task_id: str, req: TaskUpdate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                due = datetime.strptime(req.due_date, "%Y-%m-%d").date() if req.due_date else None
                cur.execute("""
                    UPDATE platform.task
                    SET title = %s, description = %s, status = %s, priority = %s, due_date = %s, updated_at = now()
                    WHERE task_id = %s
                    RETURNING project_id, sample_id;
                """, (req.title, req.description, req.status, req.priority, due, task_id))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Task not found")
                
                pid, sid = row[0], row[1]
                rid = resolve_researcher_id(cur, user)

                # Automatically log in the notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Task Updated: {req.title}",
                    content=f"Task status changed to {req.status}.\nPriority: {req.priority}",
                    entry_type="general_note",
                    sample_id=sid
                )
                conn.commit()
                return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/auto_logs")
def get_auto_logs() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT log_id, actor, event_type, description, created_at
                    FROM platform.auto_log
                    ORDER BY created_at DESC LIMIT 50;
                """)
                rows = cur.fetchall()
                return [{
                    "log_id": str(r[0]),
                    "actor": r[1],
                    "event_type": r[2],
                    "description": r[3],
                    "created_at": r[4].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/team")
def get_team() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT username, full_name, role, allowed_project_codes
                    FROM platform.researcher;
                """)
                rows = cur.fetchall()
                return [{
                    "username": r[0],
                    "full_name": r[1],
                    "role": r[2],
                    "allowed_projects": r[3]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/projects")
def create_project(req: ProjectCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Get or create lead researcher
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE full_name = %s OR username = %s LIMIT 1;", (req.project_lead, req.project_lead.lower().replace(" ", "")))
                row = cur.fetchone()
                if row:
                    lead_id = row[0]
                else:
                    username = req.project_lead.lower().replace(" ", "")[:15]
                    cur.execute("""
                        INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
                        VALUES (%s, %s, 'researcher', ARRAY[%s]::text[])
                        RETURNING researcher_id;
                    """, (username, req.project_lead, req.project_code))
                    lead_id = cur.fetchone()[0]

                # Get PI researcher ID
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'afarkkila';")
                af_row = cur.fetchone()
                pi_id = af_row[0] if af_row else lead_id

                # Insert Core project
                cur.execute("""
                    INSERT INTO core.project (project_code, project_name, project_lead, principal_investigator, disease_focus, short_description, default_sensitivity, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::core.sensitivity_level, %s::core.record_status)
                    ON CONFLICT (project_code) DO UPDATE
                    SET project_name = EXCLUDED.project_name, short_description = EXCLUDED.short_description
                    RETURNING project_id;
                """, (req.project_code, req.project_name, req.project_lead, req.principal_investigator, req.disease_focus, req.short_description, req.default_sensitivity, req.status))
                pid = cur.fetchone()[0]

                # Insert Project Extension
                cur.execute("""
                    INSERT INTO platform.project_extension (project_id, project_short_title, research_question, project_type, priority, collaborators, ethics_approval_reference, current_blockers, next_actions, project_summary, latest_update)
                    VALUES (%s, %s, %s, %s, %s, %s::text[], %s, %s, %s, %s, 'Project onboarded via wizard.')
                    ON CONFLICT (project_id) DO UPDATE
                    SET ethics_approval_reference = EXCLUDED.ethics_approval_reference,
                        current_blockers = EXCLUDED.current_blockers,
                        next_actions = EXCLUDED.next_actions,
                        project_summary = EXCLUDED.project_summary;
                """, (pid, req.project_name[:50], req.short_description, req.project_type, req.priority, req.collaborators, req.ethics_approval_reference, req.current_blockers, req.next_actions, req.project_summary))

                # Add members to project_member
                # Lead
                cur.execute("""
                    INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                    VALUES (%s, %s, 'project_lead', 'read_write', 'Lead researcher on project')
                    ON CONFLICT (project_id, researcher_id) DO NOTHING;
                """, (pid, lead_id))
                
                # PI
                cur.execute("""
                    INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                    VALUES (%s, %s, 'PI', 'admin', 'Principal Investigator oversight')
                    ON CONFLICT (project_id, researcher_id) DO NOTHING;
                """, (pid, pi_id))

                # Seeding onboarding checklist items for this new project
                checklist_items = [
                    ("project", "Project Description & Goals", "Ensure project description, scientific questions, and goals are documented."),
                    ("project", "Members & Collaborators", "Add responsible researchers and their clinical/computational roles."),
                    ("document", "Protocols & SOPs", "Link the wet-lab staining/imaging and dry-lab segmentation SOPs used."),
                    ("document", "Ethics Approvals", "Record the ethics board registry reference number."),
                    ("software", "Software Versions", "Document package versions (Cylinter, Ashlar, Mesmer, Tribus) used."),
                    ("pipeline", "Stitching Pipeline Run", "Execute and link Ashlar stitching logs/runs."),
                    ("pipeline", "Cell Segmentation Quality Check", "Verify cell boundaries and mask outputs."),
                    ("dataset", "OME-TIFF Raw Slides", "Verify raw image folders are cataloged and size computed."),
                    ("dataset", "Segmented Cell Masks", "Store and register cell masks (.tif) in object storage."),
                    ("dataset", "Quantified Cell Features Table", "Verify single-cell expression tables (.csv/.h5ad) are cataloged."),
                    ("sample", "Sample Code Verification", "Align clinical patient codes with imaging specimen codes."),
                    ("publication", "Preprint/Publication Linkage", "Track linked publications or conference poster details.")
                ]
                for category, item, desc in checklist_items:
                    cur.execute("""
                        INSERT INTO platform.onboarding_checklist (project_id, category, item_name, description, status)
                        VALUES (%s, %s, %s, %s, 'pending')
                        ON CONFLICT (project_id, category, item_name) DO NOTHING;
                    """, (pid, category, item, desc))

                # Automatically write to Digital Notebook
                auto_log_notebook_entry(
                    conn, pid, lead_id,
                    title="Project Onboarded Successfully",
                    content=f"The project '{req.project_name}' has been created with code '{req.project_code}' by Lead {req.project_lead}.\nPriority set to: {req.priority}\nEthics Reference: {req.ethics_approval_reference}",
                    entry_type="general_note"
                )

                conn.commit()
                return {"status": "success", "project_id": str(pid)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/ai-models")
def get_ai_models() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT model_id, name, model_type, source, license, parameters, gpu_requirements, memory_requirements, local_deployment, api_deployment, use_cases, strengths, weaknesses, installation_instructions
                    FROM platform.ai_model
                    ORDER BY model_type, name;
                """)
                rows = cur.fetchall()
                return [{
                    "model_id": str(r[0]),
                    "name": r[1],
                    "model_type": r[2],
                    "source": r[3],
                    "license": r[4],
                    "parameters": r[5],
                    "gpu_requirements": r[6],
                    "memory_requirements": r[7],
                    "local_deployment": r[8],
                    "api_deployment": r[9],
                    "use_cases": r[10],
                    "strengths": r[11],
                    "weaknesses": r[12],
                    "installation_instructions": r[13]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/infrastructure")
def get_infrastructure() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT resource_id, name, resource_type, operating_system, cpu_specs, ram_specs, gpu_specs, storage_specs, installed_software, access_notes, maintenance_notes
                    FROM platform.infrastructure
                    ORDER BY resource_type, name;
                """)
                rows = cur.fetchall()
                return [{
                    "resource_id": str(r[0]),
                    "name": r[1],
                    "resource_type": r[2],
                    "operating_system": r[3],
                    "cpu_specs": r[4],
                    "ram_specs": r[5],
                    "gpu_specs": r[6],
                    "storage_specs": r[7],
                    "installed_software": r[8],
                    "access_notes": r[9],
                    "maintenance_notes": r[10]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/publications")
def get_publications() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pub.pub_id, pub.title, pub.authors, pub.journal, pub.publication_year, pub.doi, pub.pmid, pub.abstract, p.project_code, pub.full_text_path
                    FROM platform.publication pub
                    LEFT JOIN core.project p ON pub.project_id = p.project_id
                    ORDER BY pub.publication_year DESC, pub.title;
                """)
                rows = cur.fetchall()
                return [{
                    "pub_id": str(r[0]),
                    "title": r[1],
                    "authors": r[2],
                    "journal": r[3],
                    "publication_year": r[4],
                    "doi": r[5],
                    "pmid": r[6],
                    "abstract": r[7],
                    "project_code": r[8],
                    "full_text_path": r[9]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/checklists/{project_code}")
def get_project_checklists(project_code: str) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (project_code,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = row[0]
                cur.execute("""
                    SELECT checklist_id, category, item_name, description, status, checked_at
                    FROM platform.onboarding_checklist
                    WHERE project_id = %s
                    ORDER BY category, item_name;
                """, (pid,))
                rows = cur.fetchall()
                return [{
                    "checklist_id": str(r[0]),
                    "category": r[1],
                    "item_name": r[2],
                    "description": r[3],
                    "status": r[4],
                    "checked_at": r[5].isoformat() if r[5] else None
                } for r in rows]
    except HTTPException:
        raise
    except Exception as exc:
        # Table may be missing on fresh DB — don't break project workspace load
        if "onboarding_checklist" in str(exc) or "does not exist" in str(exc):
            return []
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/checklists/toggle")
def toggle_checklist(req: ChecklistToggleRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Get current status and item details
                cur.execute("""
                    SELECT project_id, category, item_name, status 
                    FROM platform.onboarding_checklist 
                    WHERE checklist_id = %s;
                """, (req.checklist_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Checklist item not found")
                
                pid, category, item_name, current_status = row[0], row[1], row[2], row[3]
                cur.execute(
                    "SELECT project_code FROM core.project WHERE project_id = %s;",
                    (pid,),
                )
                pcode_row = cur.fetchone()
                if pcode_row:
                    ensure_project_access(user, pcode_row[0], cur=cur)
                rid = resolve_researcher_id(cur, user)

                # Toggle or set status
                checked_at = datetime.now() if req.status == 'completed' else None
                cur.execute("""
                    UPDATE platform.onboarding_checklist
                    SET status = %s, checked_at = %s, updated_at = now()
                    WHERE checklist_id = %s;
                """, (req.status, checked_at, req.checklist_id))

                # Log to notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Checklist Item Updated: {item_name}",
                    content=f"Checklist item '{item_name}' in category '{category}' changed from '{current_status}' to '{req.status}'.",
                    entry_type="general_note"
                )

                conn.commit()
                return {"status": "success", "new_status": req.status}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))