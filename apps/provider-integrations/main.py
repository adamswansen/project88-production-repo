#!/usr/bin/env python3
"""
Main entry point for Project88Hub Provider Integration System
Runs the sync engine and workers
"""

import os
import sys
import time
import signal
import logging
import argparse
from typing import List

from provider_sync_engine import ProviderSyncEngine
from sync_worker import SyncWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/project88/provider_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ProviderIntegrationMain')

class ProviderIntegrationSystem:
    """Main system coordinator"""
    
    def __init__(self, db_connection_string: str, num_workers: int = 2):
        self.db_connection_string = db_connection_string
        self.num_workers = num_workers
        self.sync_engine = None
        self.workers: List[SyncWorker] = []
        self.running = False
        
    def start(self):
        """Start the complete provider integration system"""
        logger.info("Starting Provider Integration System")
        
        try:
            # Start sync engine
            self.sync_engine = ProviderSyncEngine(self.db_connection_string)
            self.sync_engine.start()
            
            # Start workers
            for i in range(self.num_workers):
                worker = SyncWorker(self.db_connection_string, f"worker-{i+1}")
                worker.start()
                self.workers.append(worker)
            
            self.running = True
            logger.info(f"Provider Integration System started with {self.num_workers} workers")
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the complete system"""
        logger.info("Stopping Provider Integration System")
        self.running = False
        
        # Stop sync engine
        if self.sync_engine:
            self.sync_engine.stop()
        
        # Stop all workers
        for worker in self.workers:
            worker.stop()
        
        logger.info("Provider Integration System stopped")
    
    def status(self):
        """Get system status"""
        status = {
            'running': self.running,
            'sync_engine_active': self.sync_engine is not None,
            'workers_count': len(self.workers),
            'workers_active': sum(1 for w in self.workers if w.running)
        }
        return status

def get_db_connection_string():
    """Get database connection string from environment or config"""
    
    # Try environment variables first
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME', 'project88_myappdb')
    username = os.getenv('DB_USER', 'project88_myappuser')
    password = os.getenv('DB_PASSWORD', '')
    
    if not password:
        logger.warning("No database password provided via DB_PASSWORD environment variable")
    
    connection_string = f"host={host} port={port} dbname={database} user={username} password={password}"
    
    return connection_string

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description='Project88Hub Provider Integration System')
    parser.add_argument('--workers', type=int, default=2, help='Number of sync workers to start')
    parser.add_argument('--engine-only', action='store_true', help='Run only the sync engine (no workers)')
    parser.add_argument('--worker-only', action='store_true', help='Run only a sync worker (no engine)')
    parser.add_argument('--test-connection', action='store_true', help='Test database connection and exit')
    parser.add_argument('--manual-sync', help='Trigger manual sync for provider (format: timing_partner_id:provider_name:event_id)')
    
    args = parser.parse_args()
    
    # Get database connection
    db_connection = get_db_connection_string()
    
    # Test connection if requested
    if args.test_connection:
        try:
            import psycopg2
            conn = psycopg2.connect(db_connection)
            conn.close()
            logger.info("Database connection test successful")
            return 0
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return 1
    
    # Manual sync if requested
    if args.manual_sync:
        try:
            parts = args.manual_sync.split(':')
            if len(parts) < 2:
                logger.error("Manual sync format: timing_partner_id:provider_name[:event_id]")
                return 1
            
            timing_partner_id = int(parts[0])
            provider_name = parts[1]
            event_id = parts[2] if len(parts) > 2 else None
            
            engine = ProviderSyncEngine(db_connection)
            engine.start()
            engine.manual_sync(timing_partner_id, provider_name, event_id)
            engine.stop()
            
            logger.info("Manual sync completed")
            return 0
            
        except Exception as e:
            logger.error(f"Manual sync failed: {e}")
            return 1
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    system = None
    
    try:
        if args.engine_only:
            # Run only sync engine
            engine = ProviderSyncEngine(db_connection)
            engine.start()
            
            logger.info("Sync engine running. Press Ctrl+C to stop.")
            
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                pass
            finally:
                engine.stop()
                
        elif args.worker_only:
            # Run only sync worker
            worker = SyncWorker(db_connection, "standalone-worker")
            worker.start()
            
            logger.info("Sync worker running. Press Ctrl+C to stop.")
            
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                pass
            finally:
                worker.stop()
                
        else:
            # Run complete system
            system = ProviderIntegrationSystem(db_connection, args.workers)
            system.start()
            
            logger.info("Provider Integration System running. Press Ctrl+C to stop.")
            
            # Monitor system
            try:
                while system.running:
                    time.sleep(60)
                    
                    # Log status periodically
                    status = system.status()
                    logger.debug(f"System status: {status}")
                    
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
        
        logger.info("Shutdown complete")
        return 0
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        return 1
        
    finally:
        if system:
            system.stop()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 