import pytest

from app import create_app
from app.extensions import db as _db
from app.models import User
from app.services.courses.registry import init_course_provider

GOLF_API_TEST_BASE_URL = 'https://api.golfcourseapi.com'


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def api_app():
    """An app with the golfcourseapi provider configured (GOLF_API_KEY set).

    Shared by any test that needs the "Import from API" affordance to be
    live -- e.g. search/import routes, or the flags that hide those routes
    when no key is set.
    """
    app = create_app('testing')
    app.config['GOLF_API_KEY'] = 'test-key'
    app.config['GOLF_API_BASE_URL'] = GOLF_API_TEST_BASE_URL
    init_course_provider(app)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def api_client(api_app):
    return api_app.test_client()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(db):
    def _make_user(username='dan', email='dan@example.com', password='password123'):
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    return _make_user


@pytest.fixture
def auth_user(make_user):
    return make_user()


def login(client, username='dan', password='password123'):
    return client.post('/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)
