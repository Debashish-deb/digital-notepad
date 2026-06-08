#!/usr/bin/env python3
import os
import json
import psycopg
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models
from omeia.api.llm_client import LLMClient
from omeia.api.supabase_config import postgres_conn
from omeia.api.supabase_sync import sync_documents_to_supabase

JSON_PATH = Path("/home/debdeba/data4TB/digital-notepad-main/docs/omeia_lab_documents_complete_collection.json")
DB_CONN = postgres_conn()
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_DOC_CHUNKS = "doc_chunks"
EMBEDDING_DIM = 384

def get_stable_uuid(doc_id: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, doc_id)

def get_first_elem(lst):
    return lst[0] if lst else None

def extract_billing_fields(doc):
    structured = doc.get("structured_data", {})
    form_fields = structured.get("form_fields", [])
    
    # Helper to find value by matching label case-insensitively
    def find_val(labels):
        for f in form_fields:
            name = f.get("field_name", "").lower()
            if any(l in name for l in labels):
                return f.get("value")
        return None

    doc_id = doc.get("document_id", "")
    doc_type = doc.get("classification", {}).get("document_type", "")
    
    # Defaults/Inferences based on doc content
    orgs = doc.get("entities", {}).get("organizations", [])
    recipient_org = "University of Helsinki" if any("helsinki" in o.lower() for o in orgs) else ("HUS" if any("hus" in o.lower() for o in orgs) else None)
    if not recipient_org:
        if "helsinki" in doc_id.lower() or "helsinki" in doc.get("content", {}).get("title", "").lower():
            recipient_org = "University of Helsinki"
        elif "hus" in doc_id.lower() or "hus" in doc.get("content", {}).get("title", "").lower():
            recipient_org = "HUS"

    method = "electronic_invoice" if find_val(["ovt", "edi", "electronic"]) else None
    
    # Extract specific values
    vat = find_val(["vat"])
    business_id = find_val(["business id", "y-tunnus"])
    ovt = find_val(["ovt", "edi"])
    operator = find_val(["operator"])
    
    # Clean operator code vs name
    operator_id = None
    operator_name = None
    if operator:
        if "[" in operator:
            parts = operator.split("[")
            operator_name = parts[0].strip()
            code_part = parts[1].replace("Code:", "").replace("]", "").strip()
            operator_id = code_part
        else:
            operator_name = operator
            
    reference = find_val(["reference"])
    po_box = find_val(["paper", "po box", "postal recipient"])
    
    return {
        "method": method,
        "condition_text": "If supplier cannot use electronic invoicing" if po_box else None,
        "recipient_organization": recipient_org,
        "recipient_department": find_val(["department"]),
        "operator_identifier": operator_id,
        "ovt_identifier": ovt,
        "edi_number": ovt,
        "reference_code": reference,
        "po_box": po_box,
        "postal_code": None,
        "city_or_invoice_unit": None,
        "business_id": business_id,
        "vat_number": vat,
        "operator_name": operator_name
    }


