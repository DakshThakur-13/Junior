-- ===========================================
-- Junior - Database Schema (v2)
-- Postgres + pgvector (Supabase)
-- ===========================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============ Users ============
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('lawyer', 'student', 'admin', 'user')),
    bar_council_id TEXT,
    preferred_language TEXT DEFAULT 'ENGLISH',
    subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'enterprise')),
    settings JSONB DEFAULT '{}',
    usage_stats JSONB DEFAULT '{}',
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active) WHERE is_active = true;

-- ============ Documents ============
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    court TEXT NOT NULL CHECK (court IN ('SUPREME_COURT', 'HIGH_COURT', 'DISTRICT_COURT', 'TRIBUNAL', 'OTHER')),
    case_number TEXT NOT NULL,
    case_type TEXT CHECK (case_type IN ('CIVIL', 'CRIMINAL', 'CONSTITUTIONAL', 'WRIT', 'APPEAL', 'REVIEW', 'OTHER')),
    judgment_date DATE NOT NULL,
    filing_date DATE,
    judges TEXT[] DEFAULT '{}',
    bench_strength INTEGER DEFAULT 1,
    parties JSONB DEFAULT '{"petitioner": [], "respondent": [], "advocates": {"petitioner": [], "respondent": []}}',
    summary TEXT,
    headnotes TEXT,
    full_text TEXT,
    citations_count INTEGER DEFAULT 0,
    cited_by_count INTEGER DEFAULT 0,
    legal_status TEXT DEFAULT 'GOOD_LAW' CHECK (legal_status IN ('GOOD_LAW', 'DISTINGUISHED', 'OVERRULED', 'PENDING', 'UNKNOWN')),
    language TEXT DEFAULT 'ENGLISH',
    source_url TEXT,
    pdf_url TEXT,
    doc_hash TEXT UNIQUE,
    keywords TEXT[],
    legal_provisions TEXT[],
    metadata JSONB DEFAULT '{}',
    view_count INTEGER DEFAULT 0,
    is_landmark BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (case_number, court, judgment_date)
);

CREATE INDEX IF NOT EXISTS idx_documents_legal_status ON documents(legal_status);
CREATE INDEX IF NOT EXISTS idx_documents_language ON documents(language);
CREATE INDEX IF NOT EXISTS idx_documents_is_landmark ON documents(is_landmark) WHERE is_landmark = true;
CREATE INDEX IF NOT EXISTS idx_documents_keywords ON documents USING gin(keywords);
CREATE INDEX IF NOT EXISTS idx_documents_legal_provisions ON documents USING gin(legal_provisions);
CREATE INDEX IF NOT EXISTS idx_documents_title_search ON documents USING gin(to_tsvector('english', coalesce(title, '')));
CREATE INDEX IF NOT EXISTS idx_documents_summary_search ON documents USING gin(to_tsvector('english', coalesce(summary, '')));

-- ============ Document Chunks (Embeddings) ============
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    paragraph_number INTEGER,
    chunk_type TEXT DEFAULT 'paragraph' CHECK (chunk_type IN ('heading', 'paragraph', 'quote', 'list', 'table')),
    token_count INTEGER DEFAULT 0,
    embedding vector(384),
    legal_entities JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_page ON document_chunks(page_number);
CREATE INDEX IF NOT EXISTS idx_document_chunks_content_search ON document_chunks USING gin(to_tsvector('english', coalesce(content, '')));
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============ Citations (Case Relationships) ============
CREATE TABLE IF NOT EXISTS citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citing_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    cited_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    citation_type TEXT NOT NULL CHECK (citation_type IN ('FOLLOWS', 'DISTINGUISHES', 'OVERRULES', 'APPROVES', 'DISAPPROVES', 'CONSIDERS', 'REFERS', 'MENTIONS')),
    citation_strength TEXT DEFAULT 'MEDIUM' CHECK (citation_strength IN ('STRONG', 'MEDIUM', 'WEAK')),
    paragraph_in_citing INTEGER,
    paragraph_in_cited INTEGER,
    context TEXT,
    extracted_quote TEXT,
    is_binding BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (citing_document_id, cited_document_id, citation_type)
);

CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_document_id);
CREATE INDEX IF NOT EXISTS idx_citations_cited ON citations(cited_document_id);

