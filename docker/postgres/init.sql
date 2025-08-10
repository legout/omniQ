-- OmniQ PostgreSQL Database Initialization Script
-- This script sets up the complete database schema for the OmniQ task queue system
-- 
-- Usage: This file is automatically executed by PostgreSQL during container initialization
--        when placed in the /docker-entrypoint-initdb.d/ directory

-- Enable necessary PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Create schema for OmniQ application
CREATE SCHEMA IF NOT EXISTS omniq;

-- Set default schema search path
SET search_path TO omniq, public;

-- Create application user with appropriate permissions
DO $$
BEGIN
    -- Check if user exists, create if not
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'omniq_user') THEN
        CREATE USER omniq_user WITH PASSWORD 'omniq_user_password' 
            CONNECTION LIMIT 100
            NOCREATEDB 
            NOCREATEROLE;
    END IF;
    
    -- Grant permissions on schema
    GRANT USAGE ON SCHEMA omniq TO omniq_user;
    GRANT CREATE ON SCHEMA omniq TO omniq_user;
    
    -- Grant all privileges on all tables in the schema (future tables too)
    GRANT ALL ON ALL TABLES IN SCHEMA omniq TO omniq_user;
    
    -- Grant all privileges on all sequences in the schema
    GRANT ALL ON ALL SEQUENCES IN SCHEMA omniq TO omniq_user;
    
    -- Grant all privileges on all types in the schema
    GRANT ALL ON ALL TYPES IN SCHEMA omniq TO omniq_user;
    
    -- Grant all privileges on all functions in the schema
    GRANT ALL ON ALL FUNCTIONS IN SCHEMA omniq TO omniq_user;
    
    -- Grant all privileges on all schemas in the database
    GRANT ALL ON SCHEMA public TO omniq_user;
END
$$;

-- Create tasks table for task queue management
CREATE TABLE IF NOT EXISTS omniq.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    queue_name VARCHAR(255) NOT NULL DEFAULT 'default',
    func_name TEXT NOT NULL,
    args JSONB NOT NULL DEFAULT '[]'::jsonb,
    kwargs JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ttl_seconds INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    locked_at TIMESTAMP WITH TIME ZONE,
    locked_by VARCHAR(255),
    lock_timeout_seconds INTEGER,
    priority INTEGER DEFAULT 0 CHECK (priority >= 0),
    retry_count INTEGER DEFAULT 0 CHECK (retry_count >= 0),
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    INDEX idx_tasks_queue_status (queue_name, status),
    INDEX idx_tasks_status_priority (status, priority DESC, created_at ASC),
    INDEX idx_tasks_locked_at (locked_at),
    INDEX idx_tasks_created_at (created_at),
    INDEX idx_tasks_scheduled_at (scheduled_at)
);

-- Create results table for task result storage
CREATE TABLE IF NOT EXISTS omniq.results (
    task_id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'completed', 'failed', 'cancelled')),
    result_data JSONB,
    error_data JSONB,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    INDEX idx_results_status (status, timestamp),
    INDEX idx_results_expires_at (expires_at),
    INDEX idx_results_timestamp (timestamp)
);

-- Create events table for task event logging
CREATE TABLE IF NOT EXISTS omniq.events (
    id SERIAL PRIMARY KEY,
    task_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('created', 'started', 'completed', 'failed', 'cancelled', 'retried', 'timeout')),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    worker_id VARCHAR(255),
    message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    INDEX idx_events_task_id (task_id, timestamp),
    INDEX idx_events_event_type (event_type, timestamp),
    INDEX idx_events_timestamp (timestamp),
    INDEX idx_events_worker_id (worker_id)
);

-- Create worker management table
CREATE TABLE IF NOT EXISTS omniq.workers (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(255) NOT NULL UNIQUE,
    worker_type VARCHAR(50) NOT NULL CHECK (worker_type IN ('thread', 'process', 'async', 'gevent')),
    status VARCHAR(20) NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'busy', 'stopped', 'error')),
    current_task_id UUID,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_heartbeat TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    total_tasks_processed INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    metadata JSONB,
    INDEX idx_workers_status (status),
    INDEX idx_workers_last_heartbeat (last_heartbeat),
    INDEX idx_workers_worker_type (worker_type)
);

-- Create queue statistics table
CREATE TABLE IF NOT EXISTS omniq.queue_stats (
    id SERIAL PRIMARY KEY,
    queue_name VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    pending_tasks INTEGER DEFAULT 0,
    processing_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    cancelled_tasks INTEGER DEFAULT 0,
    total_tasks_processed INTEGER DEFAULT 0,
    avg_processing_time INTERVAL DEFAULT '0 seconds',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (queue_name, date),
    INDEX idx_queue_stats_date (date),
    INDEX idx_queue_stats_queue (queue_name)
);

