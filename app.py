from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

def scrape_website():
    # Get environment variables
    login_url = os.getenv('LOGIN_URL')
    data_url = os.getenv('DATA_URL')
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')

    missing_vars = []
    if not login_url:
        missing_vars.append('LOGIN_URL')
    if not data_url:
        missing_vars.append('DATA_URL')
    if not username:
        missing_vars.append('USERNAME')
    if not password:
        missing_vars.append('PASSWORD')
    
    if missing_vars:
        return {'error': f'Missing environment variables: {", ".join(missing_vars)}'}

    login_payload = {'username': username, 'password': password}

    with requests.Session() as session:
        # Login
        try:
            login_response = session.post(login_url, data=login_payload, timeout=10)
            if login_response.status_code == 401:
                return {'error': 'Invalid credentials'}
            elif login_response.status_code != 200:
                return {'error': f'Login failed with status {login_response.status_code}'}
        except requests.Timeout:
            return {'error': 'Login request timed out'}
        except requests.ConnectionError:
            return {'error': 'Failed to connect to login server'}

        # Scrape data
        response = session.get(data_url)
        if response.status_code != 200:
            return {'error': 'Failed to retrieve data'}

        soup = BeautifulSoup(response.content, 'html.parser')
        # Extract and process data
        data_div = soup.find('div', id='data')
        data = {'key': data_div.text if data_div else 'No data found'}
        return data

@app.route('/data', methods=['GET'])
def get_data():
    data = scrape_website()
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
