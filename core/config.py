from typing import Dict

def get_settings() -> Dict:
    """Return default settings for the app."""
    return {
        "host": "127.0.0.1",
        "port": 8000
    }
