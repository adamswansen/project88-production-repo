import socket
import logging
import threading
import queue
import json
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

class ChronoTrackClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.auth_token: Optional[str] = None
        self.event_info: Optional[Dict] = None
        self.locations: List[str] = []
        self._lock = threading.Lock()
        self._response_queue = queue.Queue()
        self._listener_thread: Optional[threading.Thread] = None

    def connect(self) -> bool:
        """Establish connection to ChronoTrack server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            self._start_listener()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ChronoTrack server: {e}")
            return False

    def disconnect(self):
        """Close connection to ChronoTrack server"""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"Error closing socket: {e}")
        self.connected = False
        self.socket = None
        self.auth_token = None

    def _start_listener(self):
        """Start background thread to listen for server responses"""
        def listener():
            buffer = ""
            while self.connected:
                try:
                    data = self.socket.recv(4096).decode('utf-8')
                    if not data:
                        break
                    buffer += data
                    while '~' in buffer:
                        message, buffer = buffer.split('~', 1)
                        self._response_queue.put(message)
                except Exception as e:
                    logger.error(f"Error in listener thread: {e}")
                    break
            self.connected = False

        self._listener_thread = threading.Thread(target=listener, daemon=True)
        self._listener_thread.start()

    def _send_command(self, *args) -> str:
        """Send command to server and wait for response"""
        if not self.connected:
            raise ConnectionError("Not connected to server")

        command = '~'.join(str(arg) for arg in args)
        try:
            with self._lock:
                self.socket.sendall(f"{command}\n".encode('utf-8'))
                response = self._response_queue.get(timeout=5)
                return response
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            raise

    def get_protocol(self) -> bool:
        """Get protocol version from server"""
        try:
            response = self._send_command("client", "getprotocol")
            return response.startswith("ack")
        except Exception as e:
            logger.error(f"Error getting protocol: {e}")
            return False

    def authorize(self, user_id: str, password: str) -> bool:
        """Authorize with server"""
        try:
            response = self._send_command("authorize", user_id, password)
            if response.startswith("ack"):
                self.auth_token = response.split("~")[1]
                return True
            return False
        except Exception as e:
            logger.error(f"Error authorizing: {e}")
            return False

    def get_event_info(self) -> Optional[Dict]:
        """Get current event information"""
        try:
            response = self._send_command("geteventinfo")
            if response.startswith("ack"):
                _, name, event_id, desc = response.split("~")
                self.event_info = {
                    "name": name,
                    "id": event_id,
                    "description": desc
                }
                return self.event_info
            return None
        except Exception as e:
            logger.error(f"Error getting event info: {e}")
            return None

    def get_locations(self) -> List[str]:
        """Get available locations"""
        try:
            response = self._send_command("getlocations")
            if response.startswith("ack"):
                self.locations = response.split("~")[1:]
                return self.locations
            return []
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return []

    def get_connection_id(self) -> Optional[str]:
        """Get connection ID for resuming session"""
        try:
            response = self._send_command("getconnectionid")
            if response.startswith("ack"):
                return response.split("~")[1]
            return None
        except Exception as e:
            logger.error(f"Error getting connection ID: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self.connected and self.socket is not None 