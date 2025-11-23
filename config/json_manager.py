"""
Unified JSON Configuration Manager for PIPELINE_SQLSERVER

Provides centralized JSON file management with standardized:
- Loading and saving
- Validation and error handling
- Backup and recovery
- Thread-safe operations
"""

import json
import os
import shutil
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from constants import PathConstants


@dataclass
class JSONFileConfig:
    """Configuration for a JSON file."""
    filename: str
    default_content: Dict[str, Any] = field(default_factory=dict)
    required_keys: List[str] = field(default_factory=list)
    backup_enabled: bool = True
    validation_func: Optional[callable] = None


class JSONManager:
    """
    Centralized JSON configuration manager.
    
    Handles all JSON configuration files with:
    - Standardized loading/saving
    - Validation and error handling
    - Backup and recovery
    - Thread safety
    """
    
    def __init__(self):
        """Initialize JSON Manager."""
        self._lock = threading.RLock()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._file_timestamps: Dict[str, float] = {}  # Track file modification times
        self._file_configs = self._initialize_file_configs()
        
        # Ensure config directory exists
        os.makedirs(PathConstants.CONFIG_DIR, exist_ok=True)
        
        # Initialize all files
        self._initialize_files()
    
    def _initialize_file_configs(self) -> Dict[str, JSONFileConfig]:
        """Initialize configuration for all JSON files."""
        return {
            'app_settings': JSONFileConfig(
                filename='app_settings.json',
                default_content={
                    "window_size": [900, 780],
                    "theme": "system",
                    "backup_enabled": True,
                    "log_level": "INFO",
                    "folders": {
                        "input_folder": "",
                        "output_folder": "",
                        "log_folder": ""
                    },
                    "file_management": {
                        "auto_move_enabled": True,
                        "organize_by_date": False
                    }
                },
                required_keys=[],
                validation_func=self._validate_app_settings
            )
        }
    
    def _initialize_files(self) -> None:
        """Initialize all JSON files with default content if they don't exist."""
        for config_name, config in self._file_configs.items():
            file_path = self._get_file_path(config.filename)
            if not os.path.exists(file_path):
                self._save_file(config.filename, config.default_content)
    
    def _get_file_path(self, filename: str) -> str:
        """Get full path for a JSON file."""
        return os.path.join(PathConstants.CONFIG_DIR, filename)
    
    def _create_backup(self, filename: str) -> Optional[str]:
        """Create backup of JSON file in dedicated backup folder."""
        try:
            source_path = self._get_file_path(filename)
            if not os.path.exists(source_path):
                return None
            
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(PathConstants.CONFIG_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{filename}.backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            shutil.copy2(source_path, backup_path)
            return backup_path
        except (FileNotFoundError, PermissionError, shutil.Error):
            return None
    
    def _load_file(self, filename: str) -> Dict[str, Any]:
        """Load JSON file with error handling."""
        file_path = self._get_file_path(filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            # Validate content if validator exists
            config = self._file_configs.get(self._get_config_name(filename))
            if config and config.validation_func:
                if not config.validation_func(content):
                    raise ValueError(f"Validation failed for {filename}")
            
            return content
            
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            # Return default content if file is corrupted or missing
            config = self._file_configs.get(self._get_config_name(filename))
            if config:
                return config.default_content.copy()
            return {}
    
    def _save_file(self, filename: str, content: Dict[str, Any]) -> bool:
        """Save JSON file with backup and validation."""
        try:
            config = self._file_configs.get(self._get_config_name(filename))
            
            # Validate content before saving
            if config and config.validation_func:
                if not config.validation_func(content):
                    raise ValueError(f"Validation failed for {filename}")
            
            # Create backup if enabled
            if config and config.backup_enabled:
                self._create_backup(filename)
            
            # Save file
            file_path = self._get_file_path(filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            
            return True
            
        except (FileNotFoundError, PermissionError, json.JSONDecodeError, TypeError):
            return False
    
    def _get_config_name(self, filename: str) -> str:
        """Get config name from filename."""
        return filename.replace('.json', '').replace('_', '_')
    
    # Validation functions

    def _validate_app_settings(self, content: Dict[str, Any]) -> bool:
        """Validate application settings."""
        if not isinstance(content, dict):
            return False

        # Validate window_size
        if 'window_size' in content:
            window_size = content['window_size']
            if not (isinstance(window_size, list) and len(window_size) == 2):
                return False

        # Validate folders section
        if 'folders' in content:
            if not isinstance(content['folders'], dict):
                return False

        # Validate file_management section
        if 'file_management' in content:
            if not isinstance(content['file_management'], dict):
                return False

        return True
    
    # Public interface
    def load(self, config_name: str) -> Dict[str, Any]:
        """
        Load configuration by name with real-time file checking.
        
        Args:
            config_name: Name of configuration (e.g., 'app_settings', 'column_settings')
            
        Returns:
            Dict containing configuration data
        """
        with self._lock:
            config = self._file_configs.get(config_name)
            if not config:
                raise ValueError(f"Unknown configuration: {config_name}")
            
            file_path = self._get_file_path(config.filename)
            
            # Check if file exists and get modification time
            try:
                current_mtime = os.path.getmtime(file_path)
            except OSError:
                # File doesn't exist, return default content
                content = config.default_content.copy()
                self._cache[config_name] = content
                return content.copy()
            
            # Check if we need to reload from file
            cached_mtime = self._file_timestamps.get(config_name, 0)
            
            if config_name not in self._cache or current_mtime > cached_mtime:
                # File has been modified or not cached yet, reload
                content = self._load_file(config.filename)
                self._cache[config_name] = content
                self._file_timestamps[config_name] = current_mtime
                return content.copy()
            
            # Return cached content if file hasn't changed
            return self._cache[config_name].copy()
    
    def save(self, config_name: str, content: Dict[str, Any]) -> bool:
        """
        Save configuration by name.
        
        Args:
            config_name: Name of configuration
            content: Configuration data to save
            
        Returns:
            bool: Success status
        """
        with self._lock:
            config = self._file_configs.get(config_name)
            if not config:
                raise ValueError(f"Unknown configuration: {config_name}")
            
            success = self._save_file(config.filename, content)
            if success:
                self._cache[config_name] = content.copy()
                # Update timestamp after successful save
                file_path = self._get_file_path(config.filename)
                try:
                    self._file_timestamps[config_name] = os.path.getmtime(file_path)
                except OSError:
                    pass
            return success
    
    def get(self, config_name: str, key: str, default: Any = None) -> Any:
        """
        Get specific value from configuration.
        
        Args:
            config_name: Name of configuration
            key: Key to retrieve
            default: Default value if key not found
            
        Returns:
            Value from configuration or default
        """
        content = self.load(config_name)
        return content.get(key, default)
    
    def set(self, config_name: str, key: str, value: Any) -> bool:
        """
        Set specific value in configuration.
        
        Args:
            config_name: Name of configuration
            key: Key to set
            value: Value to set
            
        Returns:
            bool: Success status
        """
        content = self.load(config_name)
        content[key] = value
        return self.save(config_name, content)
    
    def update(self, config_name: str, updates: Dict[str, Any]) -> bool:
        """
        Update multiple values in configuration.
        
        Args:
            config_name: Name of configuration
            updates: Dictionary of key-value pairs to update
            
        Returns:
            bool: Success status
        """
        content = self.load(config_name)
        content.update(updates)
        return self.save(config_name, content)
    
    def reset(self, config_name: str) -> bool:
        """
        Reset configuration to default values.
        
        Args:
            config_name: Name of configuration
            
        Returns:
            bool: Success status
        """
        config = self._file_configs.get(config_name)
        if not config:
            raise ValueError(f"Unknown configuration: {config_name}")
        
        return self.save(config_name, config.default_content.copy())
    
    def list_configs(self) -> List[str]:
        """List all available configuration names."""
        return list(self._file_configs.keys())
    
    def clear_cache(self) -> None:
        """Clear configuration cache."""
        with self._lock:
            self._cache.clear()
    
    def backup_all(self) -> Dict[str, Optional[str]]:
        """
        Create backup of all configuration files.
        
        Returns:
            Dict mapping config names to backup file paths
        """
        backups = {}
        for config_name, config in self._file_configs.items():
            if config.backup_enabled:
                backup_path = self._create_backup(config.filename)
                backups[config_name] = backup_path
        return backups
    
    def cleanup_old_backups(self, keep_days: int = 7) -> int:
        """
        Clean up backup files older than specified days.

        Args:
            keep_days: Number of days to keep backup files

        Returns:
            int: Number of files deleted
        """
        try:
            backup_dir = os.path.join(PathConstants.CONFIG_DIR, "backups")
            if not os.path.exists(backup_dir):
                return 0

            deleted_count = 0
            cutoff_time = time.time() - (keep_days * 24 * 60 * 60)

            for filename in os.listdir(backup_dir):
                if filename.endswith('.backup_' + filename.split('.backup_')[-1]):
                    file_path = os.path.join(backup_dir, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1

            return deleted_count
        except (OSError, PermissionError):
            return 0

    # File Type Management

    def _get_file_type_path(self, file_type: str) -> str:
        """Get full path for a file type JSON file."""
        return os.path.join(PathConstants.FILE_TYPES_DIR, f"{file_type}.json")

    def load_file_type(self, file_type: str) -> Dict[str, Any]:
        """
        Load file type configuration.

        Args:
            file_type: Name of the file type

        Returns:
            Dict with 'columns' and 'dtypes' keys, empty dicts if not found
        """
        file_path = self._get_file_type_path(file_type)

        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)

                # Validate structure
                if isinstance(content, dict) and 'columns' in content and 'dtypes' in content:
                    return content
        except (json.JSONDecodeError, PermissionError):
            pass

        # Return empty structure if file doesn't exist or is invalid
        return {"columns": {}, "dtypes": {}}

    def save_file_type(self, file_type: str, columns: Dict[str, str], dtypes: Dict[str, str]) -> bool:
        """
        Save file type configuration.

        Args:
            file_type: Name of the file type
            columns: Column mappings
            dtypes: Data type mappings

        Returns:
            bool: Success status
        """
        try:
            # Ensure directory exists
            os.makedirs(PathConstants.FILE_TYPES_DIR, exist_ok=True)

            file_path = self._get_file_type_path(file_type)

            # Create backup if file exists
            if os.path.exists(file_path):
                backup_dir = os.path.join(PathConstants.FILE_TYPES_DIR, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(backup_dir, f"{file_type}.json.backup_{timestamp}")
                shutil.copy2(file_path, backup_path)

            # Save file
            content = {
                "columns": columns,
                "dtypes": dtypes
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)

            return True

        except (OSError, PermissionError, json.JSONEncodeError):
            return False

    def list_file_types(self) -> List[str]:
        """
        List all available file types.

        Returns:
            List of file type names
        """
        try:
            if not os.path.exists(PathConstants.FILE_TYPES_DIR):
                return []

            file_types = []
            for filename in os.listdir(PathConstants.FILE_TYPES_DIR):
                if filename.endswith('.json') and not filename.startswith('.'):
                    file_type = filename.replace('.json', '')
                    file_types.append(file_type)

            return sorted(file_types)
        except OSError:
            return []

    def delete_file_type(self, file_type: str) -> bool:
        """
        Delete a file type configuration.

        Args:
            file_type: Name of the file type

        Returns:
            bool: Success status
        """
        try:
            file_path = self._get_file_type_path(file_type)

            if os.path.exists(file_path):
                # Create backup before deleting
                backup_dir = os.path.join(PathConstants.FILE_TYPES_DIR, "backups")
                os.makedirs(backup_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(backup_dir, f"{file_type}.json.backup_{timestamp}")
                shutil.copy2(file_path, backup_path)

                # Delete file
                os.remove(file_path)
                return True

            return False
        except (OSError, PermissionError):
            return False


# Global JSON manager instance
json_manager = JSONManager()


# Convenience functions for backward compatibility

def load_app_settings() -> Dict[str, Any]:
    """Load application settings."""
    return json_manager.load('app_settings')

def save_app_settings(settings: Dict[str, Any]) -> bool:
    """Save application settings."""
    return json_manager.save('app_settings', settings)

# Folder configuration helpers

def get_input_folder() -> str:
    """Get input folder path from app_settings.json"""
    try:
        settings = json_manager.load('app_settings')
        return settings.get('folders', {}).get('input_folder', '')
    except Exception:
        return ''

def set_input_folder(path: str) -> bool:
    """Set input folder path in app_settings.json"""
    try:
        settings = json_manager.load('app_settings')
        if 'folders' not in settings:
            settings['folders'] = {}
        settings['folders']['input_folder'] = path
        return json_manager.save('app_settings', settings)
    except Exception:
        return False

def get_output_folder() -> str:
    """Get output folder path from app_settings.json"""
    try:
        settings = json_manager.load('app_settings')
        return settings.get('folders', {}).get('output_folder', '')
    except Exception:
        return ''

def set_output_folder(path: str) -> bool:
    """Set output folder path in app_settings.json"""
    try:
        settings = json_manager.load('app_settings')
        if 'folders' not in settings:
            settings['folders'] = {}
        settings['folders']['output_folder'] = path
        return json_manager.save('app_settings', settings)
    except Exception:
        return False

def get_log_folder() -> str:
    """Get log folder path from app_settings.json"""
    try:
        settings = json_manager.load('app_settings')
        return settings.get('folders', {}).get('log_folder', '')
    except Exception:
        return ''

def set_log_folder(path: str) -> bool:
    """Set log folder path in app_settings.json"""
    try:
        settings = json_manager.load('app_settings')
        if 'folders' not in settings:
            settings['folders'] = {}
        settings['folders']['log_folder'] = path
        return json_manager.save('app_settings', settings)
    except Exception:
        return False

# File management settings helpers

def load_file_management_settings() -> Dict[str, Any]:
    """Load file management settings from app_settings.json"""
    try:
        settings = json_manager.load('app_settings')
        return settings.get('file_management', {
            'auto_move_enabled': True,
            'organize_by_date': False
        })
    except Exception:
        return {'auto_move_enabled': True, 'organize_by_date': False}

def save_file_management_settings(settings: Dict[str, Any]) -> bool:
    """Save file management settings to app_settings.json"""
    try:
        app_settings = json_manager.load('app_settings')
        app_settings['file_management'] = settings
        return json_manager.save('app_settings', app_settings)
    except Exception:
        return False

# Legacy column/dtype settings (deprecated - use file types instead)
# Kept for backward compatibility during migration

def load_column_settings() -> Dict[str, Any]:
    """
    DEPRECATED: Load column settings from legacy file.
    Use json_manager.load_file_type() instead.
    """
    legacy_file = os.path.join(PathConstants.CONFIG_DIR, 'column_settings.json')
    try:
        if os.path.exists(legacy_file):
            with open(legacy_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_column_settings(settings: Dict[str, Any]) -> bool:
    """
    DEPRECATED: Save column settings to legacy file.
    Use json_manager.save_file_type() instead.
    """
    legacy_file = os.path.join(PathConstants.CONFIG_DIR, 'column_settings.json')
    try:
        with open(legacy_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

def load_dtype_settings() -> Dict[str, Any]:
    """
    DEPRECATED: Load dtype settings from legacy file.
    Use json_manager.load_file_type() instead.
    """
    legacy_file = os.path.join(PathConstants.CONFIG_DIR, 'dtype_settings.json')
    try:
        if os.path.exists(legacy_file):
            with open(legacy_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_dtype_settings(settings: Dict[str, Any]) -> bool:
    """
    DEPRECATED: Save dtype settings to legacy file.
    Use json_manager.save_file_type() instead.
    """
    legacy_file = os.path.join(PathConstants.CONFIG_DIR, 'dtype_settings.json')
    try:
        with open(legacy_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False