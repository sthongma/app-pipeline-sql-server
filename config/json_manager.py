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
                    "auto_move_files": True,
                    "backup_enabled": True,
                    "log_level": "INFO"
                },
                required_keys=[],
                validation_func=self._validate_app_settings
            ),
            'input_folder_config': JSONFileConfig(
                filename='input_folder_config.json',
                default_content={"folder_path": ""},
                required_keys=['folder_path'],
                validation_func=self._validate_folder_config
            ),
            'column_settings': JSONFileConfig(
                filename='column_settings.json',
                default_content={},
                validation_func=self._validate_column_settings
            ),
            'dtype_settings': JSONFileConfig(
                filename='dtype_settings.json',
                default_content={},
                validation_func=self._validate_dtype_settings
            ),
            'file_management_settings': JSONFileConfig(
                filename='file_management_settings.json',
                default_content={
                    "auto_move_enabled": True,
                    "target_folder": "Uploaded_Files",
                    "organize_by_date": True
                },
                validation_func=self._validate_file_management_settings
            ),
            'output_folder_config': JSONFileConfig(
                filename='output_folder_config.json',
                default_content={"folder_path": ""},
                required_keys=['folder_path'],
                validation_func=self._validate_folder_config
            ),
            'log_folder_config': JSONFileConfig(
                filename='log_folder_config.json',
                default_content={"log_folder_path": ""},
                required_keys=['log_folder_path'],
                validation_func=self._validate_log_folder_config
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
        if 'window_size' in content:
            window_size = content['window_size']
            if not (isinstance(window_size, list) and len(window_size) == 2):
                return False
        return True
    
    def _validate_column_settings(self, content: Dict[str, Any]) -> bool:
        """Validate column settings."""
        return isinstance(content, dict)
    
    def _validate_dtype_settings(self, content: Dict[str, Any]) -> bool:
        """Validate data type settings."""
        return isinstance(content, dict)
    
    def _validate_file_management_settings(self, content: Dict[str, Any]) -> bool:
        """Validate file management settings."""
        return isinstance(content, dict)

    def _validate_folder_config(self, content: Dict[str, Any]) -> bool:
        """Validate folder configuration."""
        if not isinstance(content, dict):
            return False
        if 'folder_path' not in content:
            return False
        return isinstance(content['folder_path'], str)

    def _validate_log_folder_config(self, content: Dict[str, Any]) -> bool:
        """Validate log folder configuration."""
        if not isinstance(content, dict):
            return False
        if 'log_folder_path' not in content:
            return False
        return isinstance(content['log_folder_path'], str)
    
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


# Global JSON manager instance
json_manager = JSONManager()


# Convenience functions for backward compatibility

def load_app_settings() -> Dict[str, Any]:
    """Load application settings."""
    return json_manager.load('app_settings')

def save_app_settings(settings: Dict[str, Any]) -> bool:
    """Save application settings."""
    return json_manager.save('app_settings', settings)

def load_column_settings() -> Dict[str, Any]:
    """Load column settings."""
    return json_manager.load('column_settings')

def save_column_settings(settings: Dict[str, Any]) -> bool:
    """Save column settings."""
    return json_manager.save('column_settings', settings)

def load_dtype_settings() -> Dict[str, Any]:
    """Load data type settings."""
    return json_manager.load('dtype_settings')

def save_dtype_settings(settings: Dict[str, Any]) -> bool:
    """Save data type settings."""
    return json_manager.save('dtype_settings', settings)

def load_file_management_settings() -> Dict[str, Any]:
    """Load file management settings."""
    return json_manager.load('file_management_settings')

def save_file_management_settings(settings: Dict[str, Any]) -> bool:
    """Save file management settings."""
    return json_manager.save('file_management_settings', settings)

def get_input_folder() -> str:
    """Get input folder path from input_folder_config.json"""
    return json_manager.get('input_folder_config', 'folder_path', '')

def set_input_folder(path: str) -> bool:
    """Set input folder path to input_folder_config.json"""
    return json_manager.set('input_folder_config', 'folder_path', path)

def get_output_folder() -> str:
    """Get output folder path from output_folder_config.json"""
    return json_manager.get('output_folder_config', 'folder_path', '')

def set_output_folder(path: str) -> bool:
    """Set output folder path to output_folder_config.json"""
    return json_manager.set('output_folder_config', 'folder_path', path)

def get_log_folder() -> str:
    """Get log folder path from log_folder_config.json"""
    return json_manager.get('log_folder_config', 'log_folder_path', '')

def set_log_folder(path: str) -> bool:
    """Set log folder path to log_folder_config.json"""
    return json_manager.set('log_folder_config', 'log_folder_path', path)