-- Create scheduled tasks table for recurring task management
CREATE TABLE IF NOT EXISTS omniq.scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_name VARCHAR(255) NOT NULL,
    func_name TEXT NOT NULL,
    args JSONB NOT NULL DEFAULT '[]'::jsonb,
    kwargs JSONB NOT NULL DEFAULT '{}'::jsonb,
    schedule_type VARCHAR(50) NOT NULL CHECK (schedule_type IN ('interval', 'cron', 'once')),
    schedule_config JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'cancelled')),
    next_run_at TIMESTAMP WITH TIME ZONE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    run_count INTEGER DEFAULT 0,
    max_runs INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    INDEX idx_scheduled_tasks_status (status, next_run_at),
    INDEX idx_scheduled_tasks_next_run (next_run_at),
    INDEX idx_scheduled_tasks_schedule_type (schedule_type)
);

-- Create task dependencies table
CREATE TABLE IF NOT EXISTS omniq.task_dependencies (
    id SERIAL PRIMARY KEY,
    task_id UUID NOT NULL,
    depends_on_task_id UUID NOT NULL,
    dependency_type VARCHAR(50) NOT NULL DEFAULT 'completion' CHECK (dependency_type IN ('completion', 'success', 'failure')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (task_id, depends_on_task_id),
    INDEX idx_task_dependencies_task_id (task_id),
    INDEX idx_task_dependencies_depends_on (depends_on_task_id)
);

-- Create audit log table for important database changes
CREATE TABLE IF NOT EXISTS omniq.audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) NOT NULL,
    record_id UUID,
    action VARCHAR(10) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(255) NOT NULL DEFAULT 'system',
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    INDEX idx_audit_log_table (table_name, record_id),
    INDEX idx_audit_log_action (action),
    INDEX idx_audit_log_changed_at (changed_at)
);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION omniq.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON omniq.tasks
    FOR EACH ROW EXECUTE FUNCTION omniq.update_updated_at_column();

CREATE TRIGGER update_results_updated_at BEFORE UPDATE ON omniq.results
    FOR EACH ROW EXECUTE FUNCTION omniq.update_updated_at_column();

CREATE TRIGGER update_queue_stats_updated_at BEFORE UPDATE ON omniq.queue_stats
    FOR EACH ROW EXECUTE FUNCTION omniq.update_updated_at_column();

CREATE TRIGGER update_scheduled_tasks_updated_at BEFORE UPDATE ON omniq.scheduled_tasks
    FOR EACH ROW EXECUTE FUNCTION omniq.update_updated_at_column();

-- Create function to cleanup expired tasks and results
CREATE OR REPLACE FUNCTION omniq.cleanup_expired_data()
RETURNS INTEGER AS $$
DECLARE
    expired_tasks INTEGER;
    expired_results INTEGER;
    expired_scheduled INTEGER;
BEGIN
    -- Clean up expired tasks
    DELETE FROM omniq.tasks 
    WHERE ttl_seconds IS NOT NULL 
    AND (created_at + (ttl_seconds || ' seconds')::INTERVAL) < NOW()
    AND status IN ('pending', 'failed');
    
    GET DIAGNOSTICS expired_tasks = ROW_COUNT;
    
    -- Clean up expired results
    DELETE FROM omniq.results WHERE expires_at < NOW();
    GET DIAGNOSTICS expired_results = ROW_COUNT;
    
    -- Clean up expired scheduled tasks
    DELETE FROM omniq.scheduled_tasks WHERE expires_at < NOW();
    GET DIAGNOSTICS expired_scheduled = ROW_COUNT;
    
    -- Return total cleaned up records
    RETURN expired_tasks + expired_results + expired_scheduled;
END;
$$ LANGUAGE plpgsql;

