import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'golf_scores.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BOOTSTRAP_SERVE_LOCAL = True
    GOLF_API_KEY = os.environ.get('GOLF_API_KEY')
    GOLF_API_BASE_URL = 'https://api.golfcourseapi.com'
    GOLF_API_DAILY_QUOTA = 50

    @staticmethod
    def init_app(app):
        if not app.config['SECRET_KEY']:
            if app.config['DEBUG'] or app.config['TESTING']:
                app.config['SECRET_KEY'] = 'dev-only-insecure-key'
            else:
                raise RuntimeError(
                    'SECRET_KEY environment variable must be set in production')


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'


config = {
    'development': DevConfig,
    'testing': TestConfig,
    'production': Config,
    'default': DevConfig,
}