def generate_gui_display(doc: dict) -> dict:
    doc_id = doc["document_id"]
    doc_type = doc["classification"]["document_type"]
    content = doc["content"]
    structured = doc.get("structured_data", {})
    
    sections = []
    
    # 1. Document Info Section
    info_fields = [
        {"label": "Document Type", "value": doc_type.replace("_", " ").title(), "editable": True},
        {"label": "Source File", "value": doc["source"]["file_name"] or "Unknown", "editable": True}
    ]
    
    # Add workbook metadata if available
    workbook_meta = doc["source"].get("workbook_metadata")
    if workbook_meta:
        if workbook_meta.get("author"):
            info_fields.append({"label": "Author", "value": workbook_meta["author"], "editable": True})
        if workbook_meta.get("last_saved_by"):
            info_fields.append({"label": "Last Saved By", "value": workbook_meta["last_saved_by"], "editable": True})
    
    # Add people entities
    people = doc["entities"].get("people", [])
    if people:
        info_fields.append({"label": "Signee / Contact", "value": ", ".join(people), "editable": True})
        
    sections.append({
        "section_title": "Document Info",
        "fields": info_fields
    })
    
    # 2. Add Form Fields / Parameters Section
    form_fields = structured.get("form_fields", [])
    if form_fields:
        ff_fields = []
        for field in form_fields:
            val = field.get("value")
            if not val:
                val = "To be filled"
                if field.get("examples"):
                    val += f" (e.g. {', '.join(field['examples'])})"
            ff_fields.append({
                "label": field["field_name"],
                "value": val,
                "editable": True
            })
        sections.append({
            "section_title": "Form Fields & Template Values",
            "fields": ff_fields
        })
        
    # 3. Add Instructions Section
    instructions = structured.get("instructions", [])
    if instructions:
        inst_fields = []
        for idx, inst in enumerate(instructions, 1):
            inst_fields.append({
                "label": f"Instruction {idx}",
                "value": inst["text"],
                "editable": True
            })
        sections.append({
            "section_title": "Operational Instructions",
            "fields": inst_fields
        })
        
    # 4. Add specific sections depending on doc_type
    if doc_type == "order_form":
        # Add Example Products if any
        tables = structured.get("tables", [])
        for t in tables:
            if t["name"] == "example_ordered_products":
                prod_fields = []
                for idx, row in enumerate(t.get("rows", []), 1):
                    val_str = f"{row.get('product_name')} [No: {row.get('product_number') or 'N/A'}]"
                    if row.get("concentration"):
                        val_str += f" (Conc: {row['concentration']})"
                    if row.get("amount"):
                        val_str += f" - {row['amount']}"
                    prod_fields.append({
                        "label": f"Example Product {idx}",
                        "value": val_str,
                        "editable": True
                    })
                sections.append({
                    "section_title": "Example Ordered Products",
                    "fields": prod_fields
                })
                
    # Add access credentials if present
    domain_specific = doc.get("domain_specific", {})
    access = domain_specific.get("access_credentials", {})
    if access:
        cred_fields = []
        for key, val in access.items():
            if isinstance(val, dict):
                v_str = "[REDACTED / SECURE VAULT]" if val.get("value_redacted") else val.get("value")
                if not v_str and val.get("sensitivity") == "secret":
                    v_str = "[REDACTED / SECURE VAULT]"
                label = key.replace("_", " ").title()
                # special check for security question
                if key == "security_question":
                    label = "Security Question"
                    v_str = val.get("english") or val.get("source_text")
                cred_fields.append({
                    "label": label,
                    "value": v_str,
                    "editable": True
                })
        if cred_fields:
            sections.append({
                "section_title": "Access Credentials",
                "fields": cred_fields
            })
    
    # Add contacts if present
    contacts = structured.get("contacts", [])
    if contacts:
        cnt_fields = []
        for c in contacts:
            label = c.get("name") or c.get("contact_type") or "Contact"
            if c.get("role"):
                label += f" ({c['role']})"
            
            parts = []
            if c.get("phone"):
                parts.append(f"Phone: {c['phone']}")
            if c.get("email"):
                parts.append(f"Email: {c['email']}")
            if c.get("organization"):
                parts.append(f"Org: {c['organization']}")
            
            cnt_fields.append({
                "label": label,
                "value": "; ".join(parts) if parts else "Available",
                "editable": True
            })
        sections.append({
            "section_title": "Key Contact Persons",
            "fields": cnt_fields
        })
        
    # Add pickup rules (UPS specific) if present
    pickups = structured.get("pickup_rules", [])
    if pickups:
        pk_fields = []
        for p in pickups:
            site = p.get("site") or "General"
            val = f"{p.get('type', '')}"
            if p.get("pickup_location"):
                val += f" at {p['pickup_location']}"
            if p.get("pickup_days"):
                val += f" ({p['pickup_days']} {p.get('pickup_time', '')})"
            if p.get("local_instruction"):
                val += f" - Note: {p['local_instruction']}"
            if p.get("instruction"):
                val += f" - Instruction: {p['instruction']}"
            pk_fields.append({
                "label": f"Pickup ({site})",
                "value": val,
                "editable": True
            })
        sections.append({
            "section_title": "Pickup Schedules",
            "fields": pk_fields
        })
        
    # Add special rules (UN1845, UN3373 etc) if present
    special = structured.get("special_commodities", [])
    if special:
        sp_fields = []
        for sp in special:
            sp_fields.append({
                "label": f"Commodity {sp.get('code')}: {sp.get('description')}",
                "value": sp.get("instruction"),
                "editable": True
            })
        sections.append({
            "section_title": "Special Commodities Shipping",
            "fields": sp_fields
        })
            
    # Add quality warning at the bottom if warnings exist
    warnings = doc.get("quality", {}).get("warnings", [])
    if warnings:
        warn_fields = []
        for idx, w in enumerate(warnings, 1):
            warn_fields.append({
                "label": f"Quality Check {idx}",
                "value": w,
                "editable": False
            })
        sections.append({
            "section_title": "Quality Warnings & Audits",
            "fields": warn_fields
        })

    return {
        "title": content["title"],
        "subtitle": content["short_summary"],
        "sections": sections
    }

