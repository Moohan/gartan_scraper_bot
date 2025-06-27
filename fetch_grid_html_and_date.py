import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

LOGIN_URL = 'https://grampianrds.firescotland.gov.uk/GartanAvailability/Account/Login.aspx'
DATA_URL = 'https://grampianrds.firescotland.gov.uk/GartanAvailability/Availability/Schedule/AvailabilityMain1.aspx?UseDefaultStation=1'
USERNAME = os.environ.get('GARTAN_USERNAME')
PASSWORD = os.environ.get('GARTAN_PASSWORD')

assert USERNAME and PASSWORD, 'GARTAN_USERNAME and GARTAN_PASSWORD must be set in .env'

from datetime import datetime


def gartan_login_and_get_session():
    """
    Logs in and returns an authenticated requests.Session().
    """
    session = requests.Session()
    # Step 1: Get login page
    resp = session.get(LOGIN_URL)
    soup = BeautifulSoup(resp.content, 'html.parser')
    # Find the login form and its action
    form = soup.find('form')
    if not form:
        raise Exception('Login form not found in page')
    action = form.get('action')
    # Defensive: ensure action is a string
    if not action or not isinstance(action, str):
        post_url = LOGIN_URL
    elif isinstance(action, str) and action.startswith('http'):
        post_url = action
    else:
        from urllib.parse import urljoin
        post_url = urljoin(LOGIN_URL, str(action))

    # Collect all input fields in the form (defensively handle BeautifulSoup types)
    payload = {}
    input_tags = []
    try:
        input_tags = list(form.find_all('input'))
    except Exception:
        # fallback: try iterating children
        input_tags = [el for el in form.descendants if getattr(el, 'name', None) == 'input']
    for input_tag in input_tags:
        try:
            name = input_tag.get('name') if hasattr(input_tag, 'get') else None
            if not name:
                continue
            value = input_tag.get('value', '') if hasattr(input_tag, 'get') else ''
            payload[name] = value
        except Exception:
            continue

    # Overwrite with actual credentials
    payload['txt_userid'] = USERNAME
    payload['txt_pword'] = PASSWORD
    # The login button value may be required
    if 'btnLogin' not in payload:
        # Find the login button by iterating inputs (since .find with attrs dict can be unreliable)
        login_button_value = 'Sign In'
        for input_tag in input_tags:
            try:
                if hasattr(input_tag, 'get') and input_tag.get('name') == 'btnLogin':
                    login_button_value = input_tag.get('value', 'Sign In')
                    break
            except Exception:
                continue
        payload['btnLogin'] = login_button_value

    # Post login with all fields and cookies
    headers = {
        'Referer': LOGIN_URL,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    }
    login_resp = session.post(post_url, data=payload, headers=headers)
    print(f"Login POST status: {login_resp.status_code}")
    if login_resp.is_redirect or login_resp.is_permanent_redirect:
        print(f"Login POST redirect location: {login_resp.headers.get('Location')}")
    # Check for visible login error message
    soup_resp = BeautifulSoup(login_resp.text, 'html.parser')
    login_msg = soup_resp.find(class_='loginMessage')
    if login_msg and login_msg.text.strip():
        print(f'WARNING: Login message detected: {login_msg.text.strip()} (see login_response.html for details)')
    if 'invalid' in login_resp.text.lower() or 'incorrect' in login_resp.text.lower():
        print('WARNING: Possible login error detected in response text. See login_response.html for details.')
    # Step 2: Get data page (after possible redirect)
    data_resp = session.get(DATA_URL, headers=headers)
    print(f"Data page GET status: {data_resp.status_code}")
    if data_resp.status_code != 200:
        raise Exception(f'Failed to retrieve data page: {data_resp.status_code}')
    return session

def fetch_grid_html_for_date(session, booking_date):
    """
    Given an authenticated session and a booking_date (str, dd/mm/yyyy), fetch the grid HTML for that date.
    Returns grid_html or None.
    """
    import json
    schedule_url = 'https://grampianrds.firescotland.gov.uk/GartanAvailability/Availability/Schedule/AvailabilityMain1.aspx/GetSchedule'
    schedule_payload = {
        "brigadeId": 47,
        "brigadeName": "P22 Dunkeld",
        "employeeBrigadeId": 0,
        "bookingDate": booking_date,
        "resolution": 15,
        "dayCount": 0,
        "showDetails": "true",
        "showHours": "true",
        "highlightContractDetails": "false",
        "highlightEmployeesOffStation": "true",
        "includeApplianceStatus": "true"
    }
    headers = {
        'Referer': DATA_URL,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest"
    }
    schedule_resp = session.post(schedule_url, headers=headers, data=json.dumps(schedule_payload))
    print(f"Schedule AJAX status for {booking_date}: {schedule_resp.status_code}")
    try:
        grid_html = schedule_resp.json().get('d', '')
        print(f'Fetched grid HTML from AJAX response for {booking_date}')
        return grid_html
    except Exception as e:
        print(f"Could not extract grid HTML for {booking_date}: {e}")
        return None
