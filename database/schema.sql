CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE source (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    publisher VARCHAR(255),
    url TEXT NOT NULL,
    license VARCHAR(255),
    retrieved_at TIMESTAMPTZ,
    source_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_source_url UNIQUE (url)
);

CREATE INDEX ix_source_publisher ON source (publisher);

CREATE TABLE entity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(80) NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    external_id VARCHAR(255),
    normalized_key VARCHAR(500),
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    entity_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_entity_status CHECK (status IN ('active', 'inactive', 'deprecated')),
    CONSTRAINT uq_entity_type_external_id UNIQUE (entity_type, external_id)
);

CREATE INDEX ix_entity_type ON entity (entity_type);
CREATE INDEX ix_entity_name ON entity (name);

CREATE TABLE dataset (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES source(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(100) NOT NULL,
    dataset_url TEXT NOT NULL,
    content_hash VARCHAR(128),
    loaded_at TIMESTAMPTZ,
    dataset_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dataset_source_name_version UNIQUE (source_id, name, version)
);

CREATE INDEX ix_dataset_source_id ON dataset (source_id);

CREATE TABLE import_job (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES dataset(id) ON DELETE RESTRICT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    records_processed INTEGER NOT NULL DEFAULT 0,
    error_log TEXT,
    job_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_import_job_status CHECK (
        status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')
    ),
    CONSTRAINT ck_import_job_records_processed CHECK (records_processed >= 0)
);

CREATE INDEX ix_import_job_dataset_id ON import_job (dataset_id);
CREATE INDEX ix_import_job_status ON import_job (status);

CREATE TABLE source_record (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES source(id) ON DELETE RESTRICT,
    dataset_id UUID NOT NULL REFERENCES dataset(id) ON DELETE RESTRICT,
    external_id VARCHAR(255) NOT NULL,
    record_type VARCHAR(120) NOT NULL,
    payload_hash VARCHAR(128) NOT NULL,
    raw_payload JSONB NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL,
    error_log TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_source_record_status CHECK (
        status IN ('ingested', 'normalized', 'validated', 'published', 'rejected', 'disputed', 'withdrawn')
    ),
    CONSTRAINT uq_source_record_dataset_type_external_id UNIQUE (
        dataset_id,
        record_type,
        external_id
    )
);

CREATE INDEX ix_source_record_source_id ON source_record (source_id);
CREATE INDEX ix_source_record_dataset_id ON source_record (dataset_id);
CREATE INDEX ix_source_record_status ON source_record (status);
CREATE INDEX ix_source_record_payload_hash ON source_record (payload_hash);

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES source(id) ON DELETE RESTRICT,
    dataset_id UUID REFERENCES dataset(id) ON DELETE RESTRICT,
    source_record_id UUID REFERENCES source_record(id) ON DELETE RESTRICT,
    claim_id UUID,
    title VARCHAR(500) NOT NULL,
    url TEXT NOT NULL,
    published_at DATE,
    excerpt TEXT,
    evidence_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_evidence_source_record_url UNIQUE (source_record_id, url)
);

CREATE INDEX ix_evidence_source_id ON evidence (source_id);
CREATE INDEX ix_evidence_dataset_id ON evidence (dataset_id);
CREATE INDEX ix_evidence_source_record_id ON evidence (source_record_id);
CREATE INDEX ix_evidence_claim_id ON evidence (claim_id);
CREATE INDEX ix_evidence_published_at ON evidence (published_at);

CREATE TABLE claim (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_entity_id UUID NOT NULL REFERENCES entity(id) ON DELETE RESTRICT,
    predicate VARCHAR(120) NOT NULL,
    object_entity_id UUID REFERENCES entity(id) ON DELETE RESTRICT,
    object_value JSONB,
    source_record_id UUID NOT NULL REFERENCES source_record(id) ON DELETE RESTRICT,
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE RESTRICT,
    valid_from DATE,
    valid_to DATE,
    confidence NUMERIC(5, 4) NOT NULL,
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_claim_confidence_range CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT ck_claim_status CHECK (
        status IN ('ingested', 'normalized', 'validated', 'published', 'rejected', 'disputed', 'withdrawn')
    ),
    CONSTRAINT ck_claim_has_object CHECK (object_entity_id IS NOT NULL OR object_value IS NOT NULL),
    CONSTRAINT ck_claim_valid_date_range CHECK (
        valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from
    )
);

ALTER TABLE evidence
ADD CONSTRAINT fk_evidence_claim
FOREIGN KEY (claim_id)
REFERENCES claim(id)
ON DELETE SET NULL;

CREATE INDEX ix_claim_subject_entity_id ON claim (subject_entity_id);
CREATE INDEX ix_claim_object_entity_id ON claim (object_entity_id);
CREATE INDEX ix_claim_source_record_id ON claim (source_record_id);
CREATE INDEX ix_claim_evidence_id ON claim (evidence_id);
CREATE INDEX ix_claim_predicate ON claim (predicate);
CREATE INDEX ix_claim_status ON claim (status);

CREATE TABLE relationship_public (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID NOT NULL REFERENCES entity(id) ON DELETE RESTRICT,
    target_entity_id UUID NOT NULL REFERENCES entity(id) ON DELETE RESTRICT,
    relationship_type VARCHAR(80) NOT NULL,
    claim_id UUID NOT NULL REFERENCES claim(id) ON DELETE RESTRICT,
    published_at TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL,
    relationship_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_relationship_public_status CHECK (
        status IN ('ingested', 'normalized', 'validated', 'published', 'rejected', 'disputed', 'withdrawn')
    ),
    CONSTRAINT uq_relationship_public_claim_id UNIQUE (claim_id)
);

CREATE INDEX ix_relationship_public_source_entity_id ON relationship_public (source_entity_id);
CREATE INDEX ix_relationship_public_target_entity_id ON relationship_public (target_entity_id);
CREATE INDEX ix_relationship_public_type ON relationship_public (relationship_type);
CREATE INDEX ix_relationship_public_claim_id ON relationship_public (claim_id);
CREATE INDEX ix_relationship_public_status ON relationship_public (status);

CREATE TABLE change_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_table VARCHAR(120) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(30) NOT NULL,
    previous_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_change_log_action CHECK (action IN ('insert', 'update', 'delete'))
);

CREATE INDEX ix_change_log_entity ON change_log (entity_table, entity_id);
