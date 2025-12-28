"""Basic tests for PlanMinCIT API"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.session import Base, get_db
from app.models.user import User, UserRole
from app.models.instrument import Instrument, InstrumentCode
from app.core.security import get_password_hash

# Test database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Test client
client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Setup and teardown test database for each test"""
    Base.metadata.create_all(bind=engine)
    
    # Seed instruments
    db = TestingSessionLocal()
    instruments = [
        Instrument(code=InstrumentCode.RURAL, name="Rural"),
        Instrument(code=InstrumentCode.URBANO, name="Urbano"),
        Instrument(code=InstrumentCode.REGION, name="Region"),
    ]
    for inst in instruments:
        db.add(inst)
    
    # Create admin user
    admin = User(
        email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin)
    db.commit()
    db.close()
    
    yield
    
    Base.metadata.drop_all(bind=engine)


def test_public_home():
    """Test public home endpoint"""
    response = client.get("/public/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_login_success():
    """Test successful login"""
    response = client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_failure():
    """Test failed login with wrong credentials"""
    response = client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_get_me_as_admin():
    """Test /auth/me endpoint as admin"""
    # Login first
    login_response = client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "admin123"}
    )
    token = login_response.json()["access_token"]
    
    # Get user info
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "ADMIN"
    assert data["email"] == "admin@test.com"


def test_create_authority_as_admin():
    """Test creating authority user as admin"""
    # Login as admin
    login_response = client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "admin123"}
    )
    token = login_response.json()["access_token"]
    
    # Create authority
    response = client.post(
        "/admin/authorities",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "municipio@test.com",
            "password": "password123",
            "authority_type": "MUNICIPIO",
            "display_name": "Municipio de Prueba",
            "instrument_assignments": [
                {"instrument_code": "RURAL", "role": "LEADER_PLANNING"},
                {"instrument_code": "URBANO", "role": "STRATEGIC_ALLY"},
                {"instrument_code": "REGION", "role": "STRATEGIC_ALLY"}
            ]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "municipio@test.com"
    assert data["authority_type"] == "MUNICIPIO"
    assert len(data["instrument_assignments"]) == 3


def test_create_authority_duplicate_leader_fails():
    """Test that creating second leader for same instrument fails"""
    # Login as admin
    login_response = client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "admin123"}
    )
    token = login_response.json()["access_token"]
    
    # Create first authority as leader of RURAL
    client.post(
        "/admin/authorities",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "leader1@test.com",
            "password": "password123",
            "authority_type": "MUNICIPIO",
            "display_name": "Leader 1",
            "instrument_assignments": [
                {"instrument_code": "RURAL", "role": "LEADER_PLANNING"},
                {"instrument_code": "URBANO", "role": "STRATEGIC_ALLY"},
                {"instrument_code": "REGION", "role": "STRATEGIC_ALLY"}
            ]
        }
    )
    
    # Try to create second leader for RURAL - should fail
    response = client.post(
        "/admin/authorities",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "leader2@test.com",
            "password": "password123",
            "authority_type": "DEPARTAMENTO",
            "display_name": "Leader 2",
            "instrument_assignments": [
                {"instrument_code": "RURAL", "role": "LEADER_PLANNING"},  # Duplicate leader
                {"instrument_code": "URBANO", "role": "STRATEGIC_ALLY"},
                {"instrument_code": "REGION", "role": "STRATEGIC_ALLY"}
            ]
        }
    )
    assert response.status_code == 400
    assert "líder" in response.json()["detail"].lower()


def test_authority_cannot_access_admin_endpoints():
    """Test that authority user cannot access admin endpoints"""
    # Login as admin and create authority
    admin_login = client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "admin123"}
    )
    admin_token = admin_login.json()["access_token"]
    
    client.post(
        "/admin/authorities",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "authority@test.com",
            "password": "password123",
            "authority_type": "MUNICIPIO",
            "display_name": "Authority Test",
            "instrument_assignments": [
                {"instrument_code": "RURAL", "role": "STRATEGIC_ALLY"},
                {"instrument_code": "URBANO", "role": "STRATEGIC_ALLY"},
                {"instrument_code": "REGION", "role": "STRATEGIC_ALLY"}
            ]
        }
    )
    
    # Login as authority
    authority_login = client.post(
        "/auth/login",
        json={"email": "authority@test.com", "password": "password123"}
    )
    authority_token = authority_login.json()["access_token"]
    
    # Try to access admin endpoint - should fail
    response = client.get(
        "/admin/authorities",
        headers={"Authorization": f"Bearer {authority_token}"}
    )
    assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
