#!/usr/bin/env python3
"""
Setup Scheduled Operations for Project88 RunSignUp Integration
1. Schedule backfill to run when rate limit resets
2. Start continuous incremental scheduler
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime, timedelta
import pickle
import schedule
import threading

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from notifications import notify_error, get_notification_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduled_operations.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ScheduledOperationsManager:
    """Manages scheduled operations for RunSignUp integration"""
    
    def __init__(self):
        self.rate_limiter_cache_file = "/tmp/rate_limiter_runsignup.pkl"
        self.backfill_completed_file = "/tmp/backfill_completed.flag"
        self.scheduler_running = False
        
    def get_rate_limit_reset_time(self) -> datetime:
        """Calculate when the rate limit will reset (only if actually at limit)"""
        try:
            if os.path.exists(self.rate_limiter_cache_file):
                with open(self.rate_limiter_cache_file, 'rb') as f:
                    calls = pickle.load(f)
                
                if calls:
                    # Remove calls older than 1 hour
                    now = datetime.now()
                    recent_calls = [call for call in calls if (now - call).total_seconds() < 3600]
                    
                    logger.info(f"Rate limiter status: {len(recent_calls)}/1000 calls in last hour")
                    
                    # Only wait if we actually have 1000+ calls
                    if len(recent_calls) >= 1000:
                        oldest_call = min(recent_calls)
                        reset_time = oldest_call + timedelta(hours=1)
                        logger.info(f"Rate limit reached, reset time: {reset_time}")
                        return reset_time
                    else:
                        logger.info("Rate limit not reached, can run immediately")
                        return datetime.now()  # Can run immediately
                        
        except Exception as e:
            logger.error(f"Error reading rate limiter cache: {e}")
        
        # Default: can run immediately if no cache or error
        logger.info("No rate limiter cache found, can run immediately")
        return datetime.now()
    
    def run_backfill(self):
        """Run the complete backfill process"""
        logger.info("🚀 Starting scheduled backfill...")
        
        try:
            # Run backfill with all timing partners
            result = subprocess.run([
                sys.executable, 
                "runsignup_backfill.py", 
                "--resume"  # Resume from checkpoint if exists
            ], capture_output=True, text=True, timeout=3600*6)  # 6 hour timeout
            
            if result.returncode == 0:
                logger.info("✅ Backfill completed successfully")
                # Mark backfill as completed
                with open(self.backfill_completed_file, 'w') as f:
                    f.write(f"Backfill completed at {datetime.now()}")
                return True
            else:
                logger.error(f"❌ Backfill failed with exit code {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
                notify_error("Scheduled Backfill Failed", 
                           f"Backfill process exited with code {result.returncode}",
                           result.stderr[:200] if result.stderr else "No error details")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Backfill timed out after 6 hours")
            notify_error("Backfill Timeout", "Backfill process timed out after 6 hours", "Consider running with smaller batches")
            return False
        except Exception as e:
            logger.error(f"❌ Error running backfill: {e}")
            notify_error("Backfill Execution Error", str(e), "Failed to start or execute backfill process")
            return False
    
    def run_incremental_sync(self):
        """Run a single incremental sync cycle"""
        logger.info("🔄 Running incremental sync...")
        
        try:
            result = subprocess.run([
                sys.executable, 
                "runsignup_scheduler.py", 
                "--once"  # Run once instead of continuous
            ], capture_output=True, text=True, timeout=1800)  # 30 minute timeout
            
            if result.returncode == 0:
                logger.info("✅ Incremental sync completed successfully")
                return True
            else:
                logger.error(f"❌ Incremental sync failed with exit code {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
                notify_error("Incremental Sync Failed", 
                           f"Sync process exited with code {result.returncode}",
                           result.stderr[:200] if result.stderr else "No error details")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Incremental sync timed out after 30 minutes")
            notify_error("Incremental Sync Timeout", "Sync process timed out after 30 minutes", "Check for API issues or large datasets")
            return False
        except Exception as e:
            logger.error(f"❌ Error running incremental sync: {e}")
            notify_error("Incremental Sync Execution Error", str(e), "Failed to start or execute sync process")
            return False
    
    def is_backfill_completed(self) -> bool:
        """Check if backfill has been completed"""
        return os.path.exists(self.backfill_completed_file)
    
    def start_continuous_scheduler(self):
        """Start the continuous incremental sync scheduler"""
        logger.info("🔄 Starting continuous incremental sync scheduler...")
        
        try:
            # Run the scheduler in default mode (continuous)
            process = subprocess.Popen([
                sys.executable, 
                "runsignup_scheduler.py"
            ])
            
            logger.info(f"✅ Scheduler started with PID: {process.pid}")
            
            # Save PID for monitoring
            with open("/tmp/scheduler_pid.txt", "w") as f:
                f.write(str(process.pid))
            
            return process
            
        except Exception as e:
            logger.error(f"❌ Error starting continuous scheduler: {e}")
            notify_error("Scheduler Startup Error", str(e), "Failed to start continuous incremental sync")
            return None
    
    def setup_scheduled_operations(self):
        """Setup all scheduled operations"""
        logger.info("🎯 Setting up RunSignUp scheduled operations...")
        
        # Get rate limit reset time
        reset_time = self.get_rate_limit_reset_time()
        current_time = datetime.now()
        
        if reset_time <= current_time:
            logger.info("✅ Rate limit already reset, can run backfill immediately")
            wait_seconds = 0
        else:
            wait_seconds = (reset_time - current_time).total_seconds()
            logger.info(f"⏰ Rate limit resets at {reset_time}, waiting {wait_seconds/60:.1f} minutes")
        
        # Show notification status
        notif_status = get_notification_status()
        logger.info(f"📱 Notification status: {notif_status}")
        
        if not self.is_backfill_completed():
            if wait_seconds > 0:
                logger.info(f"⏰ Scheduling backfill to run in {wait_seconds/60:.1f} minutes...")
                time.sleep(wait_seconds)
            
            logger.info("🚀 Starting backfill now...")
            backfill_success = self.run_backfill()
            
            if not backfill_success:
                logger.error("❌ Backfill failed, not starting incremental scheduler")
                return False
        else:
            logger.info("✅ Backfill already completed, skipping to incremental sync")
        
        # Start continuous incremental sync scheduler
        logger.info("🔄 Starting continuous incremental sync scheduler...")
        scheduler_process = self.start_continuous_scheduler()
        
        if scheduler_process:
            logger.info("✅ All scheduled operations setup complete!")
            
            # Monitor the scheduler process
            try:
                while True:
                    if scheduler_process.poll() is not None:
                        logger.error("❌ Scheduler process died, attempting restart...")
                        notify_error("Scheduler Process Died", "Incremental sync scheduler stopped unexpectedly", "Attempting automatic restart")
                        
                        # Wait a bit and restart
                        time.sleep(60)
                        scheduler_process = self.start_continuous_scheduler()
                        
                        if not scheduler_process:
                            logger.error("❌ Failed to restart scheduler, exiting")
                            return False
                    
                    time.sleep(60)  # Check every minute
                    
            except KeyboardInterrupt:
                logger.info("🛑 Received interrupt signal, stopping scheduler...")
                scheduler_process.terminate()
                logger.info("✅ Scheduler stopped gracefully")
                return True
        else:
            logger.error("❌ Failed to start scheduler")
            return False

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup RunSignUp Scheduled Operations')
    parser.add_argument('--test-notifications', action='store_true', help='Test notification system')
    parser.add_argument('--check-status', action='store_true', help='Check current status')
    parser.add_argument('--force-backfill', action='store_true', help='Force backfill even if already completed')
    
    args = parser.parse_args()
    
    manager = ScheduledOperationsManager()
    
    if args.test_notifications:
        logger.info("🧪 Testing notification system...")
        try:
            from notifications import notify_error
            success = notify_error("Test Notification", "This is a test notification from Project88", "Testing SMS integration")
            if success:
                logger.info("✅ Test notification sent successfully")
            else:
                logger.error("❌ Test notification failed")
        except Exception as e:
            logger.error(f"❌ Notification test error: {e}")
        return
    
    if args.check_status:
        logger.info("📊 Current status:")
        reset_time = manager.get_rate_limit_reset_time()
        backfill_done = manager.is_backfill_completed()
        notif_status = get_notification_status()
        
        logger.info(f"⏰ Rate limit resets: {reset_time}")
        logger.info(f"📦 Backfill completed: {backfill_done}")
        logger.info(f"📱 Notification status: {notif_status}")
        return
    
    if args.force_backfill:
        logger.info("🔄 Forcing backfill (removing completion flag)...")
        if os.path.exists(manager.backfill_completed_file):
            os.remove(manager.backfill_completed_file)
    
    # Setup and run all scheduled operations
    try:
        success = manager.setup_scheduled_operations()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        notify_error("Scheduled Operations Fatal Error", str(e), "Critical error in scheduled operations manager")
        sys.exit(1)

if __name__ == "__main__":
    main() 