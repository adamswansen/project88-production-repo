import redis
import json
import logging
import threading
from typing import Dict, Optional
from chronotrack_client import ChronoTrackClient

logger = logging.getLogger(__name__)

class ChronoTrackManager:
    def __init__(self, redis_url: str = 'redis://localhost:6379/0'):
        self.redis = redis.from_url(redis_url)
        self.clients: Dict[str, ChronoTrackClient] = {}
        self._lock = threading.Lock()
        self._pubsub = self.redis.pubsub()
        self._pubsub.subscribe('chronotrack_commands')
        self._start_command_listener()

    def _start_command_listener(self):
        """Start background thread to listen for Redis commands"""
        def listener():
            for message in self._pubsub.listen():
                if message['type'] == 'message':
                    try:
                        command = json.loads(message['data'])
                        self._handle_command(command)
                    except Exception as e:
                        logger.error(f"Error handling command: {e}")

        thread = threading.Thread(target=listener, daemon=True)
        thread.start()

    def _handle_command(self, command: Dict):
        """Handle commands received via Redis"""
        action = command.get('action')
        session_id = command.get('session_id')
        
        if not action or not session_id:
            return

        if action == 'connect':
            self.connect_client(
                session_id,
                command.get('host'),
                command.get('port'),
                command.get('user_id'),
                command.get('password')
            )
        elif action == 'disconnect':
            self.disconnect_client(session_id)
        elif action == 'get_event_info':
            self.get_event_info(session_id)
        elif action == 'get_locations':
            self.get_locations(session_id)

    def connect_client(self, session_id: str, host: str, port: int, 
                      user_id: str, password: str) -> bool:
        """Connect a new ChronoTrack client"""
        with self._lock:
            if session_id in self.clients:
                self.disconnect_client(session_id)

            client = ChronoTrackClient(host, port)
            if not client.connect():
                return False

            if not client.get_protocol():
                client.disconnect()
                return False

            if not client.authorize(user_id, password):
                client.disconnect()
                return False

            self.clients[session_id] = client
            self._publish_status(session_id, 'connected')
            return True

    def disconnect_client(self, session_id: str):
        """Disconnect a ChronoTrack client"""
        with self._lock:
            if session_id in self.clients:
                self.clients[session_id].disconnect()
                del self.clients[session_id]
                self._publish_status(session_id, 'disconnected')

    def get_event_info(self, session_id: str) -> Optional[Dict]:
        """Get event info for a session"""
        with self._lock:
            if session_id not in self.clients:
                return None
            
            client = self.clients[session_id]
            event_info = client.get_event_info()
            if event_info:
                self._publish_event_info(session_id, event_info)
            return event_info

    def get_locations(self, session_id: str) -> list:
        """Get locations for a session"""
        with self._lock:
            if session_id not in self.clients:
                return []
            
            client = self.clients[session_id]
            locations = client.get_locations()
            if locations:
                self._publish_locations(session_id, locations)
            return locations

    def _publish_status(self, session_id: str, status: str):
        """Publish connection status to Redis"""
        self.redis.publish(
            f'chronotrack_status_{session_id}',
            json.dumps({'status': status})
        )

    def _publish_event_info(self, session_id: str, event_info: Dict):
        """Publish event info to Redis"""
        self.redis.publish(
            f'chronotrack_event_{session_id}',
            json.dumps(event_info)
        )

    def _publish_locations(self, session_id: str, locations: list):
        """Publish locations to Redis"""
        self.redis.publish(
            f'chronotrack_locations_{session_id}',
            json.dumps(locations)
        )

    def get_client(self, session_id: str) -> Optional[ChronoTrackClient]:
        """Get client for a session"""
        return self.clients.get(session_id)

    def is_connected(self, session_id: str) -> bool:
        """Check if a session is connected"""
        client = self.get_client(session_id)
        return client is not None and client.is_connected() 