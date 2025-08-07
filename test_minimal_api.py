#!/usr/bin/env python3
"""
Minimal API test to isolate issues
"""

import sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify
import pytest

app = Flask(__name__)


@app.route("/test")
def api_test_endpoint():
    """Simple test endpoint"""
    return jsonify({"status": "ok", "message": "API is working"})


@app.route("/db-test")
def db_test():
    """Test database connection"""
    try:
        conn = sqlite3.connect("gartan_availability.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM crew")
        result = cursor.fetchone()
        conn.close()
        return jsonify({"status": "ok", "crew_count": result["count"]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def test_minimal_api():
    """Test the API endpoints with proper Flask context"""
    with app.test_client() as client:
        # Test the basic endpoint
        response = client.get("/test")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["message"] == "API is working"


if __name__ == "__main__":
    print("Starting minimal API server...")
    app.run(debug=False, host="127.0.0.1", port=5001, use_reloader=False)
