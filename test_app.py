import pytest
from app import app, scrape_website
import os

# Test the scraping function
def test_scrape_website(monkeypatch):
    class MockResponse:
        @property
        def content(self):
            return '<html><body><div id="data">Test Data</div></body></html>'

    def mock_post(*args, **kwargs):
        return MockResponse()

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr('requests.Session.post', mock_post)
    monkeypatch.setattr('requests.Session.get', mock_get)

    monkeypatch.setenv('LOGIN_URL', 'https://example.com/login')
    monkeypatch.setenv('DATA_URL', 'https://example.com/data')
    monkeypatch.setenv('USERNAME', 'your_username')
    monkeypatch.setenv('PASSWORD', 'your_password')

    data = scrape_website()
    assert data == {'key': 'Test Data'}  # Adjust this based on your actual data extraction logic

# Test the Flask API endpoint
def test_get_data(client):
    response = client.get('/data')
    assert response.status_code == 200
    assert response.json == {'key': 'Test Data'}  # Adjust this based on your actual data extraction logic

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client
