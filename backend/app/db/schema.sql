-- Supabase PostgreSQL Schema for Resume Shortlisting Automation

-- Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(5) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    google_drive_folder_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for job_id lookups
CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title);

-- Resumes Table
CREATE TABLE IF NOT EXISTS resumes (
    id BIGSERIAL PRIMARY KEY,
    job_id VARCHAR(5) NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    google_drive_file_id VARCHAR(100) NOT NULL,
    candidate_name VARCHAR(200),
    upload_timestamp TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(job_id, google_drive_file_id)
);

-- Index for resume lookups
CREATE INDEX IF NOT EXISTS idx_resumes_job_id ON resumes(job_id);

-- Evaluations Table
CREATE TABLE IF NOT EXISTS evaluations (
    id BIGSERIAL PRIMARY KEY,
    resume_id BIGINT NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    job_id VARCHAR(5) NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    match_score DECIMAL(5,2) NOT NULL CHECK (match_score >= 0 AND match_score <= 100),
    status VARCHAR(20) NOT NULL CHECK (status IN ('OK to Proceed', 'Not OK', 'Pending')),
    justification TEXT NOT NULL,
    skills_extracted JSONB DEFAULT '[]'::jsonb,
    skills_matched JSONB DEFAULT '[]'::jsonb,
    experience_years DECIMAL(4,1),
    education TEXT,
    previous_roles JSONB DEFAULT '[]'::jsonb,
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(resume_id)
);

-- Index for evaluation lookups
CREATE INDEX IF NOT EXISTS idx_evaluations_job_id ON evaluations(job_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_status ON evaluations(status);
CREATE INDEX IF NOT EXISTS idx_evaluations_match_score ON evaluations(match_score DESC);

-- Audit Log Table (for tracking activities)
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    performed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for jobs table
DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
-- Enable RLS on all tables
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- For internal HR tool, allow all operations with service key
-- These policies allow full access when using the service role key
CREATE POLICY "Allow all for service role" ON jobs FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON resumes FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON evaluations FOR ALL USING (true);
CREATE POLICY "Allow all for service role" ON audit_logs FOR ALL USING (true);
