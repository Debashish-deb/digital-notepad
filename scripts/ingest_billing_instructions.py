#!/usr/bin/env python3
import os
import json
import psycopg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_CONN = os.getenv("POSTGRES_CONN", "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai")

PAYLOAD = {
  "document": {
    "document_type": "billing_instruction",
    "source_language": "fi",
    "document_date_raw": "10.8.2022",
    "document_date_iso": "2022-08-10",
    "author": {
      "name": "Jarkko Auraheimo",
      "email": "jarkko.auranheimo@helsinki.fi"
    },
    "subject": "HUS billing instructions and project funding status",
    "original_context": "Hei kaikki, Laskutusohje tässä alla."
  },
  "funding_status": [
    {
      "project_code": "TYH2021103",
      "status_raw": "tänä vuonna päättyvä",
      "status_interpreted": "ending this year",
      "amount_eur": 3200
    },
    {
      "project_code": "TYH2022206",
      "status_raw": "korkkaamaton",
      "status_interpreted": "unopened / unused",
      "amount_eur": 47000
    }
  ],
  "billing_instructions": {
    "primary_method": {
      "method": "electronic_invoice",
      "recipient": {
        "organization": "HUS Kuntayhtymä/HYKS-sairaanhoitoalue",
        "department": "Naistentaudit ja synnytykset"
      },
      "operator_identifier": "E204503",
      "ovt_identifier": "003715675350130",
      "reference": "2179002TYH2021103"
    },
    "fallback_method": {
      "condition": "If supplier cannot use electronic invoicing",
      "method": "postal_invoice",
      "recipient": {
        "organization": "HUS Kuntayhtymä / HYKS-sairaanhoitoalue",
        "department": "Naistentaudit ja synnytykset",
        "po_box": "PL 94029",
        "postal_code": "01051",
        "city_or_invoice_unit": "LASKUT"
      }
    }
  },
  "organization_identifiers": {
    "business_id_fi": "1567535-0",
    "vat_number": "FI15675350",
    "edi_number": "003715675350130",
    "operator": {
      "name": "OpusCapita Solutions Oy",
      "operator_number": "E204503"
    }
  },
  "gui_display": {
    "title": "HUS Billing Instructions",
    "subtitle": "Billing and project funding information from 10.8.2022",
    "sections": [
      {
        "section_title": "Document Info",
        "fields": [
          { "label": "Date", "value": "10.8.2022", "editable": True },
          { "label": "Author", "value": "Jarkko Auraheimo", "editable": True },
          { "label": "Email", "value": "jarkko.auranheimo@helsinki.fi", "editable": True }
        ]
      },
      {
        "section_title": "Funding Status",
        "fields": [
          { "label": "TYH2021103", "value": "Ending this year; 3200 EUR", "editable": True },
          { "label": "TYH2022206", "value": "Unopened / unused; 47000 EUR", "editable": True }
        ]
      },
      {
        "section_title": "Primary Billing Method",
        "fields": [
          { "label": "Method", "value": "Electronic invoice", "editable": True },
          { "label": "Recipient", "value": "HUS Kuntayhtymä/HYKS-sairaanhoitoalue, Naistentaudit ja synnytykset", "editable": True },
          { "label": "Operator identifier", "value": "E204503", "editable": True },
          { "label": "OVT identifier", "value": "003715675350130", "editable": True },
          { "label": "Reference", "value": "2179002TYH2021103", "editable": True }
        ]
      },
      {
        "section_title": "Fallback Billing Method",
        "fields": [
          { "label": "Condition", "value": "If supplier cannot use electronic invoicing", "editable": True },
          { "label": "Postal recipient", "value": "HUS Kuntayhtymä / HYKS-sairaanhoitoalue, Naistentaudit ja synnytykset, PL 94029, 01051 LASKUT", "editable": True }
        ]
      },
      {
        "section_title": "Identifiers",
        "fields": [
          { "label": "Y-tunnus", "value": "1567535-0", "editable": True },
          { "label": "VAT number", "value": "FI15675350", "editable": True },
          { "label": "EDI number", "value": "003715675350130", "editable": True },
          { "label": "Operator", "value": "OpusCapita Solutions Oy", "editable": True },
          { "label": "Operator number", "value": "E204503", "editable": True }
        ]
      }
    ]
  }
}

def main():
    print(f"Ingesting Billing Instructions to: {DB_CONN}")
    with psycopg.connect(DB_CONN) as conn:
        with conn.cursor() as cur:
            # Overwrite previous uploaded billing/ordering data safely
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

            # 1. Insert core.documents
            doc = PAYLOAD["document"]
            cur.execute("""
                INSERT INTO core.documents (document_type, document_date, source_language, author_name, author_email, subject, raw_text, structured_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING document_id;
            """, (
                doc["document_type"], 
                doc["document_date_iso"], 
                doc["source_language"], 
                doc["author"]["name"], 
                doc["author"]["email"], 
                doc["subject"], 
                doc["original_context"],
                psycopg.types.json.Jsonb(PAYLOAD)
            ))
            doc_id = cur.fetchone()[0]

            # 2. Insert billing_instructions strictly typed
            bi = PAYLOAD["billing_instructions"]
            org = PAYLOAD["organization_identifiers"]
            cur.execute("""
                INSERT INTO core.billing_instructions (
                    document_id, method, condition_text, recipient_organization, recipient_department, 
                    operator_identifier, ovt_identifier, edi_number, reference_code, 
                    po_box, postal_code, city_or_invoice_unit, business_id, vat_number, operator_name
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                doc_id,
                bi["primary_method"]["method"],
                bi["fallback_method"]["condition"],
                bi["primary_method"]["recipient"]["organization"],
                bi["primary_method"]["recipient"]["department"],
                bi["primary_method"]["operator_identifier"],
                bi["primary_method"]["ovt_identifier"],
                org["edi_number"],
                bi["primary_method"]["reference"],
                bi["fallback_method"]["recipient"]["po_box"],
                bi["fallback_method"]["recipient"]["postal_code"],
                bi["fallback_method"]["recipient"]["city_or_invoice_unit"],
                org["business_id_fi"],
                org["vat_number"],
                org["operator"]["name"]
            ))

            # 3. Insert document_entities EAV for dynamic GUI
            gui = PAYLOAD["gui_display"]
            display_order = 0
            for section in gui["sections"]:
                for field in section["fields"]:
                    display_order += 1
                    cur.execute("""
                        INSERT INTO core.document_entities (
                            document_id, entity_type, section_title, label, value, editable, display_order
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        doc_id, 
                        "gui_field", 
                        section["section_title"], 
                        field["label"], 
                        field["value"], 
                        field.get("editable", True),
                        display_order
                    ))
            
            conn.commit()
            print("Successfully ingested billing instructions.")

if __name__ == "__main__":
    main()
