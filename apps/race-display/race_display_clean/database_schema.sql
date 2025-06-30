-- Database schema for Race Display Multi-User Application
-- This schema supports multiple concurrent users and events with proper isolation

-- Create database if it doesn't exist (run manually)
-- CREATE DATABASE raw_tag_data;

-- Timing Sessions table - tracks each user's event session
CREATE TABLE IF NOT EXISTS timing_sessions (
    id SERIAL PRIMARY KEY,
    session_name VARCHAR(255) NOT NULL,
    event_id VARCHAR(100) NOT NULL,
    user_session_id VARCHAR(100) NOT NULL,  -- Links to Redis session
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    UNIQUE(user_session_id, event_id, status) -- Only one active session per user/event
);

-- Timing Locations table - tracks reader locations per session
CREATE TABLE IF NOT EXISTS timing_locations (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES timing_sessions(id) ON DELETE CASCADE,
    location_name VARCHAR(100) NOT NULL,
    reader_id VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, location_name)
);

-- Timing Reads table - stores actual timing data
CREATE TABLE IF NOT EXISTS timing_reads (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES timing_sessions(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES timing_locations(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    location_name VARCHAR(100) NOT NULL,
    tag_code VARCHAR(50) NOT NULL,
    read_time VARCHAR(20) NOT NULL,
    lap_count INTEGER DEFAULT 1,
    reader_id VARCHAR(50),
    gator_number INTEGER DEFAULT 0,
    raw_data JSONB,
    read_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, sequence_number, location_name)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_timing_sessions_user_event ON timing_sessions(user_session_id, event_id);
CREATE INDEX IF NOT EXISTS idx_timing_sessions_status ON timing_sessions(status);
CREATE INDEX IF NOT EXISTS idx_timing_locations_session ON timing_locations(session_id);
CREATE INDEX IF NOT EXISTS idx_timing_reads_session ON timing_reads(session_id);
CREATE INDEX IF NOT EXISTS idx_timing_reads_timestamp ON timing_reads(read_timestamp);
CREATE INDEX IF NOT EXISTS idx_timing_reads_tag_code ON timing_reads(tag_code);
CREATE INDEX IF NOT EXISTS idx_timing_reads_location ON timing_reads(location_name);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update timestamps
CREATE TRIGGER update_timing_sessions_updated_at 
    BEFORE UPDATE ON timing_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views for common queries
CREATE OR REPLACE VIEW timing_session_stats AS
SELECT 
    ts.id,
    ts.session_name,
    ts.event_id,
    ts.user_session_id,
    ts.status,
    ts.created_at,
    COUNT(tr.id) as total_reads,
    COUNT(DISTINCT tr.tag_code) as unique_tags,
    COUNT(DISTINCT tl.id) as total_locations,
    MIN(tr.read_timestamp) as first_read,
    MAX(tr.read_timestamp) as last_read
FROM timing_sessions ts
LEFT JOIN timing_locations tl ON ts.id = tl.session_id
LEFT JOIN timing_reads tr ON ts.id = tr.session_id
GROUP BY ts.id, ts.session_name, ts.event_id, ts.user_session_id, ts.status, ts.created_at;

-- Sample data cleanup function (call periodically)
CREATE OR REPLACE FUNCTION cleanup_old_sessions(days_old INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Mark old sessions as completed
    UPDATE timing_sessions 
    SET status = 'completed', ended_at = CURRENT_TIMESTAMP
    WHERE status = 'active' 
    AND created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust user as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO race_timing_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO race_timing_user; 