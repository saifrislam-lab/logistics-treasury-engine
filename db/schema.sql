-- =========================================================
-- Carrier Alpha — Canonical Database Schema (v1)
-- Source of truth for logistics treasury engine
-- =========================================================
-- This file reflects:
-- 1) Live Supabase tables
-- 2) Applied constraints and indexes
-- 3) Locked v1 invariants
--
-- Apply changes via Supabase SQL Editor
-- Then commit this file to git
-- =========================================================

-- Required extension (usually already enabled in Supabase)
create extension if not exists "uuid-ossp";

-- =========================================================
-- ENUMS
-- =========================================================

-- Claim lifecycle enum (locked for v1)
-- Lifecycle:
-- DRAFT → SUBMITTED → DISPUTED → RECOVERED | DENIED
do $$
begin
  if not exists (
    select 1
    from pg_type
    where typname = 'claim_status'
  ) then
    create type claim_status as enum (
      'DRAFT',
      'SUBMITTED',
      'DISPUTED',
      'RECOVERED',
      'DENIED'
    );
  end if;
end$$;

-- =========================================================
-- TABLE: shipments
-- Canonical shipment record (1 row per carrier + tracking)
-- =========================================================

create table if not exists public.shipments (
  id uuid primary key default uuid_generate_v4(),

  carrier varchar not null,
  tracking_number varchar not null,

  service_type varchar,
  shipped_at timestamptz,
  promised_delivery timestamptz,
  actual_delivery timestamptz,

  total_charged numeric default 0.00,
  weight_lbs numeric,

  raw_json_data jsonb,  -- full carrier payload for audit evidence

  created_at timestamptz default now()
);

-- Uniqueness: prevents duplicate claims
alter table public.shipments
add constraint shipments_carrier_tracking_unique
unique (carrier, tracking_number);

-- =========================================================
-- TABLE: invoices
-- Carrier invoice ingestion (optional linkage in v1)
-- =========================================================

create table if not exists public.invoices (
  id uuid primary key default uuid_generate_v4(),

  file_name text not null,
  carrier text,

  total_amount numeric,
  status text default 'INGESTED',

  upload_date timestamptz default now()
);

-- =========================================================
-- TABLE: audit_results
-- Deterministic eligibility decision ledger
-- =========================================================

create table if not exists public.audit_results (
  id uuid primary key default uuid_generate_v4(),

  shipment_id uuid not null,

  is_eligible boolean default false,
  variance_amount numeric default 0.00,

  failure_reason text,     -- human-readable explanation
  rule_id varchar,         -- rule that triggered decision

  audited_at timestamptz default now(),

  constraint audit_results_shipment_fk
    foreign key (shipment_id)
    references public.shipments(id)
    on delete cascade
);

-- =========================================================
-- TABLE: claims
-- Operational recovery lifecycle (Recovery Roadmap)
-- =========================================================

create table if not exists public.claims (
  id uuid primary key default uuid_generate_v4(),

  shipment_id uuid not null,
  audit_id uuid,

  status claim_status default 'DRAFT',

  claim_amount numeric,        -- requested refund
  recovery_amount numeric default 0.00,  -- credited by carrier

  carrier_case_number varchar,
  reason text,

  submitted_at timestamptz,
  settled_at timestamptz,
  created_at timestamptz default now(),

  constraint claims_shipment_fk
    foreign key (shipment_id)
    references public.shipments(id)
    on delete cascade,

  constraint claims_audit_fk
    foreign key (audit_id)
    references public.audit_results(id)
    on delete set null
);

-- =========================================================
-- INDEXES (performance + stability)
-- =========================================================

create index if not exists idx_shipments_carrier_tracking
  on public.shipments(carrier, tracking_number);

create index if not exists idx_audit_results_shipment_id
  on public.audit_results(shipment_id);

create index if not exists idx_claims_shipment_id
  on public.claims(shipment_id);

create index if not exists idx_claims_audit_id
  on public.claims(audit_id);

create index if not exists idx_claims_status
  on public.claims(status);

-- =========================================================
-- END OF SCHEMA
-- =========================================================
