from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
response = client.get('/')
print('status_code:', response.status_code)
print(response.text[:2000])
