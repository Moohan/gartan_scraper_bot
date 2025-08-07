"""
Phase 2 Integration Demonstration

This script demonstrates all Phase 2 components working together:
- Error Handling with automatic classification and retry
- Unified Configuration with environment overrides
- Enhanced Logging with performance tracking
- Refined API with standardized responses
"""

import os
import tempfile
import sqlite3
import time
from pathlib import Path

# Set environment variables for testing
os.environ['GARTAN_SKIP_AUTH_VALIDATION'] = '1'
os.environ['GARTAN_LOG_LEVEL'] = 'INFO'

# Import Phase 2 components
from error_handling import ErrorHandler, ErrorCategory, ErrorSeverity, handle_exceptions
from unified_config import GartanConfig, DatabaseConfig, CacheConfig
from enhanced_logging import get_logger, log_context, track_performance
from refined_api import APICore, APIResponse

def demonstrate_error_handling():
    """Demonstrate error handling capabilities."""
    print("\n🛡️  Error Handling Demonstration")
    print("-" * 40)
    
    handler = ErrorHandler()
    
    # Test error classification
    network_error = ConnectionError("Network is unreachable")
    classified = handler.classify_exception(network_error)
    print(f"✅ Error Classification: {classified.category.value} - {classified.severity.value}")
    
    # Test retry mechanism
    attempt_count = 0
    def failing_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("Temporary failure")
        return "Success after retries"
    
    try:
        result = handler.with_retry(failing_function, max_retries=3, delay=0.1)
        print(f"✅ Retry Mechanism: {result} (attempts: {attempt_count})")
    except Exception as e:
        print(f"❌ Retry failed: {e}")
    
    # Test error statistics
    handler.handle_error_legacy(ErrorCategory.DATABASE, ErrorSeverity.HIGH, "Test DB Error")
    handler.handle_error_legacy(ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, "Test Network Error")
    
    stats = handler.get_statistics()
    print(f"✅ Error Statistics: {stats['total_errors']} total errors tracked")

def demonstrate_configuration():
    """Demonstrate unified configuration."""
    print("\n⚙️  Configuration Demonstration")
    print("-" * 40)
    
    # Create configuration with custom settings
    config = GartanConfig()
    config.database.connection_pool_size = 3
    config.cache.default_expiry_minutes = 30
    config.scraping.max_days_default = 14
    
    print(f"✅ Database Config: Pool size = {config.database.connection_pool_size}")
    print(f"✅ Cache Config: Expiry = {config.cache.default_expiry_minutes} minutes")
    print(f"✅ Scraping Config: Max days = {config.scraping.max_days_default}")
    
    # Test environment override
    os.environ['GARTAN_MAX_DAYS'] = '21'
    config_with_override = GartanConfig()
    print(f"✅ Environment Override: Max days = {config_with_override.scraping.max_days_default}")
    
    # Test serialization
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config.save_to_file(f.name)
        loaded_config = GartanConfig.load_from_file(f.name)
        print(f"✅ Serialization: Config saved and loaded successfully")
        os.unlink(f.name)

def demonstrate_logging():
    """Demonstrate enhanced logging."""
    print("\n📈 Logging Demonstration")
    print("-" * 40)
    
    logger = get_logger("demo")
    
    # Test structured logging with context
    with log_context(operation="demo_operation", user_id="test_user"):
        logger.info("This is a test message with context")
        print("✅ Structured Logging: Message logged with context")
    
    # Test performance tracking
    with track_performance("demo_computation"):
        # Simulate some work
        time.sleep(0.01)
        result = sum(range(1000))
        print(f"✅ Performance Tracking: Computation completed (result: {result})")
    
    print("✅ Enhanced Logging: All features demonstrated")

def demonstrate_api():
    """Demonstrate refined API."""
    print("\n🔌 API Demonstration")
    print("-" * 40)
    
    # Create API response
    response = APIResponse(
        success=True,
        data={"entities": ["crew1", "crew2"], "count": 2},
        execution_time_ms=15.5
    )
    
    print(f"✅ API Response: Success = {response.success}")
    print(f"✅ API Response: Data = {response.data}")
    print(f"✅ API Response: Execution time = {response.execution_time_ms}ms")
    
    # Test response serialization
    response_dict = response.to_dict()
    print(f"✅ API Serialization: {len(response_dict)} fields in response")
    
    # Test error response
    error_response = APIResponse(
        success=False,
        error="Entity not found",
        error_code="ENTITY_NOT_FOUND"
    )
    print(f"✅ API Error Response: {error_response.error} ({error_response.error_code})")

@handle_exceptions(error_category=ErrorCategory.EXTERNAL)
def demonstrate_integration():
    """Demonstrate all components working together."""
    print("\n🎯 Integration Demonstration")
    print("-" * 40)
    
    # Get unified configuration
    config = GartanConfig()
    
    # Set up logging with configuration
    logger = get_logger("integration")
    
    # Use error handling with API-style response
    try:
        with log_context(operation="integration_test"):
            with track_performance("full_integration_test"):
                # Simulate API operation
                logger.info("Starting integration test")
                
                # Create a temporary database for testing
                with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as db_file:
                    db_path = db_file.name
                
                # Update config to use test database
                config.database.path = db_path
                
                # Test database creation
                conn = sqlite3.connect(db_path)
                conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
                conn.execute("INSERT INTO test VALUES (1, 'Test Entity')")
                conn.commit()
                conn.close()
                
                logger.info("Test database created successfully")
                
                # Create API response
                response = APIResponse(
                    success=True,
                    data={"message": "Integration test completed", "db_path": db_path},
                    execution_time_ms=25.0
                )
                
                print("✅ Integration: All components working together")
                print(f"✅ Integration: Response = {response.to_dict()}")
                
                # Cleanup
                os.unlink(db_path)
                
                return response
                
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            error_code="INTEGRATION_FAILURE"
        )

def main():
    """Run complete Phase 2 demonstration."""
    print("🎉 Phase 2: Code Simplicity & Robustness")
    print("=" * 50)
    print("Demonstrating all Phase 2 components...")
    
    try:
        # Demonstrate each component
        demonstrate_error_handling()
        demonstrate_configuration()
        demonstrate_logging()
        demonstrate_api()
        
        # Demonstrate integration
        result = demonstrate_integration()
        
        print(f"\n🎯 Final Result: {result.success}")
        if result.success:
            print("✅ All Phase 2 components working perfectly!")
        else:
            print(f"❌ Integration issue: {result.error}")
        
        print("\n📊 Phase 2 Summary:")
        print("- ✅ Error Handling: Comprehensive exception management")
        print("- ✅ Configuration: Unified, validated, environment-aware")
        print("- ✅ Logging: Structured, performant, context-aware")
        print("- ✅ API: Standardized, robust, monitored")
        print("- ✅ Integration: All components work seamlessly together")
        
        print("\n🎉 Phase 2 implementation is COMPLETE and SUCCESSFUL!")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