-- Create function to get queue statistics
CREATE OR REPLACE FUNCTION omniq.get_queue_stats(queue_name VARCHAR(255))
RETURNS TABLE(
    pending_count INTEGER,
    processing_count INTEGER,
    completed_count INTEGER,
    failed_count INTEGER,
    cancelled_count INTEGER,
    total_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
        COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_count,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
        COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_count,
        COUNT(*) as total_count
    FROM omniq.tasks
    WHERE queue_name = queue_name;
END;
$$ LANGUAGE plpgsql;

-- Create function to record task event
CREATE OR REPLACE FUNCTION omniq.record_task_event(
    p_task_id UUID,
    p_event_type VARCHAR(50),
    p_worker_id VARCHAR(255) DEFAULT NULL,
    p_message TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO omniq.events (task_id, event_type, worker_id, message, metadata)
    VALUES (p_task_id, p_event_type, p_worker_id, p_message, p_metadata);
END;
$$ LANGUAGE plpgsql;

-- Create function to update worker heartbeat
CREATE OR REPLACE FUNCTION omniq.update_worker_heartbeat(p_worker_id VARCHAR(255))
RETURNS VOID AS $$
BEGIN
    INSERT INTO omniq.workers (worker_id, status, last_heartbeat)
    VALUES (p_worker_id, 'busy', NOW())
    ON CONFLICT (worker_id) 
    DO UPDATE SET 
        status = CASE 
            WHEN EXCLUDED.status = 'busy' THEN 'busy'
            ELSE omniq.workers.status 
        END,
        last_heartbeat = NOW();
END;
$$ LANGUAGE plpgsql;

-- Create function to process scheduled tasks
CREATE OR REPLACE FUNCTION omniq.process_scheduled_tasks()
RETURNS INTEGER AS $$
DECLARE
    tasks_to_run RECORD;
    tasks_run INTEGER := 0;
BEGIN
    -- Find scheduled tasks that need to run
    FOR tasks_to_run IN 
        SELECT * FROM omniq.scheduled_tasks
        WHERE status = 'active'
        AND (next_run_at IS NULL OR next_run_at <= NOW())
        AND (max_runs IS NULL OR run_count < max_runs)
        AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY next_run_at ASC
        LIMIT 100
    LOOP
        -- Process the scheduled task (this would be called from the application)
        -- For now, just update the run count and next run time
        UPDATE omniq.scheduled_tasks 
        SET 
            run_count = run_count + 1,
            last_run_at = NOW(),
            next_run_at = CASE 
                WHEN schedule_type = 'once' THEN NULL
                ELSE omniq.calculate_next_run(schedule_type, schedule_config, last_run_at)
            END
        WHERE id = tasks_to_run.id;
        
        tasks_run := tasks_run + 1;
    END LOOP;
    
    RETURN tasks_run;
END;
$$ LANGUAGE plpgsql;

-- Create function to calculate next run time (placeholder - would be implemented in application)
CREATE OR REPLACE FUNCTION omniq.calculate_next_run(
    schedule_type VARCHAR(50),
    schedule_config JSONB,
    last_run TIMESTAMP WITH TIME ZONE
) RETURNS TIMESTAMP WITH TIME ZONE AS $$
BEGIN
    -- This is a placeholder function
    -- The actual implementation would be in the application layer
    RETURN NOW() + INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for recent task activity
CREATE MATERIALIZED VIEW IF NOT EXISTS omniq.recent_task_activity AS
SELECT 
    t.id,
    t.queue_name,
    t.func_name,
    t.status,
    t.created_at,
    t.completed_at,
    t.error_message,
    e.event_type,
    e.worker_id,
    e.timestamp as last_event_time
FROM omniq.tasks t
LEFT JOIN LATERAL (
    SELECT event_type, worker_id, timestamp
    FROM omniq.events
    WHERE task_id = t.id
    ORDER BY timestamp DESC
    LIMIT 1
) e ON true
WHERE t.created_at >= NOW() - INTERVAL '7 days'
WITH DATA;

-- Create index on the materialized view
CREATE INDEX IF NOT EXISTS idx_recent_task_activity_created_at ON omniq.recent_task_activity(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recent_task_activity_status ON omniq.recent_task_activity(status);
CREATE INDEX IF NOT EXISTS idx_recent_task_activity_queue ON omniq.recent_task_activity(queue_name);

-- Create refresh function for the materialized view
CREATE OR REPLACE FUNCTION omniq.refresh_recent_task_activity()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY omniq.recent_task_activity;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions on all newly created objects
GRANT ALL ON ALL TABLES IN SCHEMA omniq TO omniq_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA omniq TO omniq_user;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA omniq TO omniq_user;
GRANT ALL ON ALL TYPES IN SCHEMA omniq TO omniq_user;
GRANT ALL ON ALL MATERIALIZED VIEWS IN SCHEMA omniq TO omniq_user;

-- Create initial data
INSERT INTO omniq.workers (worker_id, worker_type, status) VALUES 
('omniq-initial-worker', 'async', 'idle')
ON CONFLICT (worker_id) DO NOTHING;

-- Insert sample scheduled task if none exist
INSERT INTO omniq.scheduled_tasks (
    task_name, 
    func_name, 
    schedule_type, 
    schedule_config, 
    next_run_at
) VALUES (
    'cleanup_expired_data',
    'omniq.cleanup_expired_data',
    'interval',
    '{"interval": "1 hour"}'::jsonb,
    NOW() + INTERVAL '1 hour'
)
ON CONFLICT (task_name) DO NOTHING;

-- Create database user for application connections
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'omniq_app') THEN
        CREATE USER omniq_app WITH PASSWORD 'omniq_app_password' 
            CONNECTION LIMIT 50
            NOCREATEDB 
            NOCREATEROLE;
    END IF;
    
    -- Grant limited permissions to application user
    GRANT USAGE ON SCHEMA omniq TO omniq_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA omniq TO omniq_app;
    GRANT SELECT, USAGE ON ALL SEQUENCES IN SCHEMA omniq TO omniq_app;
    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA omniq TO omniq_app;
    GRANT USAGE ON ALL TYPES IN SCHEMA omniq TO omniq_app;
END
$$;

-- Create read-only user for reporting
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'omniq_readonly') THEN
        CREATE USER omniq_readonly WITH PASSWORD 'omniq_readonly_password' 
            CONNECTION LIMIT 20
            NOCREATEDB 
            NOCREATEROLE;
    END IF;
    
    -- Grant read-only permissions
    GRANT USAGE ON SCHEMA omniq TO omniq_readonly;
    GRANT SELECT ON ALL TABLES IN SCHEMA omniq TO omniq_readonly;
    GRANT SELECT ON ALL SEQUENCES IN SCHEMA omniq TO omniq_readonly;
    GRANT SELECT ON ALL MATERIALIZED VIEWS IN SCHEMA omniq TO omniq_readonly;
    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA omniq TO omniq_readonly;
    GRANT USAGE ON ALL TYPES IN SCHEMA omniq TO omniq_readonly;
END
$$;

-- Set up row level security (RLS) for enhanced security
ALTER TABLE omniq.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE omniq.results ENABLE ROW LEVEL SECURITY;
ALTER TABLE omniq.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE omniq.workers ENABLE ROW LEVEL SECURITY;
ALTER TABLE omniq.queue_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE omniq.scheduled_tasks ENABLE ROW LEVEL SECURITY;

-- Create policies for row level security
-- These are basic policies - adjust based on your specific security requirements
CREATE POLICY app_users_can_access_tasks ON omniq.tasks
    FOR ALL TO omniq_app
    USING (true)
    WITH CHECK (true);

CREATE POLICY app_users_can_access_results ON omniq.results
    FOR ALL TO omniq_app
    USING (true)
    WITH CHECK (true);

CREATE POLICY app_users_can_access_events ON omniq.events
    FOR ALL TO omniq_app
    USING (true)
    WITH CHECK (true);

CREATE POLICY readonly_users_can_select ON omniq.tasks
    FOR SELECT TO omniq_readonly
    USING (true);

CREATE POLICY readonly_users_can_select ON omniq.results
    FOR SELECT TO omniq_readonly
    USING (true);

CREATE POLICY readonly_users_can_select ON omniq.events
    FOR SELECT TO omniq_readonly
    USING (true);

-- Create database statistics and monitoring views
CREATE OR REPLACE VIEW omniq.database_stats AS
SELECT 
    schemaname as schema_name,
    tablename as table_name,
    attname as column_name,
    n_distinct as distinct_values,
    correlation as data_correlation,
    most_common_vals as most_common_values,
    most_common_freqs as most_common_frequencies
FROM pg_stats 
WHERE schemaname = 'omniq'
ORDER BY tablename, attname;

-- Create performance monitoring view
CREATE OR REPLACE VIEW omniq.performance_metrics AS
SELECT 
    schemaname as schema_name,
    relname as table_name,
    seq_scan as sequential_scans,
    seq_tup_read as tuples_read_sequentially,
    idx_scan as index_scans,
    idx_tup_fetch as tuples_fetched_from_index,
    n_tup_ins as tuples_inserted,
    n_tup_upd as tuples_updated,
    n_tup_del as tuples_deleted,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples,
    last_vacuum as last_vacuum_time,
    last_autovacuum as last_autovacuum_time,
    last_analyze as last_analyze_time,
    last_autoanalyze as last_autoanalyze_time
FROM pg_stat_user_tables
WHERE schemaname = 'omniq'
ORDER BY relname;

-- Final verification and setup
-- Run initial cleanup to ensure clean state
SELECT omniq.cleanup_expired_data();

-- Refresh materialized view
SELECT omniq.refresh_recent_task_activity();

-- Log initialization completion
INSERT INTO omniq.events (task_id, event_type, message, metadata)
VALUES (uuid_generate_v4(), 'database_initialized', 'OmniQ database initialized successfully', 
        '{"version": "1.0.0", "timestamp": NOW()}'::jsonb);

-- Set up database configuration for optimal performance
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = '200';
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = '0.9';
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = '100';
ALTER SYSTEM SET random_page_cost = '1.1';
ALTER SYSTEM SET effective_io_concurrency = '200';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET min_parallel_table_scan_size = '8MB';
ALTER SYSTEM SET min_parallel_index_scan_size = '512kB';
ALTER SYSTEM SET max_parallel_workers_per_gather = '2';
ALTER SYSTEM SET max_parallel_maintenance_workers = '2';

-- Reload configuration
SELECT pg_reload_conf();

-- Display completion message
SELECT 'OmniQ database initialization completed successfully' as message;