# Project88Hub Provider Integration System

A comprehensive system for synchronizing registration data from multiple race registration providers into a unified database.

## Overview

This system provides intelligent, event-based synchronization with the following providers:
- **RunSignUp** - US-based race registration platform
- **Race Roster** - Canadian race registration platform  
- **Haku** - Event management and registration platform
- **Let's Do This** - UK-based race platform

## Key Features

### Event-Based Sync Scheduling
- **Outside 24 hours**: Hourly syncs
- **Within 24 hours**: Every 15 minutes  
- **Within 4 hours**: Every minute
- **Continues until 1 hour PAST event start time**

### Intelligent Sync Management
- **Full sync** on first run, then **incremental syncs** only
- **Priority-based** job queue (closer to event start = higher priority)
- **Automatic retry** with exponential backoff
- **Comprehensive logging** and error tracking

### Provider Support
- **Standardized data models** across all providers
- **Provider-specific authentication** (API keys, OAuth, JWT)
- **Rate limiting** to respect API limits
- **Raw data preservation** for audit trails

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Sync Engine    │───▶│   Sync Queue     │───▶│  Sync Workers   │
│                 │    │                  │    │                 │
│ • Schedules     │    │ • Priority-based │    │ • Process jobs  │
│ • Orchestrates  │    │ • Retry logic    │    │ • Store data    │
│ • Event timing  │    │ • Job tracking   │    │ • Error handling│
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                    ┌──────────────────┐
                    │   Database       │
                    │                  │
                    │ • Provider tables│
                    │ • Sync history   │
                    │ • Credentials    │
                    └──────────────────┘
```

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure database environment variables**:
   ```bash
   export DB_HOST=your-postgres-host
   export DB_NAME=project88_myappdb
   export DB_USER=project88_myappuser  
   export DB_PASSWORD=your-password
   ```

3. **Create log directory**:
   ```bash
   sudo mkdir -p /var/log/project88
   sudo chown $USER:$USER /var/log/project88
   ```

## Usage

### Start Complete System
```bash
python main.py --workers 3
```

### Run Components Separately
```bash
# Sync engine only
python main.py --engine-only

# Worker only  
python main.py --worker-only
```

### Manual Sync
```bash
# Sync all events for a timing partner/provider
python main.py --manual-sync "1:RunSignUp"

# Sync specific event
python main.py --manual-sync "1:RunSignUp:12345"
```

### Test Database Connection
```bash
python main.py --test-connection
```

## Configuration

### Provider Credentials
Credentials are stored in the `partner_provider_credentials` table:

```sql
-- Example: Add RunSignUp credentials
INSERT INTO partner_provider_credentials (
    timing_partner_id, provider_id, principal, secret
) VALUES (
    1, -- Your timing partner ID
    (SELECT provider_id FROM providers WHERE name = 'RunSignUp'),
    'your-api-key',
    'your-api-secret'
);
```

### Database Tables Required

The system uses existing provider tables:
- `runsignup_events` / `runsignup_participants`
- `raceroster_events` / `raceroster_participants` 
- `haku_events` / `haku_participants`
- `sync_queue` / `sync_history`

## Provider-Specific Details

### RunSignUp
- **Authentication**: API Key + Secret
- **Rate Limit**: 1000 calls/hour
- **Data**: Full event and participant details
- **Incremental**: Uses `last_modified` parameter

### Race Roster  
- **Authentication**: OAuth2 Client Credentials
- **Rate Limit**: 1000 calls/hour
- **Data**: Events with registration details
- **Incremental**: Uses `updated_since` parameter

### Haku
- **Authentication**: API Key + Secret
- **Rate Limit**: 500 calls/hour  
- **Data**: Events and participants with custom fields
- **Incremental**: Uses `updated_since` parameter

### Let's Do This
- **Authentication**: JWT Bearer Token
- **Rate Limit**: 1000 calls/hour
- **Data**: Applications (participants) and event details
- **Incremental**: Uses `updatedAt[after]` parameter

## Monitoring

### Logs
- **Main log**: `/var/log/project88/provider_integration.log`
- **Sync engine**: `/var/log/project88/provider_sync.log`
- **Workers**: `/var/log/project88/sync_worker.log`

### Database Monitoring
```sql
-- Check sync queue status
SELECT 
    p.name as provider,
    sq.operation_type,
    sq.status,
    COUNT(*) as count
FROM sync_queue sq
JOIN providers p ON p.provider_id = sq.provider_id
GROUP BY p.name, sq.operation_type, sq.status;

-- Recent sync history
SELECT 
    sh.sync_time,
    p.name as provider,
    sh.operation_type,
    sh.status,
    sh.num_of_synced_records
FROM sync_history sh
JOIN providers p ON p.provider_id = sh.provider_id
ORDER BY sh.sync_time DESC
LIMIT 20;
```

## Error Handling

### Automatic Retries
- **Failed jobs** retry 3 times with exponential backoff (2, 4, 8 minutes)
- **Rate limits** automatically wait and retry
- **Network errors** handled with retry logic

### Error Tracking
- All errors logged to database `sync_history` table
- Detailed error messages and stack traces in logs
- Failed jobs marked with failure reason

## Extensibility

### Adding New Providers
1. Create new adapter in `providers/` directory
2. Inherit from `BaseProviderAdapter`
3. Implement required methods:
   - `authenticate()`
   - `get_events()`
   - `get_participants()`
   - `get_provider_name()`
4. Add to `sync_worker.py` provider mapping
5. Create database tables for the provider

### Custom Sync Logic
The system is designed to be easily customizable:
- Modify sync frequencies in `EventSyncConfig.get_sync_frequency()`
- Add custom data processing in adapter `_parse_*` methods
- Extend database storage methods in sync worker

## Security Considerations

- **Credentials**: Stored encrypted in database
- **API Keys**: Never logged in plain text
- **Network**: Uses HTTPS for all API calls
- **Database**: Uses parameterized queries to prevent SQL injection

## Performance

### Optimization Features
- **Rate limiting** respects provider API limits
- **Concurrent workers** process multiple jobs simultaneously  
- **Incremental syncing** reduces data transfer
- **Priority queuing** ensures critical events sync first
- **Connection pooling** for database efficiency

### Scaling
- **Horizontal**: Add more worker processes
- **Vertical**: Increase worker count per process
- **Database**: Provider tables can be partitioned by timing partner

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Check credentials in `partner_provider_credentials` table
   - Verify API endpoints are accessible
   - Check provider API documentation for changes

2. **No Jobs Processing**
   - Verify events exist in `unified_events` table
   - Check event dates are within sync window
   - Ensure credentials exist for timing partner/provider combination

3. **Rate Limit Errors**  
   - System automatically handles rate limits
   - Check provider-specific rate limit settings
   - Consider reducing worker count if hitting limits

4. **Database Connection Issues**
   - Verify environment variables are set correctly
   - Check PostgreSQL is running and accessible
   - Test connection with `--test-connection` flag

### Debug Mode
```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
python main.py --workers 1
```

## API Reference

See individual provider adapter files for detailed API usage:
- `providers/runsignup_adapter.py`
- `providers/raceroster_adapter.py`  
- `providers/haku_adapter.py`
- `providers/letsdothis_adapter.py` 