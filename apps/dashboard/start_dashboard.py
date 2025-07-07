#!/usr/bin/env python3
"""
Project88 Dashboard Startup Script
Production-ready startup with proper configuration
"""

import os
import sys
import logging
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main startup function"""
    try:
        # Import after path is set
        from app import app, db
        from config import get_config
        
        # Get configuration
        config = get_config()
        
        # Test database connection
        logger.info("Testing database connection...")
        db.execute_query("SELECT 1")
        logger.info("Database connection successful")
        
        # Start the application
        logger.info(f"Starting Project88 Dashboard on port {config.PORT}")
        logger.info(f"Debug mode: {config.DEBUG}")
        logger.info(f"Database: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
        
        app.run(
            host='0.0.0.0',
            port=config.PORT,
            debug=config.DEBUG,
            threaded=True
        )
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 