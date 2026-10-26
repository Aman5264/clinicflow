import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clinicflow-dev-secret-key-change-in-production-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///clinicflow.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    ITEMS_PER_PAGE = 10

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
