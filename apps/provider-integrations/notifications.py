#!/usr/bin/env python3
"""
Notification system for Project88 RunSignUp integration
Handles Twilio SMS notifications for backfill success, sync success, and errors
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional
from twilio.rest import Client

logger = logging.getLogger(__name__)

class TwilioNotifier:
    """Twilio SMS notification system with state tracking"""
    
    def __init__(self):
        # Twilio credentials from environment variables
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "YOUR_TWILIO_ACCOUNT_SID")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "YOUR_TWILIO_AUTH_TOKEN")
        self.from_number = os.environ.get("TWILIO_FROM_NUMBER", "+1XXXXXXXXXX")
        self.to_number = os.environ.get("TWILIO_TO_NUMBER", "+1XXXXXXXXXX")
        
        # State tracking file
        self.state_file = "/tmp/twilio_notifications_state.json"
        self.state = self._load_state()
        
        # Initialize Twilio client
        try:
            # Set environment variables for Twilio traditional authentication
            os.environ["TWILIO_ACCOUNT_SID"] = self.account_sid
            os.environ["TWILIO_AUTH_TOKEN"] = self.auth_token
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self.client = None

    def _load_state(self) -> dict:
        """Load notification state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load notification state: {e}")
        
        # Default state
        return {
            "backfill_success_sent": False,
            "incremental_success_sent": False,
            "last_error_time": None,
            "total_errors_sent": 0
        }

    def _save_state(self):
        """Save notification state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save notification state: {e}")

    def _send_sms(self, message: str) -> bool:
        """Send SMS via Twilio"""
        if not self.client:
            logger.error("Twilio client not initialized, cannot send SMS")
            return False
        
        try:
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=self.to_number
            )
            logger.info(f"SMS sent successfully: {twilio_message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    def notify_backfill_success(self, events_count: int, races_count: int, participants_count: int) -> bool:
        """Send one-time notification for successful backfill completion"""
        if self.state["backfill_success_sent"]:
            logger.info("Backfill success notification already sent, skipping")
            return True
        
        message = f"""🎉 Project88 RunSignUp Backfill Complete!

✅ Events: {events_count:,}
✅ Races: {races_count:,} 
✅ Participants: {participants_count:,}

Backfill completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC.
Incremental sync scheduler is now active."""
        
        success = self._send_sms(message)
        if success:
            self.state["backfill_success_sent"] = True
            self._save_state()
            logger.info("Backfill success notification sent and state updated")
        
        return success

    def notify_incremental_success(self, events_synced: int, participants_synced: int) -> bool:
        """Send one-time notification for successful incremental sync"""
        if self.state["incremental_success_sent"]:
            logger.info("Incremental sync success notification already sent, skipping")
            return True
        
        message = f"""✅ Project88 Incremental Sync Working!

📊 First incremental sync complete:
• Events processed: {events_synced:,}
• Participants synced: {participants_synced:,}

Incremental sync is running every 15 minutes.
Only errors will be reported going forward."""
        
        success = self._send_sms(message)
        if success:
            self.state["incremental_success_sent"] = True
            self._save_state()
            logger.info("Incremental sync success notification sent and state updated")
        
        return success

    def notify_error(self, error_type: str, error_message: str, context: str = "") -> bool:
        """Send error notification (always sent)"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        message = f"""🚨 Project88 RunSignUp Error

❌ Type: {error_type}
⏰ Time: {timestamp} UTC
📝 Details: {error_message[:200]}{'...' if len(error_message) > 200 else ''}"""
        
        if context:
            context_suffix = '...' if len(context) > 100 else ''
            message += f"\n🔍 Context: {context[:100]}{context_suffix}"
        
        success = self._send_sms(message)
        if success:
            self.state["last_error_time"] = timestamp
            self.state["total_errors_sent"] = self.state.get("total_errors_sent", 0) + 1
            self._save_state()
            logger.info(f"Error notification sent (total errors: {self.state['total_errors_sent']})")
        
        return success

    def get_notification_status(self) -> dict:
        """Get current notification status"""
        return {
            "backfill_success_sent": self.state["backfill_success_sent"],
            "incremental_success_sent": self.state["incremental_success_sent"],
            "total_errors_sent": self.state.get("total_errors_sent", 0),
            "last_error_time": self.state.get("last_error_time"),
            "client_ready": self.client is not None
        }

# Global notifier instance
notifier = TwilioNotifier()

def notify_backfill_success(events_count: int, races_count: int, participants_count: int) -> bool:
    """Convenience function for backfill success notification"""
    return notifier.notify_backfill_success(events_count, races_count, participants_count)

def notify_incremental_success(events_synced: int, participants_synced: int) -> bool:
    """Convenience function for incremental sync success notification"""
    return notifier.notify_incremental_success(events_synced, participants_synced)

def notify_error(error_type: str, error_message: str, context: str = "") -> bool:
    """Convenience function for error notifications"""
    return notifier.notify_error(error_type, error_message, context)

def get_notification_status() -> dict:
    """Convenience function to get notification status"""
    return notifier.get_notification_status()
