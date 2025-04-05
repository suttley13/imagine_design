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
    @staticmethod
    def init_app(app):
        ProductionConfig.init_app(app)
        
        # Log cloud run specific settings
        logger.info("Initializing Cloud Run configuration")
        
        # Cloud Run specific configurations
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        
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