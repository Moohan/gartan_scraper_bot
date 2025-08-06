#!/usr/bin/env python3
"""
Production Flask API Server for Gartan Availability System

Serves REST API endpoints for crew and appliance availability data
"""

from flask import Flask, jsonify, request
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import os

# Import existing API logic
from test_direct_api import (
    get_crew_list_data,
    get_crew_available_data,
    get_crew_duration_data,
    get_appliance_available_data,
    get_appliance_duration_data,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Database configuration
DB_PATH = "gartan_availability.db"


def db_exists():
    """Check if database exists and has data"""
    try:
        if not os.path.exists(DB_PATH):
            return False
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crew")
        crew_count = cursor.fetchone()[0]
        conn.close()
        
        return crew_count > 0
    except Exception:
        return False


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        db_status = db_exists()
        return jsonify({
            "status": "healthy" if db_status else "degraded",
            "database": "connected" if db_status else "no_data",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200 if db_status else 503
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500


@app.route('/v1/crew', methods=['GET'])
def get_crew():
    """Get list of all crew members"""
    try:
        crew_data = get_crew_list_data()
        return jsonify(crew_data)
    except Exception as e:
        logger.error(f"Error getting crew list: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/v1/crew/<int:crew_id>/available', methods=['GET'])
def get_crew_available(crew_id: int):
    """Check if crew member is available right now"""
    try:
        result = get_crew_available_data(crew_id)
        
        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Crew ID {crew_id} not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        
        return jsonify(result["available"])
    except Exception as e:
        logger.error(f"Error checking crew {crew_id} availability: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/v1/crew/<int:crew_id>/duration', methods=['GET'])
def get_crew_duration(crew_id: int):
    """Get crew member's current availability duration"""
    try:
        result = get_crew_duration_data(crew_id)
        
        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Crew ID {crew_id} not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        
        return jsonify(result["duration"])
    except Exception as e:
        logger.error(f"Error getting crew {crew_id} duration: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/v1/appliances/<appliance_name>/available', methods=['GET'])
def get_appliance_available(appliance_name: str):
    """Check if appliance is available right now"""
    try:
        result = get_appliance_available_data(appliance_name)
        
        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Appliance '{appliance_name}' not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        
        return jsonify(result["available"])
    except Exception as e:
        logger.error(f"Error checking appliance {appliance_name} availability: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/v1/appliances/<appliance_name>/duration', methods=['GET'])
def get_appliance_duration(appliance_name: str):
    """Get appliance's current availability duration"""
    try:
        result = get_appliance_duration_data(appliance_name)
        
        if "error" in result:
            if "not found" in result["error"]:
                return jsonify({"error": f"Appliance '{appliance_name}' not found"}), 404
            else:
                return jsonify({"error": "Internal server error"}), 500
        
        return jsonify(result["duration"])
    except Exception as e:
        logger.error(f"Error getting appliance {appliance_name} duration: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # Production configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Gartan API Server on port {port}")
    logger.info(f"Database status: {'Ready' if db_exists() else 'No data - waiting for scraper'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
