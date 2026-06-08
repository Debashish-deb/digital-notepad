-- Phase 7B — Research imaging viewer: ROIs, overlays, channel presets

CREATE SCHEMA IF NOT EXISTS platform;

CREATE TABLE IF NOT EXISTS platform.image_roi (
    roi_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id text NOT NULL,
    user_email text NOT NULL,
    project text,
    name text NOT NULL,
    description text,
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    geometry jsonb NOT NULL,
    roi_type text NOT NULL DEFAULT 'rectangle',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT image_roi_type_chk CHECK (
        roi_type IN ('rectangle', 'polygon', 'freehand', 'point')
    )
);

CREATE INDEX IF NOT EXISTS idx_image_roi_asset_user
    ON platform.image_roi (asset_id, user_email);

CREATE TABLE IF NOT EXISTS platform.image_overlay (
    overlay_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id text NOT NULL,
    overlay_asset_id text NOT NULL,
    overlay_type text NOT NULL DEFAULT 'cell',
    label text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT image_overlay_type_chk CHECK (
        overlay_type IN ('mesmer', 'stardist', 'cell', 'nucleus', 'heatmap', 'custom')
    )
);

CREATE INDEX IF NOT EXISTS idx_image_overlay_asset
    ON platform.image_overlay (asset_id);

CREATE TABLE IF NOT EXISTS platform.image_channel_preset (
    preset_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email text NOT NULL,
    name text NOT NULL,
    channels jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_image_channel_preset_user
    ON platform.image_channel_preset (user_email);