def main():
    print(f"Reading collection from: {JSON_PATH}")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        collection = json.load(f)
        
    documents = collection.get("documents", [])
    print(f"Found {len(documents)} documents to ingest.")
    
    print(f"Connecting to database: {DB_CONN}")
    llm = LLMClient()
    qdrant = QdrantClient(url=QDRANT_URL)
    
    # Ensure Qdrant collection
    try:
        qdrant.get_collection(COLLECTION_DOC_CHUNKS)
    except Exception:
        print(f"Creating Qdrant collection: {COLLECTION_DOC_CHUNKS}")
        qdrant.create_collection(
            collection_name=COLLECTION_DOC_CHUNKS,
            vectors_config={
                "text": models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
            },
        )
        
    with psycopg.connect(DB_CONN) as conn:
        with conn.cursor() as cur:
            # Clear previous ingestion data safely
            print("Clearing previous documents and core tables...")
            cur.execute("""
                DELETE FROM core.documents 
                WHERE document_type IN (
                    'billing_instruction', 
                    'order_form', 
                    'shipping_customs_statement', 
                    'shipping_instruction', 
                    'courier_service_account_instruction', 
                    'courier_service_instruction'
                );
            """)
            
            # Start a platform job
            job_code = f"collection_ingest_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            cur.execute("""
                INSERT INTO platform.digitalization_runs (run_id, mode, storage_root, status, dry_run, started_at)
                VALUES (%s, 'collection_ingest', 'collection', 'running', false, now())
                RETURNING run_id;
            """, (job_code,))
            
            # Keep track of statistics
            ingested_count = 0
            chunk_count = 0
            vector_count = 0
            
            for doc in documents:
                doc_id_str = doc["document_id"]
                doc_uuid = get_stable_uuid(doc_id_str)
                
                doc_type = doc["classification"]["document_type"]
                content = doc["content"]
                structured = doc.get("structured_data", {})
                
                # Dynamic gui display payload
                gui_payload = generate_gui_display(doc)
                
                # Combine gui display and original document into structured_json
                full_structured = {
                    **doc,
                    "gui_display": gui_payload
                }
                
                print(f"Ingesting: {doc_id_str} ({doc_type}) -> UUID: {doc_uuid}")
                
                # 1. Insert into core.documents
                cur.execute("""
                    INSERT INTO core.documents (document_id, document_type, document_date, source_language, author_name, author_email, subject, raw_text, structured_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    doc_uuid,
                    doc_type,
                    structured.get("dates", [{}])[0].get("date_iso") if structured.get("dates") else None,
                    doc["language"]["original"],
                    doc["source"].get("workbook_metadata", {}).get("author") or get_first_elem(doc["entities"].get("people")),
                    get_first_elem(doc["entities"].get("emails")),
                    content["title"],
                    content.get("original_text") or content.get("original_text_safe") or content.get("canonical_text"),
                    psycopg.types.json.Jsonb(full_structured)
                ))
                
                # 2. Insert into core.document_entities (EAV for GUI rendering)
                display_order = 0
                for section in gui_payload["sections"]:
                    for field in section["fields"]:
                        display_order += 1
                        cur.execute("""
                            INSERT INTO core.document_entities (
                                document_id, entity_type, section_title, label, value, editable, display_order
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            doc_uuid,
                            "gui_field",
                            section["section_title"],
                            field["label"],
                            field["value"],
                            field.get("editable", True),
                            display_order
                        ))
                
                # 3. Populate core.billing_instructions if applicable
                if doc_type in ("billing_instruction", "courier_service_account_instruction", "courier_service_instruction"):
                    bi = extract_billing_fields(doc)
                    cur.execute("""
                        INSERT INTO core.billing_instructions (
                            document_id, method, condition_text, recipient_organization, recipient_department, 
                            operator_identifier, ovt_identifier, edi_number, reference_code, 
                            po_box, postal_code, city_or_invoice_unit, business_id, vat_number, operator_name
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        doc_uuid, bi["method"], bi["condition_text"], bi["recipient_organization"], bi["recipient_department"],
                        bi["operator_identifier"], bi["ovt_identifier"], bi["edi_number"], bi["reference_code"],
                        bi["po_box"], bi["postal_code"], bi["city_or_invoice_unit"], bi["business_id"], bi["vat_number"], bi["operator_name"]
                    ))
                
                # 4. Insert into platform.raw_asset_vault (for Supabase sync asset registration)
                cur.execute("""
                    INSERT INTO platform.raw_asset_vault (
                        asset_id, storage_provider, logical_path, filename, extension, size_bytes, checksum_sha256,
                        asset_type, domain, project_hint, section_hint, sensitivity_level, review_status,
                        vector_status, extraction_status, provenance, metadata_json, modified_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (asset_id) DO UPDATE SET
                        storage_provider = EXCLUDED.storage_provider,
                        logical_path = EXCLUDED.logical_path,
                        filename = EXCLUDED.filename,
                        extension = EXCLUDED.extension,
                        size_bytes = EXCLUDED.size_bytes,
                        checksum_sha256 = EXCLUDED.checksum_sha256,
                        metadata_json = EXCLUDED.metadata_json,
                        updated_at = now()
                """, (
                    doc_id_str,
                    "local_database_mirror",
                    f"docs/{doc['source']['file_name'] or doc_id_str}",
                    doc["source"]["file_name"] or doc_id_str,
                    f".{doc['source']['file_type']}" if doc["source"]["file_type"] else "",
                    doc["source"].get("source_file_size_bytes", 0),
                    doc["source"].get("source_hash_sha256", ""),
                    doc_type,
                    "orders_billing_admin",
                    "orders",
                    "billing",
                    doc["classification"].get("security_classification", "internal"),
                    "approved",
                    "indexed",
                    "extracted",
                    psycopg.types.json.Jsonb({"imported_collection": True}),
                    psycopg.types.json.Jsonb(full_structured)
                ))
                
                # 5. Insert into platform.knowledge_assets
                cur.execute("""
                    INSERT INTO platform.knowledge_assets (
                        asset_id, storage_root_id, absolute_path, relative_path, filename, extension, file_size,
                        detected_type, ingestion_status, extraction_status, review_status, embedding_status, chunking_status, metadata_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asset_id) DO UPDATE SET
                        metadata_json = EXCLUDED.metadata_json,
                        updated_at = now()
                """, (
                    doc_id_str,
                    "lab_storage_root",
                    f"/home/debdeba/data4TB/digital-notepad-main/docs/{doc['source']['file_name'] or doc_id_str}",
                    f"docs/{doc['source']['file_name'] or doc_id_str}",
                    doc["source"]["file_name"] or doc_id_str,
                    f".{doc['source']['file_type']}" if doc["source"]["file_type"] else "",
                    doc["source"].get("source_file_size_bytes", 0),
                    doc_type,
                    "completed",
                    "completed",
                    "approved",
                    "completed",
                    "completed",
                    psycopg.types.json.Jsonb(full_structured)
                ))
                
                # 6. Insert into platform.extracted_texts
                cur.execute("""
                    INSERT INTO platform.extracted_texts (asset_id, raw_text, cleaned_text, extraction_method, char_count, word_count)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    doc_id_str,
                    content.get("original_text") or content.get("original_text_safe") or content.get("canonical_text"),
                    content["canonical_text"],
                    "canonical_collection_json",
                    len(content["canonical_text"]),
                    len(content["canonical_text"].split())
                ))
                
                # 7. Ingest to RAG tables and Vectorize Chunks
                # A unique stable document code for RAG
                document_code = f"lab::billing::{doc_id_str}"
                
                # Insert into rag.document_source
                cur.execute("""
                    INSERT INTO rag.document_source (
                        document_code, title, source_type, project_id, sensitivity_level, status, metadata
                    ) VALUES (%s, %s, %s, NULL, 'internal', 'active', %s)
                    ON CONFLICT (document_code) DO UPDATE SET
                        title = EXCLUDED.title,
                        metadata = EXCLUDED.metadata,
                        status = 'active'
                    RETURNING document_id;
                """, (
                    document_code,
                    content["title"],
                    "lab_policy_document",
                    psycopg.types.json.Jsonb({
                        "corpus": "lab_operations",
                        "section_id": "billing",
                        "section_label": "Billing & ordering instructions",
                        "relative_path": f"docs/{doc['source']['file_name'] or doc_id_str}",
                        "document_kind": doc_type
                    })
                ))
                rag_doc_id = cur.fetchone()[0]
                
                # Delete existing chunks for this source
                cur.execute("DELETE FROM rag.document_chunk WHERE document_id = %s;", (rag_doc_id,))
                
                # Chunking by sections defined in JSON
                sections_list = content.get("sections", [])
                if not sections_list:
                    # Fallback to single chunk
                    sections_list = [{
                        "section_id": "sec_full",
                        "heading": "Full Document",
                        "canonical_text": content["canonical_text"]
                    }]
                
                points = []
                for idx, sec in enumerate(sections_list):
                    sec_text = sec.get("canonical_text") or sec.get("original_text") or ""
                    if not sec_text.strip():
                        continue
                        
                    chunk_uid = f"{document_code}::chunk_{idx:04d}"
                    
                    # Insert into rag.document_chunk
                    cur.execute("""
                        INSERT INTO rag.document_chunk (
                            document_id, chunk_index, chunk_uid, section_path, chunk_text, token_count, sensitivity_level, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, 'internal', %s)
                        RETURNING chunk_id;
                    """, (
                        rag_doc_id,
                        idx,
                        chunk_uid,
                        f"docs/{doc['source']['file_name'] or doc_id_str}",
                        sec_text,
                        len(sec_text.split()),
                        psycopg.types.json.Jsonb({"heading": sec.get("heading")})
                    ))
                    db_chunk_id = cur.fetchone()[0]
                    chunk_count += 1
                    
                    # Compute vector embedding
                    print(f"  Vectorizing section: {sec.get('heading') or idx}")
                    vector = llm.embed(sec_text[:4000], dim=EMBEDDING_DIM)
                    
                    # Payload for Qdrant
                    qdrant_payload = {
                        "schema_version": 1,
                        "corpus": "lab_operations",
                        "scope": "lab",
                        "source_type": "lab_policy_document",
                        "document_id": str(rag_doc_id),
                        "source_file_id": f"docs/{doc['source']['file_name'] or doc_id_str}",
                        "chunk_id": chunk_uid,
                        "chunk_index": idx,
                        "document_code": document_code,
                        "title": content["title"],
                        "text_preview": sec_text[:2000],
                        "text": sec_text[:8000],
                        "section_id": "billing",
                        "section_label": "Billing & ordering instructions",
                        "relative_path": f"docs/{doc['source']['file_name'] or doc_id_str}",
                        "where_to_find": f"Billing & ordering instructions → docs/{doc['source']['file_name'] or doc_id_str}",
                        "document_kind": doc_type,
                        "project_code": None,
                        "allowed_project_codes": [],
                        "modality": ["lab_operations"],
                        "sensitivity_level": "internal",
                        "contains_patient_level_data": False,
                        "contains_direct_identifier": False,
                        "embedding_model": "llm_client_hashed_embed",
                        "embedding_dimension": EMBEDDING_DIM,
                        "status": "active",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    
                    qid = hashlib.md5(chunk_uid.encode("utf-8")).hexdigest()
                    points.append(models.PointStruct(
                        id=qid,
                        vector={"text": vector},
                        payload=qdrant_payload
                    ))
                    vector_count += 1
                
                # Upsert points to Qdrant
                if points:
                    qdrant.upsert(collection_name=COLLECTION_DOC_CHUNKS, points=points)
                
                ingested_count += 1
            
            # Finish platform job
            cur.execute("""
                UPDATE platform.digitalization_runs
                SET status = 'completed', finished_at = now(), report_json = %s::jsonb
                WHERE run_id = %s;
            """, (
                psycopg.types.json.Jsonb({
                    "ingested_count": ingested_count,
                    "chunk_count": chunk_count,
                    "vector_count": vector_count
                }),
                job_code
            ))
            
            conn.commit()
            print(f"Success! Ingested {ingested_count} documents, {chunk_count} RAG chunks, and {vector_count} Qdrant vectors.")
            
    # Try syncing to Supabase if config is set
    print("Attempting to sync with hosted Supabase database...")
    try:
        # Override env setting to force sync execution
        os.environ["SUPABASE_SYNC_ENABLED"] = "true"
        sync_report = sync_documents_to_supabase()
        print(f"Supabase sync status: {sync_report.get('status')}. Message: {sync_report.get('message', 'No message')}")
    except Exception as e:
        print(f"Supabase sync failed (expected if credentials missing): {e}")

if __name__ == "__main__":
    main()
