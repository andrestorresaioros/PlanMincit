import requests
import json

login_data = {"email": "admin@example.com", "password": "admin123"}
print("🔐 Intentando login...")
login_response = requests.post("http://localhost:8000/auth/login", json=login_data)
print(f"Status: {login_response.status_code}")

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print(f"✅ Token obtenido\n")
    
    headers = {"Authorization": f"Bearer {token}"}
    authority_data = {
        "email": "testuser@example.com",
        "password": "test12345",
        "display_name": "Municipio Test",
        "authority_type": "MUNICIPIO",
        "instrument_assignments": [{
            "instrument_code": "RURAL",
            "role": "STRATEGIC_ALLY",
            "territory_name": "Territorio Test"
        }]
    }
    
    print("📤 Enviando:", json.dumps(authority_data, indent=2))
    create_response = requests.post("http://localhost:8000/admin/authorities", json=authority_data, headers=headers)
    print(f"\n📥 Respuesta: Status {create_response.status_code}")
    print(json.dumps(create_response.json(), indent=2))
else:
    print(f"❌ Error en login: {login_response.json()}")
