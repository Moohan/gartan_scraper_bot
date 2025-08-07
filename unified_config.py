"""
Consolidated configuration management for Gartan Scraper Bot.

Provides centralized configuration with validation, environment overrides,
and type-safe access to all application settings.
"""

import os
import json
from typing import Dict, Any, Optional, Union, List, Type
from dataclasses import dataclass, field
from pathlib import Path
from datetime import timedelta
from enum import Enum
import logging
from error_handling import ConfigurationError, ErrorInfo, ErrorCategory, ErrorSeverity

class CacheMode(Enum):
    """Available cache modes."""
    NO_CACHE = "no-cache"
    CACHE_PREFERRED = "cache-preferred"  
    CACHE_FIRST = "cache-first"
    CACHE_ONLY = "cache-only"

class LogLevel(Enum):
    """Available logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    path: str = "gartan_availability.db"
    connection_pool_size: int = 5
    timeout_seconds: int = 30
    wal_mode: bool = True
    cache_size_mb: int = 10
    
    def __post_init__(self):
        if self.connection_pool_size < 1:
            raise ValueError("connection_pool_size must be >= 1")
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be >= 1")
        if self.cache_size_mb < 1:
            raise ValueError("cache_size_mb must be >= 1")

@dataclass  
class CacheConfig:
    """Cache configuration settings."""
    directory: str = "_cache"
    default_expiry_minutes: int = 15
    today_expiry_minutes: int = 15
    tomorrow_expiry_minutes: int = 60
    future_expiry_minutes: int = 360
    max_age_days: int = 30
    default_mode: CacheMode = CacheMode.CACHE_PREFERRED
    cleanup_on_startup: bool = True
    
    def __post_init__(self):
        if self.default_expiry_minutes < 1:
            raise ValueError("default_expiry_minutes must be >= 1")
        if self.max_age_days < 1:
            raise ValueError("max_age_days must be >= 1")

@dataclass
class NetworkConfig:
    """Network configuration settings."""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    session_timeout_seconds: int = 3600
    connection_pool_size: int = 10
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    
    def __post_init__(self):
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be >= 1")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds must be >= 0")

@dataclass
class ScrapingConfig:
    """Scraping configuration settings."""
    max_days_default: int = 7
    max_concurrent_fetches: int = 3
    min_delay_seconds: float = 1.0
    max_delay_seconds: float = 10.0
    delay_base: float = 1.5
    batch_size: int = 5
    memory_limit_mb: int = 400
    
    def __post_init__(self):
        if self.max_days_default < 1:
            raise ValueError("max_days_default must be >= 1")
        if self.max_concurrent_fetches < 1:
            raise ValueError("max_concurrent_fetches must be >= 1")
        if self.min_delay_seconds < 0:
            raise ValueError("min_delay_seconds must be >= 0")
        if self.max_delay_seconds < self.min_delay_seconds:
            raise ValueError("max_delay_seconds must be >= min_delay_seconds")

@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: LogLevel = LogLevel.INFO
    file_path: str = "gartan_debug.log"
    max_file_size_mb: int = 10
    backup_count: int = 5
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    console_level: LogLevel = LogLevel.INFO
    file_level: LogLevel = LogLevel.DEBUG
    
    def __post_init__(self):
        if self.max_file_size_mb < 1:
            raise ValueError("max_file_size_mb must be >= 1")
        if self.backup_count < 0:
            raise ValueError("backup_count must be >= 0")

@dataclass
class AuthenticationConfig:
    """Authentication configuration settings."""
    username: Optional[str] = None
    password: Optional[str] = None
    login_url: str = "https://grampianrds.firescotland.gov.uk/GartanAvailability/Account/Login.aspx"
    data_url: str = "https://grampianrds.firescotland.gov.uk/GartanAvailability/Availability/Schedule/AvailabilityMain1.aspx?UseDefaultStation=1"
    schedule_url: str = "https://grampianrds.firescotland.gov.uk/GartanAvailability/Availability/Schedule/AvailabilityMain1.aspx/GetSchedule"
    
    def __post_init__(self):
        # Load from environment if not provided
        if not self.username:
            self.username = os.getenv("GARTAN_USERNAME")
        if not self.password:
            self.password = os.getenv("GARTAN_PASSWORD")
    
    def validate(self):
        """Validate authentication configuration."""
        if not self.username or not self.password:
            raise ConfigurationError(
                ErrorInfo(
                    category=ErrorCategory.CONFIGURATION,
                    severity=ErrorSeverity.FATAL,
                    message="GARTAN_USERNAME and GARTAN_PASSWORD must be set in environment variables or .env file",
                    details={"username_set": bool(self.username), "password_set": bool(self.password)}
                )
            )

@dataclass
class APIConfig:
    """API server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    threaded: bool = True
    health_check_enabled: bool = True
    cors_enabled: bool = True
    rate_limiting_enabled: bool = False
    max_requests_per_minute: int = 60
    
    def __post_init__(self):
        if not (1 <= self.port <= 65535):
            raise ValueError("port must be between 1 and 65535")
        if self.max_requests_per_minute < 1:
            raise ValueError("max_requests_per_minute must be >= 1")

