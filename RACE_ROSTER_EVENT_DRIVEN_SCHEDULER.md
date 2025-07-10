# Race Roster Event-Driven Scheduler

## Overview

The Race Roster Event-Driven Scheduler is a sophisticated synchronization system that matches the advanced scheduling logic used by RunSignUp. It provides dynamic frequency-based syncing based on event proximity, ensuring optimal data freshness while respecting API rate limits.

## Key Features

### 🎯 **Dynamic Frequency Based on Event Proximity**
- **Outside 24 hours**: Every 4 hours (not just once daily!)
- **Within 24 hours**: Every 15 minutes
- **Within 4 hours**: Every minute
- **Stop**: 1 hour after event start

### 🔍 **Event Discovery**
- **Twice daily**: 6 AM and 6 PM (same as RunSignUp)
- Only discovers **upcoming events** (not past events)
- Incremental participant syncing for existing events

### ⚡ **Priority-Based Processing**
- **High priority** (within 4 hours): Up to 50 events per cycle
- **Medium priority** (within 24 hours): Up to 20 events per cycle  
- **Low priority** (outside 24 hours): Up to 10 events per cycle

### 🛡️ **Production-Ready Features**
- **Lock file management** to prevent concurrent runs
- **Signal handling** for graceful shutdown
- **Comprehensive logging** with event timing details
- **Database connection pooling** and error recovery
- **Memory-efficient processing** with controlled batch sizes

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Event-Driven Scheduler                      │
├─────────────────────────────────────────────────────────────────┤
│  Discovery Phase (6 AM & 6 PM)                                │
│  • Fetch new upcoming events from Race Roster API              │
│  • Store in raceroster_events table                           │
├─────────────────────────────────────────────────────────────────┤
│  Processing Phase (Continuous)                                 │
│  • Query events needing sync based on frequency rules          │
│  • Prioritize by event proximity                              │
│  • Sync participants in controlled batches                     │
├─────────────────────────────────────────────────────────────────┤
│  Frequency Management                                          │
│  • Calculate sync frequency based on start_date proximity      │
│  • Apply priority limits to prevent API overload               │
│  • Skip events that finished > 1 hour ago                     │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema Integration

### Events Table: `raceroster_events`
- `event_id` (UUID): Primary key
- `external_event_id` (String): Race Roster event ID
- `timing_partner_id` (Integer): Reference to timing partner
- `event_name` (String): Event display name
- `start_date` (DateTime): Event start time
- `fetched_date` (DateTime): Last sync timestamp
- `current_participants` (Integer): Participant count

### Participants Table: `raceroster_participants`
- `id` (Integer): Primary key
- `event_id` (UUID): Foreign key to raceroster_events
- `timing_partner_id` (Integer): Reference to timing partner
- `registration_id` (String): Race Roster participant ID
- `first_name`, `last_name`, `email`: Participant details
- `bib_number` (String): Race bib assignment
- `gender` (String): M/F/Other
- `registration_date` (DateTime): When registered
- `registration_status` (String): active/inactive

## Configuration

### Environment Variables
- `POSTGRES_HOST`: Database host
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database username
- `POSTGRES_PASSWORD`: Database password

### Provider Credentials
Race Roster requires OAuth2 authentication stored in `partner_provider_credentials`:
- `provider_id`: 3 (Race Roster)
- `principal`: OAuth2 Client ID
- `secret`: OAuth2 Client Secret
- `additional_config`: JSON with username/password

## Deployment

### Files
- `raceroster_scheduler.py`: Main scheduler application
- `raceroster_daily_sync.sh`: Wrapper script for cron
- `deploy_raceroster_event_driven.sh`: Deployment script

### SystemD Service
```ini
[Unit]
Description=Race Roster Event-Driven Scheduler
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/project88/provider-integrations
ExecStart=/usr/bin/python3 /opt/project88/provider-integrations/raceroster_scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Deployment Commands
```bash
# Deploy to production
./deploy_raceroster_event_driven.sh

# Check service status
systemctl status raceroster-scheduler.service

# View logs
journalctl -u raceroster-scheduler.service -f
```

## API Integration

### Race Roster API Endpoints Used
- `GET /v1/events`: Event discovery with pagination
- `GET /v1/events/{eventId}/participants`: Participant sync with pagination
- `POST /oauth/authorize`: Authentication token refresh

### Rate Limiting
- **Events API**: 1000 requests/hour per provider
- **Participants API**: 1000 requests/hour per provider
- **Built-in delays**: 1 second between requests to respect limits

## Monitoring & Logging

### Log Levels
- **INFO**: Normal operation, sync cycles, event processing
- **ERROR**: API failures, database errors, authentication issues
- **DEBUG**: Detailed timing, pagination details, SQL queries

### Key Metrics
- Events processed per cycle
- Participants synced per event
- API response times
- Database connection health
- Memory usage patterns

### Example Log Output
```
2025-07-10 14:10:59,951 - INFO - 🚀 Starting Race Roster Event-Driven Scheduler
2025-07-10 14:10:59,962 - INFO - 🎯 Processing 10 events this cycle
2025-07-10 14:10:59,962 - INFO - ⚪ Processing 10 low-priority events
2025-07-10 14:10:59,962 - INFO - 🔄 Syncing event 2025 Turkey Day 5K (ID: 1156a810...)
2025-07-10 14:10:59,963 - INFO -    ⏰ Start time: 2025-11-27 14:00:00
2025-07-10 14:10:59,963 - INFO -    🕐 Time until start: 139 days, 23:49:00
2025-07-10 14:10:59,963 - INFO -    📊 Sync frequency: 240 minutes
```

## Comparison with Simple Sync

| Feature | Simple Daily Sync | Event-Driven Scheduler |
|---------|------------------|------------------------|
| **Frequency** | Once daily at 3 AM | Dynamic based on proximity |
| **Event Discovery** | Manual/scheduled | Twice daily automatic |
| **Priority** | All events equal | Proximity-based priority |
| **Resource Usage** | High during sync window | Distributed throughout day |
| **Real-time Data** | Up to 24 hours stale | Up to 1 minute fresh (near events) |
| **API Efficiency** | Batch processing | Optimized incremental sync |

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Check OAuth2 credentials in `partner_provider_credentials`
   - Verify username/password in `additional_config`
   - Check token expiration and refresh logic

2. **Database Connection Issues**
   - Verify PostgreSQL connectivity
   - Check connection pool settings
   - Monitor for connection leaks

3. **API Rate Limiting**
   - Monitor request frequency in logs
   - Adjust batch sizes if needed
   - Check Race Roster provider limits

4. **Memory Usage**
   - Monitor participant batch processing
   - Check for large event participant counts
   - Tune batch sizes for memory constraints

### Debug Mode
```bash
# Run in debug mode
python3 raceroster_scheduler.py --debug
```

## Future Enhancements

1. **Predictive Scheduling**: Machine learning for optimal sync timing
2. **Multi-Region Support**: Distributed scheduler instances
3. **Real-time Webhooks**: Event-triggered synchronization
4. **Advanced Metrics**: Grafana/Prometheus integration
5. **A/B Testing**: Frequency optimization experiments

## Security

- OAuth2 token encryption in database
- Secure credential storage
- Network access controls
- Audit logging for all API calls
- Rate limiting protection

---

*This scheduler represents a significant advancement in Race Roster integration, providing RunSignUp-level sophistication while maintaining reliability and efficiency.* 