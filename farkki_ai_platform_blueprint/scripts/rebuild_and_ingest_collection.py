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
from app_skeleton.api.llm_client import LLMClient
from app_skeleton.api.supabase_config import postgres_conn
from app_skeleton.api.supabase_sync import sync_documents_to_supabase

JSON_PATH = Path("/home/debdeba/Documents/scripts/farkki_ai_platform_blueprint/docs/omeia_lab_documents_complete_collection.json")
DB_CONN = postgres_conn()
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_DOC_CHUNKS = "doc_chunks"
EMBEDDING_DIM = 384

def get_stable_uuid(doc_id: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, doc_id)

def generate_gui_display(doc: dict) -> dict:
    doc_type = doc["classification"]["document_type"]
    content = doc["content"]
    structured = doc.get("structured_data", {})
    
    sections = []
    
    # 1. Document Info Section
    info_fields = [
        {"label": "Document Type", "value": doc_type.replace("_", " ").title(), "editable": True},
        {"label": "Source File", "value": doc["source"]["file_name"] or "Unknown", "editable": True}
    ]
    
    # Add author/signee details
    author = doc["source"].get("workbook_metadata", {}).get("author") or structured.get("author", {}).get("name")
    if author:
        info_fields.append({"label": "Author", "value": author, "editable": True})
    
    people = doc.get("entities", {}).get("people", [])
    if people:
        info_fields.append({"label": "Signee / Contact", "value": ", ".join(people), "editable": True})
        
    sections.append({
        "section_title": "Document Info",
        "fields": info_fields
    })
    
    # 2. Access Credentials if available
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
            
    # 3. Key Contact Persons if available
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
        
    # 4. Form Fields & Template Values (EAV format fields)
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
        
    # 5. Operational Instructions
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

    # 6. Specific fields for other categories
    pickup_rules = structured.get("pickup_rules", [])
    if pickup_rules:
        pk_fields = []
        for p in pickup_rules:
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
    # Build complete JSON documents list
    collection = {
        "schema_version": "1.0",
        "collection_id": "omeia_lab_documents_complete_collection_2026_06_04",
        "collection_name": "omeia_lab_documents_complete_collection",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Complete logistics, billing, shipping, and web portals directory for Färkkilä Lab.",
        "documents": [
            # 1. HUSLAB Order Form (Retained from original collection)
            {
                "document_id": "huslab_order_form_university_of_helsinki_h3604_vaharautio",
                "source": {
                    "file_name": "HUSLAB_order_form(1).xls",
                    "file_type": "xls"
                },
                "classification": {
                    "document_type": "order_form",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.97
                },
                "language": {
                    "original": "fi_en",
                    "canonical": "en"
                },
                "content": {
                    "title": "HUSLAB Laboratory Diagnostics Ordering Form",
                    "short_summary": "Active Excel template sheet containing invoicing details, sample codes, and product references for ordering HUSLAB diagnostic tests.",
                    "canonical_text": "HUSLAB Order form template for Helsinki University. References project H3604 and Vaharautio group.",
                    "sections": [
                        {
                            "section_id": "sec_billing",
                            "heading": "HUSLAB Billing Details",
                            "canonical_text": "Invoicing details for HUSLAB: Profitcenter H3604. Customer reference: Vaharautio."
                        }
                    ]
                },
                "entities": {
                    "people": ["Anniina Färkkilä", "Anastasia Lundgren"],
                    "organizations": ["HUSLAB", "University of Helsinki"]
                },
                "structured_data": {
                    "tables": [
                        {
                            "name": "example_ordered_products",
                            "column_names": ["product_number", "product_name", "concentration", "amount"],
                            "rows": [
                                {"product_number": "2184", "product_name": "HE-värjäys (Histology HE-staining)", "concentration": None, "amount": "10 slides"},
                                {"product_number": "1488", "product_name": "Immunohistokemiallinen värjäys (IHC staining)", "concentration": "standard", "amount": "5 slides"}
                            ]
                        }
                    ]
                }
            },
            # 2. University of Helsinki Invoicing and Delivery Address
            {
                "document_id": "university_of_helsinki_billing_and_delivery",
                "source": {
                    "file_name": "Billing_and_delivery_information_FÄRKKILÄ",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "billing_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.98
                },
                "language": {
                    "original": "fi_en",
                    "canonical": "en"
                },
                "content": {
                    "title": "University of Helsinki Billing & Delivery Guidelines",
                    "short_summary": "Färkkilä Lab delivery address, VAT identifiers, and official Telia Finland electronic/paper/email invoicing protocols.",
                    "canonical_text": "Färkkilä Lab delivery address: Anastasia Lundgren, University of Helsinki, Biomedicum Helsinki, Haartmaninkatu 8, FI-00290 Helsinki. VAT: FI03134717. EORI: FI0313471-7. Y-tunnus: 0313471-7.\nInvoicing address changes on March 2, 2020: Intermediator Telia Finland Oyj. EDI Code / OVT: 003703134717. Intermediator code: 003703575029. Invoices must include profit center H30492 / wbs730492302.",
                    "sections": [
                        {
                            "section_id": "delivery_address",
                            "heading": "Delivery Address & Contact",
                            "canonical_text": "Färkkilä Lab, Biomedicum Helsinki, 3rd floor, Haartmaninkatu 8, FI-00290 Helsinki, Finland. Attention to: Anastasia Lundgren. Phone: +358294125180."
                        },
                        {
                            "section_id": "tax_ids",
                            "heading": "Tax & Customs Identifiers",
                            "canonical_text": "VAT number: FI03134717. EORI number: FI0313471-7. Y-tunnus / Business ID: 0313471-7."
                        },
                        {
                            "section_id": "e_invoicing",
                            "heading": "Electronic Invoicing (Telia)",
                            "canonical_text": "OVT / EDI-tunnus: 003703134717. Intermediator (operaattori): Telia Finland Oyj. Intermediator code (välittäjätunnus): 003703575029."
                        },
                        {
                            "section_id": "paper_email",
                            "heading": "Paper & Email Invoicing",
                            "canonical_text": "Paper Invoices: Helsingin Yliopisto, PL 744, 00074 CGI. Email invoices (PDF): hy-laskut@helsinki.fi."
                        }
                    ]
                },
                "entities": {
                    "people": ["Anastasia Lundgren", "Anniina Färkkilä"],
                    "organizations": ["University of Helsinki", "Telia Finland Oyj", "CGI"],
                    "project_codes": ["H30492"],
                    "WBS_codes": ["730492302"]
                },
                "structured_data": {
                    "contacts": [
                        {"name": "Anastasia Lundgren", "role": "Lab Manager", "phone": "+358294125180", "organization": "University of Helsinki"}
                    ],
                    "form_fields": [
                        {"field_name": "Delivery Address", "value": "Färkkilä Lab, Biomedicum Helsinki, 3rd Floor, Haartmaninkatu 8, FI-00290 Helsinki, Finland"},
                        {"field_name": "Recipient Phone", "value": "+358294125180"},
                        {"field_name": "VAT Number", "value": "FI03134717"},
                        {"field_name": "EORI ID", "value": "FI0313471-7"},
                        {"field_name": "Business ID (Y-tunnus)", "value": "0313471-7"},
                        {"field_name": "OVT / EDI Code", "value": "003703134717"},
                        {"field_name": "Electronic Operator", "value": "Telia Finland Oyj [Code: 003703575029]"},
                        {"field_name": "Paper Billing Address", "value": "Helsingin Yliopisto, PL 744, 00074 CGI"},
                        {"field_name": "Email PDF Billing", "value": "hy-laskut@helsinki.fi"},
                        {"field_name": "Required Reference", "value": "Profitcenter: RPU/H30492 / Anniina Färkkilä lab / WBS: 730492302"}
                    ]
                }
            },
            # 3. HUS Naistentaudit & Synnytykset (HUS NaiS) Invoicing Instructions
            {
                "document_id": "hus_nais_billing_instructions",
                "source": {
                    "file_name": "Billing_and_delivery_information_FÄRKKILÄ",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "billing_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.99
                },
                "language": {
                    "original": "fi_en",
                    "canonical": "en"
                },
                "content": {
                    "title": "HUS Department of Obstetrics & Gynecology Billing Guidelines",
                    "short_summary": "Active electronic, paper, and email invoicing addresses for HUS Naistentaudit ja synnytykset, including the VTR 2024-2026 references.",
                    "canonical_text": "HUS Naistentaudit ja synnytykset billing guidelines. Reference VTR 2024-2026: TYH2024302. OVT-tunnus: 003715675350130. Operator: OpusCapita Solutions Oy (code E204503). HUS Business ID (Y-tunnus): 1567535-0. VAT: FI15675350. Contact Secretary Jarkko Auranheimo.\nFallback Paper Address: HUS Kuntayhtymä/HYKS-sairaanhoitoalue, PL 94029, 01051 LASKUT.",
                    "sections": [
                        {
                            "section_id": "e_invoice",
                            "heading": "Electronic Invoicing (HUS)",
                            "canonical_text": "OVT-tunnus: 003715675350130. Operator: OpusCapita Solutions Oy [Code: E204503]. Primary Reference for 2024-2026: TYH2024302."
                        },
                        {
                            "section_id": "paper_billing",
                            "heading": "Paper Billing Address",
                            "canonical_text": "HUS Kuntayhtymä / HYKS-sairaanhoitoalue, Naistentaudit ja synnytykset, PL 94029, 01051 LASKUT."
                        },
                        {
                            "section_id": "contact_info",
                            "heading": "Admin Contact Office",
                            "canonical_text": "HUS Administrator / Secretary: Jarkko Auranheimo. Email: jarkko.auranheimo@helsinki.fi."
                        }
                    ]
                },
                "entities": {
                    "people": ["Jarkko Auranheimo", "Anniina Färkkilä"],
                    "organizations": ["HUS Joint Authority", "OpusCapita Solutions Oy"],
                    "project_codes": ["TYH2024302"],
                    "WBS_codes": ["1179004Y1017N0214", "1179003TYH2021103"]
                },
                "structured_data": {
                    "contacts": [
                        {"name": "Jarkko Auranheimo", "role": "HUS Administrative Secretary", "email": "jarkko.auranheimo@helsinki.fi", "organization": "HUS"}
                    ],
                    "form_fields": [
                        {"field_name": "Department", "value": "Naistentaudit ja synnytykset (Obstetrics & Gynecology)"},
                        {"field_name": "OVT / EDI ID", "value": "003715675350130"},
                        {"field_name": "Operator ID", "value": "OpusCapita Solutions Oy [E204503]"},
                        {"field_name": "HUS Business ID", "value": "1567535-0"},
                        {"field_name": "HUS VAT Number", "value": "FI15675350"},
                        {"field_name": "Reference VTR 2024-2026", "value": "TYH2024302"},
                        {"field_name": "Historical reference 2021", "value": "1179004Y1017N0214 (Ullis HUS money 1088e) / 1179003TYH2021103 (Anniina new ref)"},
                        {"field_name": "Paper Address", "value": "HUS Kuntayhtymä, PL 94029, 01051 LASKUT"},
                        {"field_name": "Secretary Contacts", "value": "Jarkko Auranheimo (jarkko.auranheimo@helsinki.fi)"}
                    ]
                }
            },
            # 4. HUS GCT Evo, FICAN South & HUSLAB Project Billing (Historical and other accounts)
            {
                "document_id": "hus_other_billing_instructions",
                "source": {
                    "file_name": "Billing_and_delivery_information_FÄRKKILÄ",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "billing_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.95
                },
                "language": {
                    "original": "fi_en",
                    "canonical": "en"
                },
                "content": {
                    "title": "HUS Other Accounts (GCT Evo, FICAN South & HUSLAB Project)",
                    "short_summary": "Billing codes and references for GCT Evo, FICAN South (both expired), and Anni Virtanen's HUSLAB project.",
                    "canonical_text": "Anni Virtanen Billing: Joint Authority for the Hospital District of Helsinki and Uusimaa, HUSLAB Project: M1023YLI25, POB 94128, FI-01051 LASKUT, Reference: 7836003, VAT: FI15675350.\nHUS GCT Evo (expired end of 2019): HYKS PL 94029, Reference TYH2017255, contact Nina Nyholm (nina.n.nyholm@hus.fi).\nFICAN South (expired end of 2019): Cost center 1180005, project M1018DITHE, contact Tuula Kallioinen (tuula.kallioinen@hus.fi). OVT 003715675350165, operator OpusCapita E204503.",
                    "sections": [
                        {
                            "section_id": "anni_virtanen",
                            "heading": "Anni Virtanen HUSLAB Project",
                            "canonical_text": "Billing address: Joint Authority for the Hospital District of Helsinki and Uusimaa. HUSLAB Project: M1023YLI25. POB 94128, FI-01051 LASKUT. Reference: 7836003. VAT: FI15675350."
                        },
                        {
                            "section_id": "gct_evo",
                            "heading": "GCT Evo Account (Expired)",
                            "canonical_text": "HUS-kuntayhtymä, HYKS, Naisten- ja lastentautien tulosyksikkö, PL 94029, 01051 LASKUT. Reference: TYH2017255 NKL/Anniina Färkkilä. Contact: Nina Nyholm (nina.n.nyholm@hus.fi)."
                        },
                        {
                            "section_id": "fican_south",
                            "heading": "FICAN South Account (Expired)",
                            "canonical_text": "Eteläinen syöpäkeskus (FICAN South). Project code: M1018DITHE. Cost center: 1180005. OVT: 003715675350165. Operator: OpusCapita E204503. Contacts: Tuula Kallioinen (tuula.kallioinen@hus.fi), Riitta Liikanen (riitta.liikanen@hus.fi)."
                        }
                    ]
                },
                "entities": {
                    "people": ["Anni Virtanen", "Nina Nyholm", "Tuula Kallioinen", "Riitta Liikanen"],
                    "organizations": ["HUSLAB", "FICAN South"],
                    "project_codes": ["M1023YLI25", "TYH2017255", "M1018DITHE"],
                    "WBS_codes": ["7836003"]
                },
                "structured_data": {
                    "form_fields": [
                        {"field_name": "Anni Virtanen Project ID", "value": "M1023YLI25"},
                        {"field_name": "Anni Virtanen PO Box", "value": "POB 94128, FI-01051 LASKUT"},
                        {"field_name": "Anni Virtanen Reference", "value": "7836003"},
                        {"field_name": "GCT Evo reference", "value": "TYH2017255 NKL/Anniina Färkkilä (EXPIRED)"},
                        {"field_name": "FICAN South reference", "value": "1180005 FICAN South & M1018DITHE (EXPIRED)"}
                    ]
                }
            },
            # 5. University of Helsinki Research Funds & Budgets
            {
                "document_id": "university_of_helsinki_research_funds",
                "source": {
                    "file_name": "Billing_and_delivery_information_FÄRKKILÄ",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "billing_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.98
                },
                "language": {
                    "original": "fi_en",
                    "canonical": "en"
                },
                "content": {
                    "title": "University of Helsinki Research Grants & WBS Codes",
                    "short_summary": "Active research grants catalog, WBS accounts, basic funding reference (Henna Tyynismaa), and ONCOSYS WBS details.",
                    "canonical_text": "Research projects grants and WBS codes list:\n- LTDK Early Career Research: 730492300 (Grant years 2019-2020)\n- Instrumentariumin Tiedesäätiö: 4707997 (2019-2020)\n- Lääketieteen Säätiö: 4707995 (2019)\n- Kulttuurirahasto: 4706188 (2019-2020)\n- AstraZeneca 2021: 4721381 (Only Anastasiya orders)\n- UH 3-year grant: 730492302 (2023-2025)\n- Basic Funding: RPU H3040 / WBS 73040001 (Henna Tyynismaa admin mail)\n- ONCOSYS PI: H30492 / WBS 730492320 (Anniina Färkkilä) / WBS 73049231 (Karen halloween)",
                    "sections": [
                        {
                            "section_id": "grants",
                            "heading": "Grants & WBS Catalog",
                            "canonical_text": "LTDK: 730492300. Instrumentarium: 4707997. Lääketieteen Säätiö: 4707995. Kulttuurirahasto: 4706188. AstraZeneca: 4721381. UH 3-year grant: 730492302."
                        },
                        {
                            "section_id": "basic_funding",
                            "heading": "Basic / Faculty Funding",
                            "canonical_text": "Basic funding WBS for RPU: H3040/wbs 73040001. Costs covered from Faculty basic funding (Henna Tyynismaa notice, 23 April 2020)."
                        },
                        {
                            "section_id": "oncosys",
                            "heading": "ONCOSYS WBS",
                            "canonical_text": "ONCOSYS account: H30492 / WBS 730492320. Halloween WBS: 73049231."
                        }
                    ]
                },
                "entities": {
                    "people": ["Henna Tyynismaa", "Anniina Färkkilä", "Anastasiya Chernenko"],
                    "organizations": ["University of Helsinki", "Research Programs Unit"],
                    "WBS_codes": ["730492300", "4707997", "4707995", "4706188", "4721381", "730492302", "73040001", "730492320", "73049231"]
                },
                "structured_data": {
                    "tables": [
                        {
                            "name": "active_grants_list",
                            "column_names": ["project_name", "grant_years", "wbs_code"],
                            "rows": [
                                {"project_name": "LTDK Early Career Research-project", "grant_years": "2019 - 2020", "wbs_code": "730492300"},
                                {"project_name": "Instrumentariumin Tiedesäätiö", "grant_years": "2019 – 2020", "wbs_code": "4707997"},
                                {"project_name": "Lääketieteen Säätiö", "grant_years": "2019", "wbs_code": "4707995"},
                                {"project_name": "Kulttuurirahasto", "grant_years": "2019-2020", "wbs_code": "4706188"},
                                {"project_name": "AstraZeneca, 2021 (only Anastasiya)", "grant_years": "2021", "wbs_code": "4721381"},
                                {"project_name": "UH 3-year grant", "grant_years": "2023-2025", "wbs_code": "730492302"},
                                {"project_name": "ONCOSYS PI Money", "grant_years": "Until 2020", "wbs_code": "730492320"}
                            ]
                        }
                    ],
                    "form_fields": [
                        {"field_name": "Basic Funding WBS", "value": "73040001 [Profitcenter: H3040]"},
                        {"field_name": "Faculty Contact", "value": "Henna Tyynismaa (henna.tyynismaa@helsinki.fi)"},
                        {"field_name": "Oncosys WBS", "value": "730492320 [H30492]"},
                        {"field_name": "Halloween WBS", "value": "73049231 [H30492]"}
                    ]
                }
            },
            # 6. AstraZeneca Collaboration Agreement
            {
                "document_id": "astrazeneca_project_billing",
                "source": {
                    "file_name": "Billing_and_delivery_information_FÄRKKILÄ",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "billing_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.94
                },
                "language": {
                    "original": "fi_en",
                    "canonical": "en"
                },
                "content": {
                    "title": "AstraZeneca Project Funding & Sample Billing",
                    "short_summary": "Billing schedule (15 samples @ 5333 EUR/sample, 80k total), labor allocations, and isolation kit orders for the AstraZeneca collaboration.",
                    "canonical_text": "AstraZeneca project billing instructions. Invoicing AstraZeneca in 3 installments (3 x 5 samples @ 5333 EUR/sample). Total budget: 80,000 EUR. Allocate salaries to Fernando Perez. WBS can be used for isolation kits and SNP arrays.",
                    "sections": [
                        {
                            "section_id": "invoicing",
                            "heading": "Invoicing & Budget",
                            "canonical_text": "Invoicing AstraZeneca in 3 installments (15 samples total). Sum is 3 x 5 sample series @ 5333 EUR/sample. Budget total is 80,000 EUR."
                        },
                        {
                            "section_id": "allocation",
                            "heading": "Labor & Material Allocations",
                            "canonical_text": "Allocate labor salaries to Fernando Perez. WBS should be used for isolation kit orders and SNP array billing (notify Lab Manager Anastasiya)."
                        }
                    ]
                },
                "entities": {
                    "people": ["Fernando Perez", "Anniina Färkkilä", "Anastasiya Chernenko"],
                    "organizations": ["AstraZeneca", "Myriad"]
                },
                "structured_data": {
                    "form_fields": [
                        {"field_name": "Total Agreement Budget", "value": "80,000 EUR"},
                        {"field_name": "Invoicing Schedule", "value": "3 installments of 5 samples @ 5333 EUR/sample"},
                        {"field_name": "Salary Allocation Target", "value": "Fernando Perez"},
                        {"field_name": "Consumables Target", "value": "Isolation kits, SNP array billing"},
                        {"field_name": "Lab Manager Notice Target", "value": "Anastasiya Chernenko"}
                    ]
                }
            },
            # 7. Web Portals & Lab Accounts Credentials
            {
                "document_id": "web_portals_and_lab_credentials",
                "source": {
                    "file_name": "USERNAMES_and_PASSWORDS_to_websites_Färkkilä lab",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "courier_service_account_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.98
                },
                "language": {
                    "original": "en",
                    "canonical": "en"
                },
                "content": {
                    "title": "Färkkilä Lab Portals & Web Credentials Directory",
                    "short_summary": "Unified directory of credentials, customer IDs, and contacts for scientific supply companies (VWR, Sigma-Aldrich, Qiagen, AGA/Linde, Lindström, Selleckchem, BGI, Nordic-Biosite, Biotechne, Eurofins).",
                    "canonical_text": "Directory of credentials for supplier websites:\n- VWR Avantor: anastasiya.chernenko@helsinki.fi / saundarya.shah@helsinki.fi, password redacted, HUS account 13010815.\n- Sigma-Aldrich Merck: Mikko Savin contact, anastasiya.chernenko@helsinki.fi.\n- Qiagen: Juha Isosomppi contact, customer nr 262822.\n- AGA Linde: CO2 gas orders, references H3040/73040001/ahlnas. Customer 6120692 (Oncosys) / 6136415 (Färkkilä).\n- Lindström Oy: Lab coats online service, katri.halonen@lindstromgroup.com. Customer 3377213.",
                    "sections": [
                        {
                            "section_id": "vwr",
                            "heading": "VWR Avantor Portal",
                            "canonical_text": "Username: anastasiya.chernenko@helsinki.fi / saundarya.shah@helsinki.fi. HUS account: 13010815."
                        },
                        {
                            "section_id": "sigma",
                            "heading": "Sigma-Aldrich Merck",
                            "canonical_text": "Username: anastasiya.chernenko@helsinki.fi. Contact: Mikko Savin, Client Success Manager (mikko.savin@merckgroup.com, +358503680816)."
                        },
                        {
                            "section_id": "qiagen",
                            "heading": "Qiagen Portal",
                            "canonical_text": "Username: anastasiya.chernenko@helsinki.fi. Customer number: 262822. Contact: Juha Isosomppi (+358405376966)."
                        },
                        {
                            "section_id": "aga_linde",
                            "heading": "AGA Linde Healthcare (CO2)",
                            "canonical_text": "CO2 Orders customer numbers: 6120692 (ONCOSYS), 6136415 (FÄRKKILÄ LAB). Delivery: Biomedicum 3rd floor, shaft elevator storage. Ref: H3040/73040001/ahlnas."
                        },
                        {
                            "section_id": "lindstrom",
                            "heading": "Lindström Oy (Lab Coats)",
                            "canonical_text": "Customer number: 3377213. Account: saundarya.shah@helsinki.fi. Laundry representative: Katri Halonen (+358440886281 Dmitrii delivery)."
                        }
                    ]
                },
                "entities": {
                    "people": ["Anastasiya Chernenko", "Saundarya Shah", "Mikko Savin", "Juha Isosomppi", "Katri Halonen"],
                    "organizations": ["VWR", "Merck", "Qiagen", "AGA Linde", "Lindström Oy"],
                    "WBS_codes": ["73040001"]
                },
                "domain_specific": {
                    "access_credentials": {
                        "vwr_primary": {"value": "anastasiya.chernenko@helsinki.fi", "sensitivity": "restricted"},
                        "vwr_primary_password": {"value_redacted": "vaharautiofarkkila", "sensitivity": "secret"},
                        "vwr_secondary": {"value": "saundarya.shah@helsinki.fi", "sensitivity": "restricted"},
                        "vwr_secondary_password": {"value_redacted": "LabFarkkila2025#", "sensitivity": "secret"},
                        "sigma_user": {"value": "anastasiya.chernenko@helsinki.fi", "sensitivity": "restricted"},
                        "sigma_password": {"value_redacted": "VaharautioFarkkila2022", "sensitivity": "secret"},
                        "qiagen_user": {"value": "anastasiya.chernenko@helsinki.fi", "sensitivity": "restricted"},
                        "qiagen_password": {"value_redacted": "FarkkilaLab#1", "sensitivity": "secret"},
                        "benchling_user": {"value": "anastasiya.chernenko@helsinki.fi", "sensitivity": "restricted"},
                        "benchling_password": {"value_redacted": "ONCOSYS2019", "sensitivity": "secret"},
                        "lindstrom_user": {"value": "saundarya.shah@helsinki.fi", "sensitivity": "restricted"},
                        "lindstrom_password": {"value_redacted": "LabFarkkila2025#", "sensitivity": "secret"},
                        "bgi_user": {"value": "FarkkilaLab", "sensitivity": "restricted"},
                        "bgi_password": {"value_redacted": "FFPECores_2019", "sensitivity": "secret"},
                        "selleckchem_user": {"value": "FärkkiläLab / ashwini.sakrepantanagaraj@helsinki.fi", "sensitivity": "restricted"},
                        "selleckchem_password": {"value_redacted": "Test2021", "sensitivity": "secret"},
                        "sensire_user": {"value": "anastasiya.chernenko@helsinki.fi", "sensitivity": "restricted"},
                        "sensire_password": {"value_redacted": "FarkkilaVaharautio2021", "sensitivity": "secret"},
                        "weatherhub_user": {"value": "ONCOSYS", "sensitivity": "restricted"},
                        "weatherhub_password": {"value_redacted": "OncosysB320", "sensitivity": "secret"},
                        "nordicbiosite_user": {"value": "saundarya.shah@helsinki.fi", "sensitivity": "restricted"},
                        "nordicbiosite_password": {"value_redacted": "Farkkila2025*", "sensitivity": "secret"},
                        "biotechne_user": {"value": "saundarya.shah@helsinki.fi", "sensitivity": "restricted"},
                        "biotechne_password": {"value_redacted": "FarkkilaVaharautio2023#", "sensitivity": "secret"},
                        "idt_user": {"value": "liangzh7", "sensitivity": "restricted"},
                        "idt_password": {"value_redacted": "lzh980129", "sensitivity": "secret"},
                        "bionordika_user": {"value": "saundarya.shah@helsinki.fi", "sensitivity": "restricted"},
                        "bionordika_password": {"value_redacted": "FarkkiLAB2025*", "sensitivity": "secret"},
                        "eurofins_user": {"value": "farkkilalab@gmail.com", "sensitivity": "restricted"},
                        "eurofins_password": {"value_redacted": "Afarkkilalab1!", "sensitivity": "secret"}
                    }
                },
                "structured_data": {
                    "contacts": [
                        {"name": "Mikko Savin", "role": "Sigma Merck Success Manager", "email": "mikko.savin@merckgroup.com", "phone": "+358503680816"},
                        {"name": "Juha Isosomppi", "role": "Qiagen Support", "email": "Juha.Isosomppi@qiagen.com", "phone": "+358405376966"},
                        {"name": "Katri Halonen", "role": "Lindström Rep", "email": "Katri.Halonen@lindstromgroup.com"}
                    ]
                }
            },
            # 8. FedEx Courier Account Details
            {
                "document_id": "fedex_courier_account_details",
                "source": {
                    "file_name": "FedEx account info",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "courier_service_account_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.99
                },
                "language": {
                    "original": "en",
                    "canonical": "en"
                },
                "content": {
                    "title": "FedEx Courier Account & Customs Guidelines",
                    "short_summary": "FedEx account (733424567), online shipping instructions, support telephone contacts, and US customs compliance recommendations.",
                    "canonical_text": "FedEx Account: 733424567 (Meilahti Campus). Login: FarkkilaLab. Password redacted. Secret question: Missä olet syntynyt? Answer: Helsinki. Phone: 010800515. Customs: 0204204928.\nUS Shipping Advice: Use FedEx online requests. Proforma is auto-generated. Shipments to US must include 3 copies of USDA statement. Do not use 'biological substance category B' labels for US tissue slide shipments.",
                    "sections": [
                        {
                            "section_id": "account_info",
                            "heading": "FedEx Account & Portals",
                            "canonical_text": "FedEx account: 733424567. Login: FarkkilaLab. Portal: https://www.fedex.com/fi-fi/home.html. Customs support: 0204204928."
                        },
                        {
                            "section_id": "us_shipping",
                            "heading": "USA Shipping Advice",
                            "canonical_text": "USA shipments need 3 copies of USDA statement signed separately. Avoid 'biological substance category B' labels for tissue slide segments to minimize customs clearance issues."
                        }
                    ]
                },
                "entities": {
                    "people": ["Anastasiya Chernenko", "Markus Innilä"],
                    "organizations": ["FedEx"]
                },
                "domain_specific": {
                    "access_credentials": {
                        "account_number": {"value": "733424567", "sensitivity": "restricted"},
                        "login": {"value": "FarkkilaLab", "sensitivity": "restricted"},
                        "password": {"value_redacted": "FarkkilaLab2019", "sensitivity": "secret"},
                        "security_question": {"source_text": "Missä olet syntynyt?", "english": "Where were you born?", "sensitivity": "restricted"},
                        "security_answer": {"value_redacted": "Helsinki", "sensitivity": "secret"}
                    }
                },
                "structured_data": {
                    "contacts": [
                        {"name": "FedEx Customer Service", "phone": "010800515"},
                        {"name": "FedEx Customs Department", "phone": "0204204928"}
                    ]
                }
            },
            # 9. UPS Courier Account Details
            {
                "document_id": "ups_courier_account_details",
                "source": {
                    "file_name": "BIlling_and_delivery_information_FÄRKKILÄ",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "courier_service_account_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.99
                },
                "language": {
                    "original": "en",
                    "canonical": "en"
                },
                "content": {
                    "title": "UPS Courier Account & Contacts",
                    "short_summary": "UPS account details (9R20V0), user credentials, and account manager contact.",
                    "canonical_text": "UPS Account: 9R20V0. User ID: anastasiyacherne. Password redacted.\nContact Manager: Tuomas Tyynilä (ttyynila@ups.com, +358406771036).",
                    "sections": [
                        {
                            "section_id": "account_info",
                            "heading": "UPS Account Info",
                            "canonical_text": "UPS Account number: 9R20V0. User ID: anastasiyacherne. Password redacted."
                        },
                        {
                            "section_id": "manager",
                            "heading": "UPS Account Manager",
                            "canonical_text": "Tuomas Tyynilä, Sales & Solutions Account Manager. Email: ttyynila@ups.com. Phone: +358406771036."
                        }
                    ]
                },
                "entities": {
                    "people": ["Tuomas Tyynilä"],
                    "organizations": ["UPS"]
                },
                "domain_specific": {
                    "access_credentials": {
                        "account_number": {"value": "9R20V0", "sensitivity": "restricted"},
                        "login": {"value": "anastasiyacherne", "sensitivity": "restricted"},
                        "password": {"value_redacted": "FarkkilaVaharautio2022", "sensitivity": "secret"}
                    }
                },
                "structured_data": {
                    "contacts": [
                        {"name": "Tuomas Tyynilä", "role": "Sales & Solutions Account Manager", "email": "ttyynila@ups.com", "phone": "+358406771036", "organization": "UPS"}
                    ]
                }
            },
            # 10. Customs Invoices & USDA Statements Archive
            {
                "document_id": "customs_and_usda_archive",
                "source": {
                    "file_name": "BIlling_and_delivery_information_FÄRKKILÄ",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "shipping_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.98
                },
                "language": {
                    "original": "en",
                    "canonical": "en"
                },
                "content": {
                    "title": "Customs Invoices & USDA Statements Archive",
                    "short_summary": "Historical collection of customs invoices and USDA statement declarations for sample shipping (Karolinska, Oslo Rikshospitalet, ESRF, ProMab USA).",
                    "canonical_text": "Archived customs statements:\n1. Tapio Tainola (07.06.2022) to Rikshospitalet Oslo (Bente Halvorsen). Mouse antibodies, 351 pcs. Value: 5 EUR. Dry Ice UN1845 10kg.\n2. Tapio Tainola (23.09.2020) to Karolinska Solna (Aarren Mannion). Mus musculus tissue, 10 pcs. Value: 5 EUR. Blue Ice 1kg.\n3. Tapio Tainola (06.06.2022) to ESRF Grenoble (Anton Popov). 15 tubes antibodies, Dry Ice UN1845 3kg. Value: 5 USD.\n4. Nadezhda Zinovkina (26.11.2019) to ProMab CA USA (Van Dang). 2 tubes antibodies, Blue Ice 1.2kg. Value: 10 EUR.",
                    "sections": [
                        {
                            "section_id": "oslo_shipment",
                            "heading": "Oslo Rikshospitalet Shipment (07.06.2022)",
                            "canonical_text": "Shipper: Tapio Tainola, Wihuri Research Institute, Biomedicum. Consignee: Bente Halvorsen/Ellen Lund Sagen, Oslo Rikshospitalet. Contents: 351 pcs frozen mouse antibodies. Value: 5 EUR. Dry Ice UN1845 10kg."
                        },
                        {
                            "section_id": "karolinska_shipment",
                            "heading": "Karolinska Solna Shipment (23.09.2020)",
                            "canonical_text": "Shipper: Tapio Tainola, Biomedicum. Consignee: Aarren Mannion, Karolinska Hospital. Contents: 10 pcs mus musculus tissue. Value: 5 EUR. Blue Ice 1kg."
                        },
                        {
                            "section_id": "esrf_shipment",
                            "heading": "ESRF Grenoble Shipment (06.06.2022)",
                            "canonical_text": "Shipper: Tapio Tainola. Consignee: Anton Popov, ESRF Grenoble. Contents: 15 tubes of antibodies (mouse supernatant, research use only, non-infectious). Dry Ice UN1845 3kg. Value: 5 USD."
                        },
                        {
                            "section_id": "promab_shipment",
                            "heading": "ProMab Richmond CA Shipment (26.11.2019)",
                            "canonical_text": "Shipper: Nadezhda Zinovkina, Biomedicum. Consignee: Van Dang, ProMab. Contents: 2 tubes antibodies. Value: 10 EUR. Blue Ice 1.2kg."
                        }
                    ]
                },
                "entities": {
                    "people": ["Tapio Tainola", "Nadezhda Zinovkina", "Bente Halvorsen", "Aarren Mannion", "Anton Popov", "Van Dang"],
                    "organizations": ["Wihuri Research Institute", "Karolinska Hospital", "ESRF Magasin", "ProMab Biotechnologies"]
                },
                "structured_data": {
                    "form_fields": [
                        {"field_name": "Oslo Consignee", "value": "Bente Halvorsen / Ellen Lund Sagen Rikshospitalet [+47-98460647]"},
                        {"field_name": "Karolinska Consignee", "value": "Aarren Mannion, Karolinska Solna [+46(0)793136828]"},
                        {"field_name": "ESRF Consignee", "value": "Anton Popov, ESRF Grenoble [+33-47688273]"},
                        {"field_name": "ProMab Consignee", "value": "Van Dang, ProMab Richmond CA [1-866-339-0871]"}
                    ]
                }
            },
            # 11. USDA Statement Human Sample Template
            {
                "document_id": "usda_statement_human_template",
                "source": {
                    "file_name": "USDA_Statement_Human non hazardous",
                    "file_type": "txt"
                },
                "classification": {
                    "document_type": "shipping_instruction",
                    "domain": "orders_shipping_admin",
                    "confidence": 0.97
                },
                "language": {
                    "original": "en",
                    "canonical": "en"
                },
                "content": {
                    "title": "USDA Human Non-Hazardous Shipping Template",
                    "short_summary": "Blank USDA statement template declaration for shipping non-infectious, non-contagious, non-hazardous human samples to the United States.",
                    "canonical_text": "USDA Statement Template for human non-hazardous tissue samples.\nDeclares: Exempt human sample is non-infectious, non-contagious, non-hazardous, and non-toxic. For in vitro use only. Not obtained from humans inoculated with livestock/poultry exotic diseases. Signee: Markus Innilä, University of Helsinki.",
                    "sections": [
                        {
                            "section_id": "template",
                            "heading": "Declaration Text",
                            "canonical_text": "Contents: Exempt human sample (sample type) in (container). Samples collected by sender, stored in (temperature/dry ice/cold pack). Non-infectious, non-contagious, non-hazardous, non-toxic. For in vitro use only. Material not obtained from humans/primates inoculated/exposed to exotic livestock/poultry diseases. Not of tissue culture origin, not zoonotic."
                        }
                    ]
                },
                "entities": {
                    "people": ["Markus Innilä"],
                    "organizations": ["University of Helsinki"]
                },
                "structured_data": {
                    "instructions": [
                        {"text": "Fill placeholders: sample type, container, storage temperature, quantity."},
                        {"text": "Print 3 copies of statement and sign separately."},
                        {"text": "Ensure description matches FedEx online request form exactly."}
                    ]
                }
            }
        ]
    }
    
    # Save JSON file
    print(f"Writing collection to: {JSON_PATH}")
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
        
    documents = collection.get("documents", [])
    print(f"Ingesting {len(documents)} documents to PostgreSQL and Qdrant...")
    
    # Initialize clients
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
            # Clear previous ingestion data
            print("Clearing core database documents...")
            cur.execute("TRUNCATE core.documents, core.billing_instructions, core.document_entities CASCADE;")
            
            # Start job
            job_code = f"rebuild_ingest_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            cur.execute("""
                INSERT INTO platform.digitalization_runs (run_id, mode, storage_root, status, dry_run, started_at)
                VALUES (%s, 'collection_ingest', 'collection', 'running', false, now())
                RETURNING run_id;
            """, (job_code,))
            
            ingested_count = 0
            chunk_count = 0
            vector_count = 0
            
            for doc in documents:
                doc_id_str = doc["document_id"]
                doc_uuid = get_stable_uuid(doc_id_str)
                doc_type = doc["classification"]["document_type"]
                content = doc["content"]
                structured = doc.get("structured_data", {})
                
                # Generate dynamic gui representation
                gui_payload = generate_gui_display(doc)
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
                    None,
                    doc["language"]["original"],
                    structured.get("author", {}).get("name") or (doc["entities"].get("people")[0] if doc["entities"].get("people") else None),
                    doc["entities"].get("emails")[0] if doc["entities"].get("emails") else None,
                    content["title"],
                    content.get("canonical_text"),
                    psycopg.types.json.Jsonb(full_structured)
                ))
                
                # 2. Insert into core.document_entities (EAV fields)
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
                if doc_type == "billing_instruction":
                    # Fill structure values if they map directly, else leave empty/null
                    cur.execute("""
                        INSERT INTO core.billing_instructions (
                            document_id, method, recipient_organization
                        ) VALUES (%s, %s, %s)
                    """, (doc_uuid, "invoice", "University of Helsinki"))
                
                # 4. Insert into platform.raw_asset_vault (Supabase sync metadata)
                cur.execute("""
                    INSERT INTO platform.raw_asset_vault (
                        asset_id, storage_provider, logical_path, filename, extension, size_bytes, checksum_sha256,
                        asset_type, domain, project_hint, section_hint, sensitivity_level, review_status,
                        vector_status, extraction_status, provenance, metadata_json, modified_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (asset_id) DO UPDATE SET
                        metadata_json = EXCLUDED.metadata_json,
                        updated_at = now()
                """, (
                    doc_id_str,
                    "local_database_mirror",
                    f"docs/{doc['source']['file_name']}",
                    doc["source"]["file_name"],
                    f".{doc['source']['file_type']}",
                    0,
                    "",
                    doc_type,
                    "orders_billing_admin",
                    "orders",
                    "billing",
                    "internal",
                    "approved",
                    "indexed",
                    "extracted",
                    psycopg.types.json.Jsonb({"rebuild_collection": True}),
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
                    f"/home/debdeba/Documents/scripts/farkki_ai_platform_blueprint/docs/{doc['source']['file_name']}",
                    f"docs/{doc['source']['file_name']}",
                    doc["source"]["file_name"],
                    f".{doc['source']['file_type']}",
                    0,
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
                    content.get("canonical_text"),
                    content.get("canonical_text"),
                    "rebuild_collection_json",
                    len(content.get("canonical_text", "")),
                    len(content.get("canonical_text", "").split())
                ))
                
                # 7. Ingest RAG and Vectorize
                document_code = f"lab::billing::{doc_id_str}"
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
                        "relative_path": f"docs/{doc['source']['file_name']}",
                        "document_kind": doc_type
                    })
                ))
                rag_doc_id = cur.fetchone()[0]
                
                # Clear existing chunks
                cur.execute("DELETE FROM rag.document_chunk WHERE document_id = %s;", (rag_doc_id,))
                
                # Loop chunks
                sections_list = content.get("sections", [])
                if not sections_list:
                    sections_list = [{
                        "section_id": "sec_full",
                        "heading": "Full Document",
                        "canonical_text": content["canonical_text"]
                    }]
                    
                points = []
                for idx, sec in enumerate(sections_list):
                    sec_text = sec.get("canonical_text") or ""
                    if not sec_text.strip():
                        continue
                    
                    chunk_uid = f"{document_code}::chunk_{idx:04d}"
                    cur.execute("""
                        INSERT INTO rag.document_chunk (
                            document_id, chunk_index, chunk_uid, section_path, chunk_text, token_count, sensitivity_level, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, 'internal', %s)
                        RETURNING chunk_id;
                    """, (
                        rag_doc_id,
                        idx,
                        chunk_uid,
                        f"docs/{doc['source']['file_name']}",
                        sec_text,
                        len(sec_text.split()),
                        psycopg.types.json.Jsonb({"heading": sec.get("heading")})
                    ))
                    db_chunk_id = cur.fetchone()[0]
                    chunk_count += 1
                    
                    # Embed
                    print(f"  Vectorizing section: {sec.get('heading') or idx}")
                    vector = llm.embed(sec_text[:4000], dim=EMBEDDING_DIM)
                    
                    # Qdrant payload
                    qdrant_payload = {
                        "schema_version": 1,
                        "corpus": "lab_operations",
                        "scope": "lab",
                        "source_type": "lab_policy_document",
                        "document_id": str(rag_doc_id),
                        "source_file_id": f"docs/{doc['source']['file_name']}",
                        "chunk_id": chunk_uid,
                        "chunk_index": idx,
                        "document_code": document_code,
                        "title": content["title"],
                        "text_preview": sec_text[:2000],
                        "text": sec_text[:8000],
                        "section_id": "billing",
                        "section_label": "Billing & ordering instructions",
                        "relative_path": f"docs/{doc['source']['file_name']}",
                        "where_to_find": f"Billing & ordering instructions → docs/{doc['source']['file_name']}",
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
            print(f"Successfully ingested {ingested_count} billing & logistics blueprints to database.")

    # Supabase synchronization
    print("Attempting to sync with hosted Supabase...")
    try:
        os.environ["SUPABASE_SYNC_ENABLED"] = "true"
        sync_report = sync_documents_to_supabase()
        print(f"Supabase sync status: {sync_report.get('status')}. Message: {sync_report.get('message', 'No message')}")
    except Exception as e:
        print(f"Supabase sync failed: {e}")

if __name__ == "__main__":
    main()
