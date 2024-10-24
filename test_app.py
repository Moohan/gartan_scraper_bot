import pytest
from app import app, scrape_website

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

    data = scrape_website()
    assert data == {'key': 'value'}  # Adjust this based on your actual data extraction logic

# Test the Flask API endpoint
def test_get_data(client):
    response = client.get('/data')
    assert response.status_code == 200
    assert response.json == {'key': 'value'}  # Adjust this based on your actual data extraction logic

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client