-- ============ Chat ============
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    title TEXT,
    session_type TEXT DEFAULT 'general' CHECK (session_type IN ('general', 'research', 'drafting', 'analysis')),
    case_context TEXT,
    messages_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_active ON chat_sessions(updated_at DESC) WHERE is_archived = false;

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    translations JSONB DEFAULT '{}',
    token_count INTEGER DEFAULT 0,
    model_used TEXT,
    processing_time_ms INTEGER,
    feedback_rating INTEGER CHECK (feedback_rating IS NULL OR (feedback_rating >= 1 AND feedback_rating <= 5)),
    feedback_comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at DESC);

-- ============ Vector Search RPC ============
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 10,
    filter_court text DEFAULT NULL,
    filter_date_from date DEFAULT NULL,
    filter_date_to date DEFAULT NULL
)
RETURNS TABLE (
    chunk_id uuid,
    document_id uuid,
    content text,
    similarity float,
    document_title text,
    case_number text,
    court text,
    judgment_date date
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    dc.id as chunk_id,
    dc.document_id,
    dc.content,
    (1 - (dc.embedding <=> query_embedding)) as similarity,
    d.title as document_title,
    d.case_number,
    d.court,
    d.judgment_date
  FROM document_chunks dc
  JOIN documents d ON d.id = dc.document_id
  WHERE dc.embedding IS NOT NULL
    AND (1 - (dc.embedding <=> query_embedding)) >= match_threshold
    AND (filter_court IS NULL OR d.court = filter_court)
    AND (filter_date_from IS NULL OR d.judgment_date >= filter_date_from)
    AND (filter_date_to IS NULL OR d.judgment_date <= filter_date_to)
  ORDER BY dc.embedding <=> query_embedding
  LIMIT match_count;
$$;
-- ===========================================
-- Junior - AI Legal Assistant Database Schema
-- Version: 2.0
-- Database: Supabase (PostgreSQL + pgvector)
-- ===========================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- For text search

-- ============ Users Table ============
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'lawyer' CHECK (role IN ('lawyer', 'judge', 'student', 'admin')),
    -- ===========================================
    -- Junior - Database Schema (v2)
    -- Postgres + pgvector (Supabase)
    -- ===========================================

    CREATE EXTENSION IF NOT EXISTS pgcrypto;
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        role TEXT DEFAULT 'user' CHECK (role IN ('lawyer', 'student', 'admin', 'user')),
        bar_council_id TEXT,
        preferred_language TEXT DEFAULT 'ENGLISH',
        subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'enterprise')),
        settings JSONB DEFAULT '{}',
        usage_stats JSONB DEFAULT '{}',
        last_login_at TIMESTAMPTZ,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
    CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active) WHERE is_active = true;

    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title TEXT NOT NULL,
        court TEXT NOT NULL CHECK (court IN ('SUPREME_COURT', 'HIGH_COURT', 'DISTRICT_COURT', 'TRIBUNAL', 'OTHER')),
        case_number TEXT NOT NULL,
        case_type TEXT CHECK (case_type IN ('CIVIL', 'CRIMINAL', 'CONSTITUTIONAL', 'WRIT', 'APPEAL', 'REVIEW', 'OTHER')),
        judgment_date DATE NOT NULL,
        filing_date DATE,
        judges TEXT[] DEFAULT '{}',
        bench_strength INTEGER DEFAULT 1,
        parties JSONB DEFAULT '{"petitioner": [], "respondent": [], "advocates": {"petitioner": [], "respondent": []}}',
        summary TEXT,
        headnotes TEXT,
        full_text TEXT,
        citations_count INTEGER DEFAULT 0,
        cited_by_count INTEGER DEFAULT 0,
        legal_status TEXT DEFAULT 'GOOD_LAW' CHECK (legal_status IN ('GOOD_LAW', 'DISTINGUISHED', 'OVERRULED', 'PENDING', 'UNKNOWN')),
        language TEXT DEFAULT 'ENGLISH',
        source_url TEXT,
        pdf_url TEXT,
        doc_hash TEXT UNIQUE,
        keywords TEXT[],
        legal_provisions TEXT[],
        metadata JSONB DEFAULT '{}',
        view_count INTEGER DEFAULT 0,
        is_landmark BOOLEAN DEFAULT false,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (case_number, court, judgment_date)
    );

    CREATE INDEX IF NOT EXISTS idx_documents_legal_status ON documents(legal_status);
    CREATE INDEX IF NOT EXISTS idx_documents_language ON documents(language);
    CREATE INDEX IF NOT EXISTS idx_documents_is_landmark ON documents(is_landmark) WHERE is_landmark = true;
    CREATE INDEX IF NOT EXISTS idx_documents_keywords ON documents USING gin(keywords);
    CREATE INDEX IF NOT EXISTS idx_documents_legal_provisions ON documents USING gin(legal_provisions);
    CREATE INDEX IF NOT EXISTS idx_documents_title_search ON documents USING gin(to_tsvector('english', coalesce(title, '')));
    CREATE INDEX IF NOT EXISTS idx_documents_summary_search ON documents USING gin(to_tsvector('english', coalesce(summary, '')));

    CREATE TABLE IF NOT EXISTS document_chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        paragraph_number INTEGER,
        chunk_type TEXT DEFAULT 'paragraph' CHECK (chunk_type IN ('heading', 'paragraph', 'quote', 'list', 'table')),
        token_count INTEGER DEFAULT 0,
        embedding vector(384),
        legal_entities JSONB DEFAULT '[]',
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
    CREATE INDEX IF NOT EXISTS idx_document_chunks_page ON document_chunks(page_number);
    CREATE INDEX IF NOT EXISTS idx_document_chunks_content_search ON document_chunks USING gin(to_tsvector('english', coalesce(content, '')));
    CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

    -- ============ Citations (Case Relationships) ============