@dataclass
class SchedulerConfig:
    """Scheduler configuration settings."""
    enabled: bool = True
    scrape_interval_minutes: int = 5
    daily_scrape_hour: int = 6
    daily_scrape_days: int = 14
    update_scrape_days: int = 3
    initial_check_enabled: bool = True
    
    def __post_init__(self):
        if self.scrape_interval_minutes < 1:
            raise ValueError("scrape_interval_minutes must be >= 1")
        if not (0 <= self.daily_scrape_hour <= 23):
            raise ValueError("daily_scrape_hour must be between 0 and 23")
        if self.daily_scrape_days < 1:
            raise ValueError("daily_scrape_days must be >= 1")
        if self.update_scrape_days < 1:
            raise ValueError("update_scrape_days must be >= 1")

@dataclass
class GartanConfig:
    """Consolidated configuration for Gartan Scraper Bot."""
    
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    authentication: AuthenticationConfig = field(default_factory=AuthenticationConfig)
    api: APIConfig = field(default_factory=APIConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    
    # Global settings
    environment: str = "production"
    debug_mode: bool = False
    profile_performance: bool = False
    validate_auth_on_init: bool = True
    
    def __post_init__(self):
        # Load environment overrides
        self._load_environment_overrides()
        
        # Validate critical configurations (skip in testing environments)
        if self.validate_auth_on_init and self.environment != "testing":
            try:
                self.authentication.validate()
            except ConfigurationError:
                # Only validate auth if we're not in a testing context
                if not os.getenv("GARTAN_SKIP_AUTH_VALIDATION"):
                    raise
    
    def _load_environment_overrides(self):
        """Load configuration overrides from environment variables."""
        # Database overrides
        if db_path := os.getenv("GARTAN_DB_PATH"):
            self.database.path = db_path
        if pool_size := os.getenv("GARTAN_DB_POOL_SIZE"):
            self.database.connection_pool_size = int(pool_size)
        
        # Cache overrides  
        if cache_dir := os.getenv("GARTAN_CACHE_DIR"):
            self.cache.directory = cache_dir
        if cache_expiry := os.getenv("GARTAN_CACHE_EXPIRY"):
            self.cache.default_expiry_minutes = int(cache_expiry)
        
        # Network overrides
        if timeout := os.getenv("GARTAN_NETWORK_TIMEOUT"):
            self.network.timeout_seconds = int(timeout)
        if retries := os.getenv("GARTAN_MAX_RETRIES"):
            self.network.max_retries = int(retries)
        
        # Scraping overrides
        if max_days := os.getenv("GARTAN_MAX_DAYS"):
            self.scraping.max_days_default = int(max_days)
        if workers := os.getenv("GARTAN_MAX_WORKERS"):
            self.scraping.max_concurrent_fetches = int(workers)
        
        # Logging overrides
        if log_level := os.getenv("GARTAN_LOG_LEVEL"):
            try:
                self.logging.level = LogLevel(log_level.upper())
            except ValueError:
                pass  # Keep default if invalid
        if log_file := os.getenv("GARTAN_LOG_FILE"):
            self.logging.file_path = log_file
        
        # API overrides
        if api_host := os.getenv("GARTAN_API_HOST"):
            self.api.host = api_host
        if api_port := os.getenv("GARTAN_API_PORT"):
            self.api.port = int(api_port)
        if api_debug := os.getenv("GARTAN_API_DEBUG"):
            self.api.debug = api_debug.lower() in ("true", "1", "yes")
        
        # Scheduler overrides
        if sched_interval := os.getenv("GARTAN_SCRAPE_INTERVAL"):
            self.scheduler.scrape_interval_minutes = int(sched_interval)
        if daily_hour := os.getenv("GARTAN_DAILY_SCRAPE_HOUR"):
            self.scheduler.daily_scrape_hour = int(daily_hour)
        
        # Global overrides
        if env := os.getenv("GARTAN_ENVIRONMENT"):
            self.environment = env
        if debug := os.getenv("GARTAN_DEBUG"):
            self.debug_mode = debug.lower() in ("true", "1", "yes")
        if profile := os.getenv("GARTAN_PROFILE"):
            self.profile_performance = profile.lower() in ("true", "1", "yes")
    
    def get_cache_minutes(self, day_offset: int) -> int:
        """Get cache expiry minutes based on day offset (legacy compatibility)."""
        if day_offset == 0:
            return self.cache.today_expiry_minutes
        elif day_offset == 1:
            return self.cache.tomorrow_expiry_minutes
        else:
            return self.cache.future_expiry_minutes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        result = {}
        for field_name, field_value in self.__dict__.items():
            if hasattr(field_value, '__dict__'):
                # Handle dataclass sub-configurations
                result[field_name] = {}
                for sub_field_name, sub_field_value in field_value.__dict__.items():
                    if isinstance(sub_field_value, Enum):
                        result[field_name][sub_field_name] = sub_field_value.value
                    else:
                        result[field_name][sub_field_name] = sub_field_value
            else:
                result[field_name] = field_value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GartanConfig':
        """Create configuration from dictionary."""
        # Extract sub-configuration data
        db_data = data.get('database', {})
        cache_data = data.get('cache', {})
        network_data = data.get('network', {})
        scraping_data = data.get('scraping', {})
        logging_data = data.get('logging', {})
        auth_data = data.get('authentication', {})
        api_data = data.get('api', {})
        scheduler_data = data.get('scheduler', {})
        
        # Handle enum conversions
        if 'default_mode' in cache_data:
            cache_data['default_mode'] = CacheMode(cache_data['default_mode'])
        if 'level' in logging_data:
            logging_data['level'] = LogLevel(logging_data['level'])
        if 'console_level' in logging_data:
            logging_data['console_level'] = LogLevel(logging_data['console_level'])
        if 'file_level' in logging_data:
            logging_data['file_level'] = LogLevel(logging_data['file_level'])
        
        # Create sub-configurations
        return cls(
            database=DatabaseConfig(**db_data),
            cache=CacheConfig(**cache_data),
            network=NetworkConfig(**network_data),
            scraping=ScrapingConfig(**scraping_data),
            logging=LoggingConfig(**logging_data),
            authentication=AuthenticationConfig(**auth_data),
            api=APIConfig(**api_data),
            scheduler=SchedulerConfig(**scheduler_data),
            environment=data.get('environment', 'production'),
            debug_mode=data.get('debug_mode', False),
            profile_performance=data.get('profile_performance', False)
        )
    
    def save_to_file(self, file_path: Union[str, Path]):
        """Save configuration to JSON file."""
        file_path = Path(file_path)
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod  
    def load_from_file(cls, file_path: Union[str, Path]) -> 'GartanConfig':
        """Load configuration from JSON file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return cls.from_dict(data)

# Global configuration instance
_global_config: Optional[GartanConfig] = None

def get_config() -> GartanConfig:
    """Get the global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = GartanConfig()
    return _global_config

def set_config(config: GartanConfig):
    """Set the global configuration instance."""
    global _global_config
    _global_config = config

def load_config_from_file(file_path: Union[str, Path]) -> GartanConfig:
    """Load and set global configuration from file."""
    config = GartanConfig.load_from_file(file_path)
    set_config(config)
    return config

def reset_config():
    """Reset configuration to default values."""
    global _global_config
    _global_config = GartanConfig()

# Legacy compatibility - maintain backward compatibility with existing config.py
@dataclass
class LegacyConfig:
    """Legacy configuration class for backward compatibility."""
    
    def __init__(self):
        self._modern_config = get_config()
    
    @property
    def cache_dir(self) -> str:
        return self._modern_config.cache.directory
    
    @property 
    def cache_expiry_minutes(self) -> int:
        return self._modern_config.cache.default_expiry_minutes
    
    def get_cache_minutes(self, day_offset: int) -> int:
        return self._modern_config.get_cache_minutes(day_offset)

# Legacy global instance
config = LegacyConfig()
