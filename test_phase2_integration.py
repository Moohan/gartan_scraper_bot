"""
Integration tests for Phase 2 improvements.

Tests the complete integration of error handling, configuration management,
enhanced logging, and refined API layer.
"""

import pytest
import tempfile
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Import all Phase 2 modules
from error_handling import ErrorHandler, GartanError, ErrorCategory, ErrorSeverity
from unified_config import GartanConfig, CacheMode, LogLevel, DatabaseConfig, CacheConfig
from enhanced_logging import LogManager, get_logger, track_performance, log_context
from refined_api import APICore, APIResponse
from config_migration import ConfigMigrator

class TestPhase2ErrorHandling:
    """Test Phase 2.1: Error Handling Standardization."""
    
    def test_error_classification(self):
        """Test automatic error classification."""
        handler = ErrorHandler()
        
        # Test different exception types
        db_error = sqlite3.Error("Database locked")
        classified = handler.classify_exception(db_error)
        assert classified.category == ErrorCategory.DATABASE
        assert classified.severity == ErrorSeverity.MEDIUM  # Database locked is MEDIUM severity
        
        network_error = ConnectionError("Connection failed")
        classified = handler.classify_exception(network_error)
        assert classified.category == ErrorCategory.NETWORK
        assert classified.severity == ErrorSeverity.MEDIUM
    
    def test_error_statistics(self):
        """Test error statistics tracking."""
        handler = ErrorHandler()
        
        # Generate some errors using legacy interface
        handler.handle_error_legacy(ErrorCategory.DATABASE, ErrorSeverity.HIGH, "DB Error 1")
        handler.handle_error_legacy(ErrorCategory.DATABASE, ErrorSeverity.MEDIUM, "DB Error 2")
        handler.handle_error_legacy(ErrorCategory.NETWORK, ErrorSeverity.LOW, "Network Warning")
        
        stats = handler.get_statistics()
        assert stats['total_errors'] == 3
        assert stats['by_category'][ErrorCategory.DATABASE.value] == 2
        assert stats['by_severity'][ErrorSeverity.HIGH.value] == 1
    
    def test_error_recovery(self):
        """Test error recovery mechanisms."""
        handler = ErrorHandler()
        
        call_count = 0
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        # Test retry mechanism
        result = handler.with_retry(failing_function, max_retries=3)
        assert result == "success"
        assert call_count == 3

class TestPhase2Configuration:
    """Test Phase 2.2: Configuration Consolidation."""
    
    def test_unified_config_creation(self):
        """Test unified configuration creation."""
        config = GartanConfig()
        
        # Test default values
        assert config.database.path == "gartan_availability.db"
        assert config.cache.default_expiry_minutes == 15
        assert config.scraping.max_days_default == 7
        assert config.logging.level == LogLevel.INFO
    
    def test_environment_overrides(self):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            'GARTAN_DB_PATH': '/custom/path.db',
            'GARTAN_CACHE_DIR': '/custom/cache',
            'GARTAN_MAX_DAYS': '14',
            'GARTAN_LOG_LEVEL': 'DEBUG'
        }):
            config = GartanConfig()
            
            assert config.database.path == '/custom/path.db'
            assert config.cache.directory == '/custom/cache'
            assert config.scraping.max_days_default == 14
            assert config.logging.level == LogLevel.DEBUG
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test invalid values during construction
        with pytest.raises(ValueError):
            DatabaseConfig(connection_pool_size=0)
        
        with pytest.raises(ValueError):
            CacheConfig(default_expiry_minutes=0)
    
    def test_config_serialization(self):
        """Test configuration serialization."""
        config = GartanConfig()
        
        # Test to_dict
        config_dict = config.to_dict()
        assert 'database' in config_dict
        assert 'cache' in config_dict
        assert config_dict['database']['path'] == "gartan_availability.db"
        
        # Test from_dict
        restored_config = GartanConfig.from_dict(config_dict)
        assert restored_config.database.path == config.database.path
        assert restored_config.cache.default_expiry_minutes == config.cache.default_expiry_minutes
    
    def test_config_migration(self):
        """Test configuration migration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            migrator = ConfigMigrator(backup_dir=temp_dir)
            
            # Test legacy settings extraction
            legacy_settings = {
                'cache_directory': '/old/cache',
                'scraping_max_days': 10
            }
            
            config = migrator.create_unified_config(legacy_settings)
            assert config.cache.directory == '/old/cache'
            assert config.scraping.max_days_default == 10

class TestPhase2Logging:
    """Test Phase 2.3: Logging Improvements."""
    
    def test_log_manager_creation(self):
        """Test log manager creation and setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = GartanConfig()
            config.logging.file_path = str(Path(temp_dir) / "test.log")
            
            log_manager = LogManager(config)
            logger = log_manager.get_logger("test")
            
            assert logger.name == "test"
    
    def test_structured_logging(self):
        """Test structured logging with context."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = GartanConfig()
            config.logging.file_path = str(Path(temp_dir) / "test.log")
            
            log_manager = LogManager(config)
            
            with log_manager.context(operation="test_op", user_id="test_user"):
                log_manager.log_with_context(
                    level=20,  # INFO
                    message="Test message",
                    extra_context={"test_key": "test_value"}
                )
            
            # Check log file exists
            log_file = Path(temp_dir) / "test.log"
            assert log_file.exists()
    
    def test_performance_tracking(self):
        """Test performance tracking functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = GartanConfig()
            config.logging.file_path = str(Path(temp_dir) / "test.log")
            
            log_manager = LogManager(config)
            
            with log_manager.track_performance("test_operation") as operation_id:
                # Simulate some work
                import time
                time.sleep(0.01)
            
            # Check that metrics were recorded
            recent_metrics = log_manager.performance_tracker.get_recent_metrics(1)
            assert len(recent_metrics) == 1
            assert recent_metrics[0].operation == "test_operation"
            assert recent_metrics[0].duration > 0

