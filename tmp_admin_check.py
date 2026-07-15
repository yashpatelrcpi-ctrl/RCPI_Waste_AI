from app import app
from fastapi.testclient import TestClient

client = TestClient(app)
resp = client.get('/admin-dashboard')
print('status=', resp.status_code)
print('contains_admin=', 'Admin Dashboard' in resp.text or 'Dashboard' in resp.text)
print(resp.text[:200])
