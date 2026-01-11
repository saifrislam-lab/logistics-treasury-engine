-- ============================================================
-- Carrier Alpha — Canonical Database Schema v1
-- Purpose: Treasury-grade logistics audit & recovery ledger
-- ============================================================

-- Enable UUIDs
create extension if not exists "uuid-ossp";

-- ============================================================
-- ENUMS
-- ============================================================

do $$
begin
  if not exists (select 1 from pg_type where typname = 'claim_status') then
    create type claim_status as enum (
      'DRAFT',
      'SUBMITTED',
      'DISPUTED',
      'RECOVERED',
      'DENIED'
    );
  end if;
end$$;

-- ============================================================
-- SHIPMENTS
-- One row per (carrier, tracking_number)
-- ============================================================

create table if not exists public.shipments (
  id uuid primary key default uuid_generate_v4(),

  tracking_number varchar not null,
  carrier varchar not null,

  service_type varchar,
  shipped_at timestamptz,
  promised_delivery timestamptz,
  actual_delivery timestamptz,

  total_charged numeric default 0.00,
  weight_lbs numeric,

  raw_json_data jsonb,

  created_at timestamptz default now(),

  constraint shipments_carrier_tracking_unique
    unique (carrier, tracking_number)
);

create index if not exists idx_shipments_tracking
  on public.shipments (tracking_number);

create index if not exists idx_shipments_carrier
  on public.shipments (carrier);

-- ============================================================
-- INVOICES
-- ============================================================

create table if not exists public.invoices (
  id uuid primary key default uuid_generate_v4(),

  file_name text not null,
  carrier text,
  total_amount numeric,

  status text default 'INGESTED',

  upload_date timestamptz default now()
);

-- ============================================================
-- AUDIT RESULTS
-- Exactly ONE audit per shipment (deterministic verdict)
-- ============================================================

create table if not exists public.audit_results (
  id uuid primary key default uuid_generate_v4(),

  shipment_id uuid
    references public.shipments(id)
    on delete cascade,

  is_eligible boolean default false,
  variance_amount numeric default 0.00,

  failure_reason text,
  rule_id varchar,

  audited_at timestamptz default now()
);

-- HARD INVARIANT: one audit per shipment
alter table public.audit_results
add constraint audit_results_one_per_shipment
unique (shipment_id);

create index if not exists idx_audit_results_shipment
  on public.audit_results (shipment_id);

-- ============================================================
-- CLAIMS
-- Exactly ONE claim per shipment
-- ============================================================

create table if not exists public.claims (
  id uuid primary key default uuid_generate_v4(),

  shipment_id uuid
    references public.shipments(id)
    on delete cascade,

  audit_id uuid
    references public.audit_results(id)
    on delete restrict,

  status claim_status default 'DRAFT',

  claim_amount numeric,
  recovery_amount numeric default 0.00,

  carrier_case_number varchar,
  reason text,

  submitted_at timestamptz,
  settled_at timestamptz,

  created_at timestamptz default now()
);

-- HARD INVARIANT: one claim per shipment
alter table public.claims
add constraint claims_one_per_shipment
unique (shipment_id);

create index if not exists idx_claims_shipment
  on public.claims (shipment_id);

create index if not exists idx_claims_status
  on public.claims (status);

-- ============================================================
-- END OF SCHEMA
-- ============================================================