-- Create vector index for similarity search (IVFFlat for fast approximate search)
CREATE INDEX idx_document_chunks_embedding ON document_chunks 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_page ON document_chunks(page_number);
CREATE INDEX idx_document_chunks_content_search ON document_chunks USING gin(to_tsvector('english', content)
CREATE INDEX idx_documents_legal_status ON documents(legal_status);
CREATE INDEX idx_documents_language ON documents(language);
CREATE INDEX idx_documents_is_landmark ON documents(is_landmark) WHERE is_landmark = true;
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (citing_document_id, cited_document_id, citation_type)
CREATE INDEX idx_documents_keywords ON documents USING gin(keywords);

    CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_document_id);
    CREATE INDEX IF NOT EXISTS idx_citations_cited ON citations(cited_document_id);

    -- ============ Chat Sessions ============
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        title TEXT,
        session_type TEXT DEFAULT 'general' CHECK (session_type IN ('general', 'research', 'drafting', 'analysis')),
        case_context TEXT,
        messages_count INTEGER DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        is_archived BOOLEAN DEFAULT false,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_chat_sessions_active ON chat_sessions(updated_at DESC) WHERE is_archived = false;

    -- ============ Chat Messages ============
    CREATE TABLE IF NOT EXISTS chat_messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
        content TEXT NOT NULL,
        citations JSONB DEFAULT '[]',
        translations JSONB DEFAULT '{}',
        token_count INTEGER DEFAULT 0,
        model_used TEXT,
        processing_time_ms INTEGER,
        feedback_rating INTEGER CHECK (feedback_rating IS NULL OR (feedback_rating >= 1 AND feedback_rating <= 5)),
        feedback_comment TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
    CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at DESC);

    -- ============ Vector Search RPC ============
    CREATE OR REPLACE FUNCTION match_document_chunks(
        query_embedding vector(384),
        match_threshold float DEFAULT 0.3,
        match_count int DEFAULT 10,
        filter_court text DEFAULT NULL,
        filter_date_from date DEFAULT NULL,
        filter_date_to date DEFAULT NULL
    )
    RETURNS TABLE (
        chunk_id uuid,
        document_id uuid,
        content text,
        similarity float,
        document_title text,
        case_number text,
        court text,
        judgment_date date
    )
    LANGUAGE sql
    STABLE
    AS $$
      SELECT
        dc.id as chunk_id,
        dc.document_id,
        dc.content,
        (1 - (dc.embedding <=> query_embedding)) as similarity,
        d.title as document_title,
        d.case_number,
        d.court,
        d.judgment_date
      FROM document_chunks dc
      JOIN documents d ON d.id = dc.document_id
      WHERE dc.embedding IS NOT NULL
        AND (1 - (dc.embedding <=> query_embedding)) >= match_threshold
        AND (filter_court IS NULL OR d.court = filter_court)
        AND (filter_date_from IS NULL OR d.judgment_date >= filter_date_from)
        AND (filter_date_to IS NULL OR d.judgment_date <= filter_date_to)
      ORDER BY dc.embedding <=> query_embedding
      LIMIT match_count;
    $$;
CREATE INDEX idx_documents_legal_provisions ON documents USING gin(legal_provisions);
CREATE INDEX idx_documents_title_search ON documents USING gin(to_tsvector('english', title));
CREATE INDEX idx_documents_summary_search ON documents USING gin(to_tsvector('english', summary));

