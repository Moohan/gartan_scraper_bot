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

    if not all([login_url, data_url, username, password]):
        return {'error': 'Missing environment variables'}

    login_payload = {'username': username, 'password': password}

    with requests.Session() as session:
        # Login
        login_response = session.post(login_url, data=login_payload)
        if login_response.status_code != 200:
            return {'error': 'Login failed'}

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
