CREATE TABLE IF NOT EXISTS core.documents (
  document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_type text NOT NULL,
  document_date date,
  source_language text,
  author_name text,
  author_email text,
  subject text,
  raw_text text,
  structured_json jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.document_entities (
  entity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES core.documents(document_id) ON DELETE CASCADE,
  entity_type text NOT NULL,
  label text NOT NULL,
  value text,
  normalized_value text,
  editable boolean DEFAULT true,
  section_title text,
  display_order integer DEFAULT 0
);

CREATE TABLE IF NOT EXISTS core.billing_instructions (
  billing_instruction_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES core.documents(document_id) ON DELETE CASCADE,
  method text,
  condition_text text,
  recipient_organization text,
  recipient_department text,
  operator_identifier text,
  ovt_identifier text,
  edi_number text,
  reference_code text,
  po_box text,
  postal_code text,
  city_or_invoice_unit text,
  business_id text,
  vat_number text,
  operator_name text
);