-- ============ Document Chunks Table (with embeddings) ============
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    paragraph_number INTEGER,
    embedding vector(1536), -- OpenAI embedding dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector index for similarity search
CREATE INDEX idx_document_chunks(Case Relationships) ============
CREATE TABLE IF NOT EXISTS citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citing_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    cited_document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    citation_type TEXT NOT NULL CHECK (citation_type IN ('FOLLOWS', 'DISTINGUISHES', 'OVERRULES', 'APPROVES', 'DISAPPROVES', 'CONSIDERS', 'REFERS', 'MENTIONS')),
    citation_strength TEXT DEFAULT 'MEDIUM' CHECK (citation_strength IN ('STRONG', 'MEDIUM', 'WEAK')),
    paragraph_in_citing INTEGER,
    paragraph_in_cited INTEGER,
    context TEXT,
    extracted_quote TEXT,
    is_binding BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_citation UNIQUE(citing_document_id, cited_document_id, paragraph_in_citing)
);

CREATE INDEX idx_citations_citing ON citations(citing_document_id);
CREATE INDEX idx_citations_cited ON citations(cited_document_id);
CREATE INDEX idx_citations_type ON citations(citation_type);
CREATE INDEX idx_citations_binding ON citations(is_binding) WHERE is_binding = true
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_citations_citing ON citations(citing_document_id);
CREATE INDEX idx_citations_cited ON citations(cited_document_id);
session_type TEXT DEFAULT 'RESEARCH' CHECK (session_type IN ('RESEARCH', 'DRAFTING', 'ANALYSIS', 'TRANSLATION', 'CONSULTATION')),
    case_context JSONB DEFAULT '{}', -- Stores related case info
    messages_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_type ON chat_sessions(session_type);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX idx_chat_sessions_active ON chat_sessions(user_id, updated_at DESC) WHERE is_archived = false
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_ CHECK (role IN ('USER', 'ASSISTANT', 'SYSTEM')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]', -- [{document_id, page, paragraph, relevance}]
    translations JSONB DEFAULT '{}', -- {hindi: "...", marathi: "..."}
    token_count INTEGER DEFAULT 0,
    model_used TEXT,
    processing_time_ms INTEGER,
    feedback_rating INTEGER CHECK (feedback_rating >= 1 AND feedback_rating <= 5),
    feedback_comment TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_role ON chat_messages(role
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);384), -- Updated to match BAAI/bge-small-en-v1.5
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    filter_court TEXT DEFAULT NULL,
    filter_date_from DATE DEFAULT NULL,
    filter_date_to DATE DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    content TEXT,
    page_number INTEGER,
    paragraph_number INTEGER,
    metadata JSONB,
    similarity FLOAT,
    document_title TEXT,
    case_number TEXT,
    court TEXT,
    judgment_date DATE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.content,
        dc.page_number,
        dc.paragraph_number,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        d.title,
        d.case_number,
        d.court,
        d.judgment_date
    FROM document_chunks dc
    INNER JOIN documents d ON dc.document_id = d.id
    WHERE 
        1 - (dc.embedding <=> query_embedding) > match_threshold
        AND (filter_court IS NULL OR d.court = filter_court)
        AND (filter_date_from IS NULL OR d.judgment_date >= filter_date_from)
        AND (filter_date_to IS NULL OR d.judgment_date <= filter_date_to)
        dc.content,
        dc.page_number,
        dc.paragraph_number,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============ Row Level Security (RLS) ============
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Users can only read their own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (auth.uid() = id);

-- Documents are readable by all authenticated users (public case law)
CREATE POLICY "Documents are viewable by authenticated users" ON documents
    FOR SELECT USING (auth.role() = 'authenticated');

-- Document chunks follow document policy
CREATE POLICY "Document chunks are viewable by authenticated users" ON document_chunks
    FOR SELECT USING (auth.role() = 'authenticated');

-- Users can only access their own chat sessions
CREATE POLICY "Users can access own chat sessions" ON chat_sessions
    FOR ALL USING (auth.uid() = user_id);

-- Chat messages follow session policy
CREATE POLICY "Users can access own chat messages" ON chat_messages
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM chat_sessions 
            WHERE chat_sessions.id = chat_messages.session_id 
            AND chat_sessions.user_id = auth.uid()
        )
    );

-- ============ Triggers for updated_at ============
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
