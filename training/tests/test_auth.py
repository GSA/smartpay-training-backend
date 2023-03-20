from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
import jwt
import pytest

from training.api.auth import JWTUser
from training.config import settings

app = FastAPI()
settings.JWT_SECRET = 'super_secret'


@pytest.fixture
def user():
    return {
        'name': 'Leopold Bloom',
        'email': 'lbloom@sandymount.com'
    }


@pytest.fixture
def goodJWT(user):
    return jwt.encode(user, settings.JWT_SECRET, algorithm="HS256")


@pytest.fixture
def badJWT(user):
    return jwt.encode(user, 'hakzors', algorithm="HS256")


@app.get("/home")
def read_current_user(user=Depends(JWTUser())):
    return user


client = TestClient(app)


def test_valid_jwt(goodJWT, user):
    response = client.get("/home", headers={"Authorization": f"Bearer {goodJWT}"})
    assert response.status_code == 200
    assert response.json() == user


def test_invalid_jwt(badJWT, user):
    response = client.get("/home", headers={"Authorization": f"Bearer {badJWT}"})
    assert response.status_code == 403
    assert response.json() == {'detail': 'Invalid or expired token.'}


def test_missing_jwt(badJWT, user):
    response = client.get("/home")
    assert response.status_code == 403
    assert response.json() == {'detail': 'Not authenticated'}
