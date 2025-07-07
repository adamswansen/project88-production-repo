"""
Configuration management for Project88 Dashboard
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    
    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'project88_myappdb')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    
    # Application
    PORT = int(os.getenv('PORT', '5004'))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Cache
    CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))
    
    @classmethod
    def get_db_config(cls):
        """Get database configuration dictionary"""
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'database': cls.DB_NAME,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
        }
    
    @classmethod
    def get_redis_config(cls):
        """Get Redis configuration dictionary"""
        return {
            'host': cls.REDIS_HOST,
            'port': cls.REDIS_PORT,
            'db': cls.REDIS_DB,
        }

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    CACHE_TTL = 60  # Shorter cache for development

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    DB_NAME = 'project88_test_db'
    CACHE_TTL = 1  # Very short cache for testing

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration class based on environment"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return config_map.get(config_name, DevelopmentConfig) 