-- ===========================================
-- Junior - Production Schema
-- PostgreSQL + pgvector for Supabase
-- ===========================================

create extension if not exists pgcrypto;
create extension if not exists vector;
create extension if not exists pg_trgm;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

-- ============ Users ============
create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    email text unique not null,
    name text not null,
    role text not null default 'user' check (role in ('lawyer', 'student', 'admin', 'user')),
    bar_council_id text,
    preferred_language text not null default 'ENGLISH',
    subscription_tier text not null default 'free' check (subscription_tier in ('free', 'pro', 'enterprise')),
    settings jsonb not null default '{}'::jsonb,
    usage_stats jsonb not null default '{}'::jsonb,
    last_login_at timestamptz,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_users_email on public.users(email);
create index if not exists idx_users_role on public.users(role);
create index if not exists idx_users_active on public.users(is_active) where is_active = true;

-- ============ Documents ============
create table if not exists public.documents (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    court text not null check (court in ('SUPREME_COURT', 'HIGH_COURT', 'DISTRICT_COURT', 'TRIBUNAL', 'OTHER')),
    case_number text not null,
    case_type text check (case_type in ('CIVIL', 'CRIMINAL', 'CONSTITUTIONAL', 'WRIT', 'APPEAL', 'REVIEW', 'OTHER')),
    judgment_date date not null,
    filing_date date,
    judges text[] not null default '{}',
    bench_strength integer not null default 1 check (bench_strength > 0),
    parties jsonb not null default '{"petitioner": [], "respondent": [], "advocates": {"petitioner": [], "respondent": []}}'::jsonb,
    summary text,
    headnotes text,
    full_text text,
    citations_count integer not null default 0,
    cited_by_count integer not null default 0,
    legal_status text not null default 'GOOD_LAW' check (legal_status in ('GOOD_LAW', 'DISTINGUISHED', 'OVERRULED', 'PENDING', 'UNKNOWN')),
    language text not null default 'ENGLISH',
    source_url text,
    pdf_url text,
    doc_hash text unique,
    keywords text[] not null default '{}',
    legal_provisions text[] not null default '{}',
    metadata jsonb not null default '{}'::jsonb,
    view_count integer not null default 0,
    is_landmark boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (case_number, court, judgment_date)
);

create index if not exists idx_documents_status on public.documents(legal_status);
create index if not exists idx_documents_language on public.documents(language);
create index if not exists idx_documents_landmark on public.documents(is_landmark) where is_landmark = true;
create index if not exists idx_documents_judgment_date on public.documents(judgment_date desc);
create index if not exists idx_documents_keywords on public.documents using gin(keywords);
create index if not exists idx_documents_legal_provisions on public.documents using gin(legal_provisions);
create index if not exists idx_documents_metadata on public.documents using gin(metadata);
create index if not exists idx_documents_title_fts on public.documents using gin(to_tsvector('english', coalesce(title, '')));
create index if not exists idx_documents_summary_fts on public.documents using gin(to_tsvector('english', coalesce(summary, '')));

-- ============ Document Chunks ============
create table if not exists public.document_chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references public.documents(id) on delete cascade,
    content text not null,
    page_number integer not null check (page_number >= 1),
    paragraph_number integer,
    chunk_type text not null default 'paragraph' check (chunk_type in ('heading', 'paragraph', 'quote', 'list', 'table')),
    token_count integer not null default 0,
    embedding vector(1024),
    legal_entities jsonb not null default '[]'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (document_id, page_number, paragraph_number, chunk_type)
);

create index if not exists idx_document_chunks_document_id on public.document_chunks(document_id);
create index if not exists idx_document_chunks_page on public.document_chunks(page_number);
create index if not exists idx_document_chunks_metadata on public.document_chunks using gin(metadata);
create index if not exists idx_document_chunks_content_fts on public.document_chunks using gin(to_tsvector('english', coalesce(content, '')));
create index if not exists idx_document_chunks_embedding_cosine on public.document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ============ Citations ============
create table if not exists public.citations (
    id uuid primary key default gen_random_uuid(),
    citing_document_id uuid not null references public.documents(id) on delete cascade,
    cited_document_id uuid not null references public.documents(id) on delete cascade,
    citation_type text not null check (citation_type in ('FOLLOWS', 'DISTINGUISHES', 'OVERRULES', 'APPROVES', 'DISAPPROVES', 'CONSIDERS', 'REFERS', 'MENTIONS')),
    citation_strength text not null default 'MEDIUM' check (citation_strength in ('STRONG', 'MEDIUM', 'WEAK')),
    paragraph_in_citing integer,
    paragraph_in_cited integer,
    context text,
    extracted_quote text,
    is_binding boolean not null default false,
    created_at timestamptz not null default now(),
    unique (citing_document_id, cited_document_id, citation_type)
);

