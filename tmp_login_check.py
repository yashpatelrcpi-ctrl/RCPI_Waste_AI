from app import app
from fastapi.testclient import TestClient

client = TestClient(app)
response = client.post('/citizen-login', data={'username': 'test_citizen', 'password': 'citizen@123'})
print('status=', response.status_code)
print('location=', response.headers.get('location'))
