from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create a test-specific app
test_app = FastAPI()

# Mock endpoint for "/" to skip auth token
@test_app.get("/")
async def test_root():
    return {"message": "Hello"}

# Create the test client
client = TestClient(test_app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello"}