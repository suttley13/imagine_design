import os
from datetime import timedelta

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
        'sqlite:///test.db'
    WTF_CSRF_ENABLED = False


# Production configuration
class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///prod.db'
    JWT_COOKIE_SECURE = True  # Only send cookies over HTTPS
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Configure production-specific logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler('logs/redesign_ai.log', maxBytes=10485760, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('RedesignAI startup')


# Cloud Run configuration
class CloudRunConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        
        # Log to stdout/stderr for Cloud Run
        import logging
        from logging import StreamHandler
        
        file_handler = StreamHandler()
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        
        # Handle proxy server headers
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'cloud_run': CloudRunConfig,
    'default': DevelopmentConfig
} 