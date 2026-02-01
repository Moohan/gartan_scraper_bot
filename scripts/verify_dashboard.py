from api_server import app
from benchmark_api_flask import setup_dummy_data

def verify_dashboard():
    setup_dummy_data()
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode()
    assert 'Managing Station: P22' in html
    assert 'Crew' in html
    assert 'Officer' in html
    # Check if some crew members are listed
    assert 'Crew 0' in html
    assert 'AVAILABLE' in html
    print("Dashboard verification PASSED")

if __name__ == "__main__":
    verify_dashboard()
