import pytest

from app import create_app
from app.extensions import db as _db
from app.models import User


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


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
