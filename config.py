import os
from datetime import timedelta
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Base configuration for all environments
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_SECURE = False  # Set to True in production for HTTPS only
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_CHECK_FORM = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    @staticmethod
    def init_app(app):
        pass


# Development configuration
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///dev.db'


# Testing configuration
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///:memory:'


# Production configuration
class ProductionConfig(Config):
    DEBUG = False
    
    # For production, prefer PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # If DATABASE_URL isn't set, fall back to SQLite (not ideal for production)
    if not SQLALCHEMY_DATABASE_URI:
        logger.warning('DATABASE_URL not set, using SQLite (not recommended for production)')
        SQLALCHEMY_DATABASE_URI = 'sqlite:///prod.db'
    
    # In production, use secure cookies
    JWT_COOKIE_SECURE = True


# Cloud Run configuration
class CloudRunConfig(ProductionConfig):
    """Configuration for Google Cloud Run deployment"""
    
    # Cloud Run specific settings
    DEBUG = False
    PREFERRED_URL_SCHEME = 'https'
    
    # Set database URL
    db_url = os.environ.get('DATABASE_URL')
    
    # If DB_URL contains spaces, it might be corrupted
    if db_url and ' ' in db_url:
        # Try to extract actual database URL
        logger.warning(f"DATABASE_URL appears to be malformed: {db_url[:20]}...")
        try:
            # Try to extract the PostgreSQL URL
            if 'postgresql' in db_url:
                parts = db_url.split(' ')
                for part in parts:
                    if part.startswith('postgresql'):
                        db_url = part
                        logger.info(f"Extracted clean DATABASE_URL")
                        break
        except Exception as e:
            logger.error(f"Failed to clean DATABASE_URL: {str(e)}")
            db_url = None
            
    # Set the database URL
    if db_url:
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        # Fallback to standard Cloud SQL connection format
        logger.warning("Using fallback Cloud SQL connection string")
        instance = os.environ.get('INSTANCE_CONNECTION_NAME', 
                                 'designai-454112:us-central1:redesign-ai-db')
        db_name = os.environ.get('DB_NAME', 'redesign_db')
        db_user = os.environ.get('DB_USER', 'postgres')
        db_pass = os.environ.get('DB_PASS', '')
        
        # Handle empty password case - PostgreSQL treats empty string as no password
        db_pass_segment = f":{db_pass}" if db_pass else ""
        
        # Build connection string with conditional password segment
        SQLALCHEMY_DATABASE_URI = f"postgresql://{db_user}{db_pass_segment}@/{db_name}?host=/cloudsql/{instance}"
        logger.info(f"Using connection string: postgresql://{db_user}:*****@/{db_name}?host=/cloudsql/{instance}")
    
    @staticmethod
    def init_app(app):
        ProductionConfig.init_app(app)
        
        # Log cloud run specific settings
        logger.info("Initializing Cloud Run configuration")
        
        # Cloud Run specific configurations
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        
        # Add Cloud Run-specific error logging
        import logging
        from logging import StreamHandler
        
        stream_handler = StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        
        # Additional Cloud Run specific settings could go here
        logger.info("Cloud Run configuration complete")


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'cloud_run': CloudRunConfig,
    'default': DevelopmentConfig
} 