create index if not exists idx_citations_citing on public.citations(citing_document_id);
create index if not exists idx_citations_cited on public.citations(cited_document_id);

-- ============ Chat ============
create table if not exists public.chat_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references public.users(id) on delete set null,
    title text,
    session_type text not null default 'general' check (session_type in ('general', 'research', 'drafting', 'analysis')),
    case_context text,
    messages_count integer not null default 0,
    total_tokens integer not null default 0,
    is_archived boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_chat_sessions_user_id on public.chat_sessions(user_id);
create index if not exists idx_chat_sessions_updated on public.chat_sessions(updated_at desc) where is_archived = false;

create table if not exists public.chat_messages (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.chat_sessions(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    citations jsonb not null default '[]'::jsonb,
    translations jsonb not null default '{}'::jsonb,
    token_count integer not null default 0,
    model_used text,
    processing_time_ms integer,
    feedback_rating integer check (feedback_rating is null or (feedback_rating between 1 and 5)),
    feedback_comment text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_chat_messages_session_id on public.chat_messages(session_id);
create index if not exists idx_chat_messages_created_at on public.chat_messages(created_at desc);

-- ============ Triggers ============
drop trigger if exists trg_users_set_updated_at on public.users;
create trigger trg_users_set_updated_at
before update on public.users
for each row execute function public.set_updated_at();

drop trigger if exists trg_documents_set_updated_at on public.documents;
create trigger trg_documents_set_updated_at
before update on public.documents
for each row execute function public.set_updated_at();

drop trigger if exists trg_chat_sessions_set_updated_at on public.chat_sessions;
create trigger trg_chat_sessions_set_updated_at
before update on public.chat_sessions
for each row execute function public.set_updated_at();

-- ============ Vector Search RPC ============
create or replace function public.match_document_chunks(
    query_embedding vector(1024),
    match_threshold double precision default 0.3,
    match_count integer default 10,
    filter_courts text[] default null,
    filter_statuses text[] default null,
    filter_date_from date default null,
    filter_date_to date default null
)
returns table (
    id uuid,
    document_id uuid,
    content text,
    page_number integer,
    paragraph_number integer,
    metadata jsonb,
    similarity double precision,
    title text,
    case_number text,
    court text,
    judgment_date date
)
language sql
stable
as $$
    select
        dc.id,
        dc.document_id,
        dc.content,
        dc.page_number,
        dc.paragraph_number,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) as similarity,
        d.title,
        d.case_number,
        d.court,
        d.judgment_date
    from public.document_chunks as dc
    inner join public.documents as d on d.id = dc.document_id
    where dc.embedding is not null
      and 1 - (dc.embedding <=> query_embedding) >= match_threshold
      and (filter_courts is null or d.court = any(filter_courts))
      and (filter_statuses is null or d.legal_status = any(filter_statuses))
      and (filter_date_from is null or d.judgment_date >= filter_date_from)
      and (filter_date_to is null or d.judgment_date <= filter_date_to)
    order by dc.embedding <=> query_embedding
    limit match_count;
$$;

comment on function public.match_document_chunks(vector, double precision, integer, text[], text[], date, date)
is 'Semantic retrieval over document_chunks using pgvector cosine similarity.';

-- ============ Row Level Security ============
alter table public.users enable row level security;
alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;
alter table public.citations enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

drop policy if exists documents_read_authenticated on public.documents;
create policy documents_read_authenticated
on public.documents
for select
to authenticated
using (true);

drop policy if exists document_chunks_read_authenticated on public.document_chunks;
create policy document_chunks_read_authenticated
on public.document_chunks
for select
to authenticated
using (true);

drop policy if exists citations_read_authenticated on public.citations;
create policy citations_read_authenticated
on public.citations
for select
to authenticated
using (true);

drop policy if exists chat_sessions_service_or_owner on public.chat_sessions;
create policy chat_sessions_service_or_owner
on public.chat_sessions
for all
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists chat_messages_service_or_owner on public.chat_messages;
create policy chat_messages_service_or_owner
on public.chat_messages
for all
to authenticated
using (
    exists (
        select 1
        from public.chat_sessions cs
        where cs.id = session_id and cs.user_id = auth.uid()
    )
)
with check (
    exists (
        select 1
        from public.chat_sessions cs
        where cs.id = session_id and cs.user_id = auth.uid()
    )
);