class TestPhase2API:
    """Test Phase 2.4: API Layer Refinement."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        
        # Create test database
        conn = sqlite3.connect(self.db_path)
        
        # Create tables
        conn.execute("""
            CREATE TABLE crew_entities (
                entity_id TEXT PRIMARY KEY,
                entity_name TEXT NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE TABLE appliance_entities (
                entity_id TEXT PRIMARY KEY,
                entity_name TEXT NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE TABLE crew_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES crew_entities (entity_id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE appliance_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES appliance_entities (entity_id)
            )
        """)
        
        # Insert test data
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        
        conn.execute("INSERT INTO crew_entities VALUES ('crew1', 'Test Crew 1')")
        conn.execute("INSERT INTO appliance_entities VALUES ('app1', 'Test Appliance 1')")
        
        conn.execute("""
            INSERT INTO crew_availability (entity_id, start_time, end_time, created_at)
            VALUES ('crew1', ?, ?, ?)
        """, (now.isoformat(), tomorrow.isoformat(), now.isoformat()))
        
        conn.commit()
        conn.close()
        
        # Configure API core to use test database
        self.config = GartanConfig()
        self.config.database.path = str(self.db_path)
        self.api_core = APICore(self.config)
    
    def teardown_method(self):
        """Clean up test database."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_api_response_structure(self):
        """Test standardized API response structure."""
        response = APIResponse(success=True, data={"test": "value"})
        
        assert response.success is True
        assert response.data == {"test": "value"}
        assert response.timestamp is not None
        
        response_dict = response.to_dict()
        assert 'success' in response_dict
        assert 'data' in response_dict
        assert 'timestamp' in response_dict
    
    def test_entity_list_api(self):
        """Test entity list API endpoint."""
        # Test crew list
        response = self.api_core.get_entity_list("crew")
        assert response.success is True
        assert isinstance(response.data, list)
        assert len(response.data) == 1
        assert response.data[0]['id'] == 'crew1'
        assert response.data[0]['name'] == 'Test Crew 1'
        
        # Test invalid entity type
        response = self.api_core.get_entity_list("invalid")
        assert response.success is False
        assert "Invalid entity type" in response.error
    
    def test_availability_check_api(self):
        """Test availability check API endpoint."""
        # Test valid check
        response = self.api_core.check_availability("crew", "crew1")
        assert response.success is True
        assert response.data is True  # Should be available
        
        # Test non-existent entity
        response = self.api_core.check_availability("crew", "nonexistent")
        assert response.success is False
        assert "Entity not found" in response.error
    
    def test_duration_calculation_api(self):
        """Test availability duration calculation."""
        response = self.api_core.get_availability_duration("crew", "crew1")
        assert response.success is True
        assert isinstance(response.data, str)
        
        # Should be close to 24 hours
        duration = float(response.data)
        assert 23.0 <= duration <= 25.0
    
    def test_system_status_api(self):
        """Test system status API endpoint."""
        response = self.api_core.get_system_status()
        assert response.success is True
        assert 'database_status' in response.data
        assert response.data['database_status'] == 'healthy'
        assert response.data['crew_entities'] == 1
        assert response.data['appliance_entities'] == 1

class TestPhase2Integration:
    """Test complete Phase 2 integration."""
    
    def test_error_handling_with_api(self):
        """Test error handling integration with API."""
        # Create API with invalid database path
        config = GartanConfig()
        config.database.path = "/nonexistent/path.db"
        
        api_core = APICore(config)
        
        # Should handle database errors gracefully
        response = api_core.get_entity_list("crew")
        assert response.success is False
        assert "Database not found" in response.error
    
    def test_logging_with_api_performance(self):
        """Test logging integration with API performance tracking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up test database
            db_path = Path(temp_dir) / "test.db"
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE crew_entities (entity_id TEXT, entity_name TEXT)")
            conn.execute("INSERT INTO crew_entities VALUES ('test1', 'Test')")
            conn.commit()
            conn.close()
            
            # Configure API with logging
            config = GartanConfig()
            config.database.path = str(db_path)
            config.logging.file_path = str(Path(temp_dir) / "api.log")
            
            # Create API with performance tracking
            api_core = APICore(config)
            
            # Make API call (should be logged with performance metrics)
            response = api_core.get_entity_list("crew")
            assert response.success is True
            assert response.execution_time_ms is not None
            assert response.execution_time_ms > 0
            
            # Check log file was created
            log_file = Path(temp_dir) / "api.log"
            assert log_file.exists()
    
    def test_configuration_with_all_components(self):
        """Test configuration integration across all components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create comprehensive configuration
            config = GartanConfig()
            config.database.path = str(Path(temp_dir) / "integrated.db")
            config.logging.file_path = str(Path(temp_dir) / "integrated.log")
            config.cache.directory = str(Path(temp_dir) / "cache")
            
            # Save and reload configuration
            config_file = Path(temp_dir) / "config.json"
            config.save_to_file(config_file)
            
            loaded_config = GartanConfig.load_from_file(config_file)
            assert loaded_config.database.path == config.database.path
            assert loaded_config.logging.file_path == config.logging.file_path
            assert loaded_config.cache.directory == config.cache.directory

def run_phase2_integration_tests():
    """Run all Phase 2 integration tests."""
    print("🧪 Running Phase 2 Integration Tests...")
    
    # Run tests using pytest
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short"
    ], capture_output=True, text=True)
    
    print(f"Exit code: {result.returncode}")
    print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")
    
    return result.returncode == 0

if __name__ == "__main__":
    run_phase2_integration_tests()
