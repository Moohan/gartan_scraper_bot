#!/usr/bin/env python3
"""
Minimal API test to isolate issues
"""

import sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/test")
def test():
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


if __name__ == "__main__":
    print("Starting minimal API server...")
    app.run(debug=False, host="127.0.0.1", port=5001, use_reloader=False)
