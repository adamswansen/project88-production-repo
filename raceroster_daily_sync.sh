#!/bin/bash

# Race Roster Event-Driven Sync Script
# Runs sophisticated event-driven sync with dynamic frequency based on event proximity

cd /opt/project88/provider-integrations

# Log start time
echo "$(date): Starting Race Roster Event-Driven Scheduler" >> raceroster_sync.log

# Run the event-driven scheduler
python3 raceroster_scheduler.py >> raceroster_sync.log 2>&1

# Log completion
echo "$(date): Race Roster Event-Driven Scheduler completed" >> raceroster_sync.log 