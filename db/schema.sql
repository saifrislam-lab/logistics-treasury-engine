-- db/schema.sql
-- Carrier Alpha - Current Supabase schema (reconstructed from information_schema.columns)
-- Source: Supabase public schema table/column listing provided by user
-- NOTE: This is the "as-is" baseline. Constraints/keys are minimal today.

-- Ensure uuid generator exists (Supabase often has this already)
create extension if not exists "uuid-ossp";

-- -------------------------
-- Table: shipments
-- -------------------------
create table if not exists public.shipments (
  id uuid primary key default uuid_generate_v4(),
  tracking_number varchar not null,
  carrier varchar not null,
  service_type varchar,
  shipped_at timestamptz,
  promised_delivery timestamptz,
  actual_delivery timestamptz,
  raw_json_data jsonb,
  created_at timestamptz default now(),
  total_charged numeric default 0.00,
  weight_lbs numeric
);

-- -------------------------
-- Table: invoices
-- -------------------------
create table if not exists public.invoices (
  id uuid primary key default uuid_generate_v4(),
  file_name text not null,
  upload_date timestamptz default now(),
  carrier text,
  total_amount numeric,
  status text default 'INGESTED'
);

-- -------------------------
-- Table: audit_results
-- -------------------------
create table if not exists public.audit_results (
  id uuid primary key default uuid_generate_v4(),
  shipment_id uuid,
  is_eligible boolean default false,
  variance_amount numeric default 0.00,
  failure_reason text,
  rule_id varchar,
  audited_at timestamptz default now()
);

-- -------------------------
-- Enum: claim_status (exists because claims.status is USER-DEFINED)
-- -------------------------
-- This enum already exists in your DB. The exact labels need verification.
-- We'll define the target enum in the "canonicalization" section below.

-- -------------------------
-- Table: claims
-- -------------------------
create table if not exists public.claims (
  id uuid primary key default uuid_generate_v4(),
  shipment_id uuid,
  audit_id uuid,
  status claim_status default 'DRAFT',
  claim_amount numeric,
  recovery_amount numeric default 0.00,
  carrier_case_number varchar,
  submitted_at timestamptz,
  settled_at timestamptz,
  created_at timestamptz default now(),
  reason text
);
