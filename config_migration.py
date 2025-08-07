"""
Migration utility for transitioning to unified configuration system.

Provides tools to migrate from the old config system to the new unified system,
ensuring backward compatibility and smooth transition.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime

from unified_config import GartanConfig, get_config, set_config
from error_handling import ConfigurationError, ErrorInfo, ErrorCategory, ErrorSeverity

class ConfigMigrator:
    """Handles migration from old configuration system to unified config."""
    
    def __init__(self, backup_dir: str = "_config_backup"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    def backup_existing_config(self) -> Dict[str, str]:
        """Backup existing configuration files."""
        backed_up_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Files to backup
        config_files = [
            "config.py",
            "cli.py", 
            "logging_config.py"
        ]
        
        for config_file in config_files:
            source_path = Path(config_file)
            if source_path.exists():
                backup_name = f"{config_file}.backup_{timestamp}"
                backup_path = self.backup_dir / backup_name
                shutil.copy2(source_path, backup_path)
                backed_up_files[config_file] = str(backup_path)
        
        return backed_up_files
    
    def extract_legacy_settings(self) -> Dict[str, Any]:
        """Extract settings from legacy configuration files."""
        settings = {}
        
        # Try to import and extract settings from existing config
        try:
            # Import existing config if available
            import config as legacy_config
            
            # Extract cache settings
            if hasattr(legacy_config, 'cache_dir'):
                settings['cache_directory'] = legacy_config.cache_dir
            if hasattr(legacy_config, 'cache_expiry_minutes'):
                settings['cache_default_expiry'] = legacy_config.cache_expiry_minutes
            
            # Extract other settings if available
            if hasattr(legacy_config, 'max_days_default'):
                settings['scraping_max_days'] = legacy_config.max_days_default
            if hasattr(legacy_config, 'max_concurrent_fetches'):
                settings['scraping_max_concurrent'] = legacy_config.max_concurrent_fetches
                
        except ImportError:
            # No legacy config found, use defaults
            pass
        
        # Check for environment variables that might override
        env_overrides = {
            'GARTAN_CACHE_DIR': 'cache_directory',
            'GARTAN_MAX_DAYS': 'scraping_max_days',
            'GARTAN_MAX_WORKERS': 'scraping_max_concurrent',
            'GARTAN_DB_PATH': 'database_path'
        }
        
        for env_var, setting_key in env_overrides.items():
            if value := os.getenv(env_var):
                settings[setting_key] = value
        
        return settings
    
    def create_unified_config(self, legacy_settings: Optional[Dict[str, Any]] = None) -> GartanConfig:
        """Create unified configuration with legacy settings applied."""
        if legacy_settings is None:
            legacy_settings = self.extract_legacy_settings()
        
        # Start with default configuration
        config = GartanConfig()
        
        # Apply legacy settings
        if 'cache_directory' in legacy_settings:
            config.cache.directory = legacy_settings['cache_directory']
        if 'cache_default_expiry' in legacy_settings:
            config.cache.default_expiry_minutes = int(legacy_settings['cache_default_expiry'])
        if 'scraping_max_days' in legacy_settings:
            config.scraping.max_days_default = int(legacy_settings['scraping_max_days'])
        if 'scraping_max_concurrent' in legacy_settings:
            config.scraping.max_concurrent_fetches = int(legacy_settings['scraping_max_concurrent'])
        if 'database_path' in legacy_settings:
            config.database.path = legacy_settings['database_path']
        
        return config
    
    def validate_migration(self, new_config: GartanConfig) -> bool:
        """Validate that migration preserved essential settings."""
        try:
            # Validate authentication is working
            new_config.authentication.validate()
            
            # Check that critical paths exist or can be created
            cache_path = Path(new_config.cache.directory)
            cache_path.mkdir(exist_ok=True)
            
            db_path = Path(new_config.database.path)
            db_path.parent.mkdir(exist_ok=True)
            
            return True
            
        except Exception as e:
            raise ConfigurationError(
                ErrorInfo(
                    category=ErrorCategory.CONFIGURATION,
                    severity=ErrorSeverity.HIGH,
                    message=f"Migration validation failed: {str(e)}",
                    details={"error_type": type(e).__name__}
                )
            )
    
    def migrate(self, save_config_file: bool = True) -> GartanConfig:
        """Perform complete migration to unified configuration."""
        print("🔄 Starting configuration migration...")
        
        # 1. Backup existing configuration
        backed_up = self.backup_existing_config()
        if backed_up:
            print(f"✅ Backed up {len(backed_up)} configuration files")
        
        # 2. Extract legacy settings
        legacy_settings = self.extract_legacy_settings()
        if legacy_settings:
            print(f"✅ Extracted {len(legacy_settings)} legacy settings")
        
        # 3. Create unified configuration
        new_config = self.create_unified_config(legacy_settings)
        print("✅ Created unified configuration")
        
        # 4. Validate migration
        if self.validate_migration(new_config):
            print("✅ Migration validation passed")
        
        # 5. Set as global configuration
        set_config(new_config)
        print("✅ Applied unified configuration globally")
        
        # 6. Optionally save to file
        if save_config_file:
            config_file = Path("gartan_config.json")
            new_config.save_to_file(config_file)
            print(f"✅ Saved configuration to {config_file}")
        
        print("🎉 Configuration migration completed successfully!")
        return new_config

def migrate_configuration(backup_existing: bool = True, save_config_file: bool = True) -> GartanConfig:
    """Convenience function to migrate configuration."""
    migrator = ConfigMigrator()
    return migrator.migrate(save_config_file)

def create_default_config_file(file_path: str = "gartan_config.json"):
    """Create a default configuration file for reference."""
    config = GartanConfig()
    config.save_to_file(file_path)
    print(f"✅ Created default configuration file: {file_path}")

if __name__ == "__main__":
    # Command-line migration tool
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Gartan Scraper Bot configuration")
    parser.add_argument("--backup", action="store_true", help="Backup existing configuration files")
    parser.add_argument("--save", action="store_true", help="Save unified configuration to file")
    parser.add_argument("--create-default", action="store_true", help="Create default configuration file")
    parser.add_argument("--config-file", default="gartan_config.json", help="Configuration file path")
    
    args = parser.parse_args()
    
    if args.create_default:
        create_default_config_file(args.config_file)
    else:
        migrate_configuration(backup_existing=args.backup, save_config_file=args.save)
