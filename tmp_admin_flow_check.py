from app import app
from fastapi.testclient import TestClient

client = TestClient(app)
resp = client.post('/admin-complaints', data={
    'complaint_id': 1,
    'status': 'In Progress',
    'priority': 'High',
    'remarks': 'Assigned by admin',
    'assigned_driver': 'Driver One',
    'assigned_ward_officer': 'Officer Rao',
})
print('admin_update_status=', resp.status_code)
print('location=', resp.headers.get('location'))
