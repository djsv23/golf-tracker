from tests.conftest import login


def test_register_login_protected_page_logout(client, db):
    resp = client.post('/register', data={
        'username': 'dan',
        'email': 'dan@example.com',
        'password': 'password123',
        'password2': 'password123',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Sign In' in resp.data

    resp = client.get('/', follow_redirects=True)
    assert b'Sign In' in resp.data

    resp = login(client)
    assert resp.status_code == 200
    assert b'Hello, dan!' in resp.data

    resp = client.get('/logout', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Sign In' in resp.data

    resp = client.get('/', follow_redirects=True)
    assert b'Sign In' in resp.data


def test_login_invalid_password(client, auth_user):
    resp = login(client, password='wrong-password')
    assert b'Invalid username or password' in resp.data


def test_register_duplicate_username(client, auth_user):
    resp = client.post('/register', data={
        'username': 'dan',
        'email': 'someoneelse@example.com',
        'password': 'password123',
        'password2': 'password123',
    })
    assert b'Please use a different username' in resp.data


def test_register_duplicate_email(client, auth_user):
    resp = client.post('/register', data={
        'username': 'someoneelse',
        'email': 'dan@example.com',
        'password': 'password123',
        'password2': 'password123',
    })
    assert b'Please use a different email address' in resp.data


def test_user_profile_page(client, auth_user):
    login(client)
    resp = client.get('/user/dan')
    assert resp.status_code == 200
    assert b'User: dan' in resp.data


def test_edit_profile(client, auth_user, db):
    login(client)
    resp = client.post('/edit_profile', data={
        'username': 'dan2',
        'about_me': 'hello world',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Your changes have been saved' in resp.data
    assert auth_user.username == 'dan2'
