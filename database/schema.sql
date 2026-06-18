CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE source (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,

    publisher TEXT,

    url TEXT,

    license TEXT,

    retrieved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE entity (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    entity_type TEXT NOT NULL,

    name TEXT NOT NULL,

    description TEXT,

    external_id TEXT,

    status TEXT,

    created_at TIMESTAMP DEFAULT NOW(),

    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_entity_type
ON entity(entity_type);

CREATE INDEX idx_entity_name
ON entity(name);

CREATE TABLE relationship (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_entity_id UUID NOT NULL,

    target_entity_id UUID NOT NULL,

    relationship_type TEXT NOT NULL,

    start_date DATE,

    end_date DATE,

    notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_source_entity
        FOREIGN KEY (source_entity_id)
        REFERENCES entity(id),

    CONSTRAINT fk_target_entity
        FOREIGN KEY (target_entity_id)
        REFERENCES entity(id)
);

CREATE INDEX idx_relationship_source
ON relationship(source_entity_id);

CREATE INDEX idx_relationship_target
ON relationship(target_entity_id);

CREATE INDEX idx_relationship_type
ON relationship(relationship_type);

CREATE TABLE evidence (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    relationship_id UUID NOT NULL,

    source_id UUID NOT NULL,

    title TEXT,

    url TEXT,

    published_at DATE,

    excerpt TEXT,

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_relationship
        FOREIGN KEY (relationship_id)
        REFERENCES relationship(id),

    CONSTRAINT fk_source
        FOREIGN KEY (source_id)
        REFERENCES source(id)
);

CREATE TABLE dataset (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_id UUID,

    name TEXT NOT NULL,

    description TEXT,

    version TEXT,

    dataset_url TEXT,

    loaded_at TIMESTAMP,

    CONSTRAINT fk_dataset_source
        FOREIGN KEY (source_id)
        REFERENCES source(id)
);

CREATE TABLE import_job (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    dataset_id UUID,

    started_at TIMESTAMP,

    finished_at TIMESTAMP,

    status TEXT,

    records_processed INTEGER,

    error_log TEXT,

    CONSTRAINT fk_import_dataset
        FOREIGN KEY (dataset_id)
        REFERENCES dataset(id)
);

CREATE TABLE change_log (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    entity_name TEXT,

    entity_id UUID,

    action TEXT,

    previous_value JSONB,

    new_value JSONB,

    changed_at TIMESTAMP DEFAULT NOW()
);

