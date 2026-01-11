-- ============================================================
-- Carrier Alpha — Canonical Database Schema v1 (Step 5 updated)
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
-- SERVICE COMMITMENTS (Guarantee Rules Engine - v1)
-- ============================================================

create table if not exists public.service_commitments (
  id uuid primary key default uuid_generate_v4(),

  carrier varchar not null,
  service_type varchar not null,
  guaranteed boolean not null default true,

  commit_time_local time,
  commit_day_type varchar,

  valid_from date not null default current_date,
  valid_to date,

  created_at timestamptz default now(),

  constraint service_commitments_unique
    unique (carrier, service_type, valid_from)
);

-- ============================================================
-- EXCEPTION RULES (Caveat #2 fix - deterministic)
-- ============================================================

create table if not exists public.exception_rules (
  id uuid primary key default uuid_generate_v4(),
  carrier text not null,
  match_type text not null,      -- 'CODE' | 'KEYWORD'
  match_value text not null,     -- e.g. 'WX', 'WEATHER'
  excusable boolean not null,
  category text,                 -- WEATHER / ADDRESS / FORCE_MAJEURE / OTHER
  created_at timestamptz default now(),
  unique (carrier, match_type, match_value)
);

-- ============================================================
-- AUDIT RESULTS
-- Exactly ONE audit per shipment (deterministic verdict)
-- Includes Caveat #1 (timezone) and Caveat #2 (exceptions)
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

  audited_at timestamptz default now(),

  -- Caveat #1: timezone
  timezone_assumption text,
  timezone_confidence numeric,

  -- Caveat #2: exceptions
  exception_category text,
  exception_signal text
);

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

alter table public.claims
add constraint claims_one_per_shipment
unique (shipment_id);

create index if not exists idx_claims_shipment
  on public.claims (shipment_id);

create index if not exists idx_claims_status
  on public.claims (status);

-- ============================================================
-- CANONICAL VIEW: v_audit_truth (Single source of truth)
-- ============================================================

create or replace view public.v_audit_truth as
select
  s.id as shipment_id,
  s.carrier,
  s.tracking_number,
  s.service_type,
  s.shipped_at,
  s.promised_delivery,
  s.actual_delivery,
  s.total_charged,
  s.weight_lbs,
  ar.is_eligible,
  ar.variance_amount,
  ar.failure_reason,
  ar.rule_id,
  ar.audited_at,
  ar.timezone_assumption,
  ar.timezone_confidence,
  ar.exception_category,
  ar.exception_signal,
  c.id as claim_id,
  c.status as claim_status,
  c.claim_amount,
  c.recovery_amount,
  c.carrier_case_number,
  c.submitted_at,
  c.settled_at,
  c.created_at as claim_created_at,
  c.reason as claim_reason
from public.shipments s
join public.audit_results ar on ar.shipment_id = s.id
left join public.claims c on c.shipment_id = s.id;
