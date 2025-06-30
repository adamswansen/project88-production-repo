# API Configuration
API_CONFIG = {
    'BASE_URL': 'https://api.chronotrack.com/api',
    'FORMAT': 'json',
    'CLIENT_ID': '727dae7f',
    'DEFAULT_USER_ID': '',  # You'll need to fill this in
    'DEFAULT_PASSWORD': '',  # You'll need to fill this in
    'DEFAULT_EVENT_ID': ''  # You'll need to fill this in
}

# Protocol Configuration
PROTOCOL_CONFIG = {
    'HOST': '127.0.0.1',
    'PORT': 61611,
    'FORMAT_ID': 'CT01_33',
    'FIELD_SEPARATOR': '~',
    'LINE_TERMINATOR': '\r\n'
}

# Server Configuration
SERVER_CONFIG = {
    'HOST': '0.0.0.0',
    'PORT': 5001,
    'DEBUG': True  # Set to True for development
}

# Random messages for display
RANDOM_MESSAGES = [
    "Great job!",
    "Keep it up!",
    "You're doing amazing!",
    "Almost there!",
    "Looking strong!"
] 