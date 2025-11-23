"""
Settings Manager Service

Centralizes settings loading, caching, and reloading logic with support for new file type structure
"""

import json
import os
import threading
from typing import Dict, Any, Optional, List
from constants import PathConstants
from config.json_manager import json_manager


class SettingsManager:
    """
    Centralized settings management with file watching and caching

    Responsibilities:
    - Load column and dtype settings from file type configs
    - Support both legacy (single file) and new (per-type files) structures
    - Cache settings with timestamp-based invalidation
    - Thread-safe settings access
    - Automatic reload when files change
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern to ensure only one SettingsManager exists"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize settings manager"""
        # Avoid re-initialization in singleton
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        self._settings_lock = threading.Lock()

        # Cache for file type configurations
        self._file_type_cache: Dict[str, Dict[str, Any]] = {}
        self._file_type_timestamps: Dict[str, float] = {}

    def reload_all(self, force: bool = False) -> None:
        """
        Reload all settings from disk

        Args:
            force: Force reload even if files haven't changed
        """
        with self._settings_lock:
            self._file_type_cache.clear()
            self._file_type_timestamps.clear()

    def _get_file_type_config(self, file_type: str, reload: bool = True) -> Dict[str, Any]:
        """
        Get file type configuration from new structure

        Args:
            file_type: Name of file type
            reload: Whether to check for file changes

        Returns:
            Dict with 'columns' and 'dtypes' keys
        """
        file_path = os.path.join(PathConstants.FILE_TYPES_DIR, f"{file_type}.json")

        if not os.path.exists(file_path):
            return {"columns": {}, "dtypes": {}}

        if reload:
            current_mtime = os.path.getmtime(file_path)
            cached_mtime = self._file_type_timestamps.get(file_type, 0)

            if file_type not in self._file_type_cache or current_mtime > cached_mtime:
                # Load from file
                config = json_manager.load_file_type(file_type)
                self._file_type_cache[file_type] = config
                self._file_type_timestamps[file_type] = current_mtime
                return config

        return self._file_type_cache.get(file_type, {"columns": {}, "dtypes": {}})

    def get_column_settings(self, file_type: str) -> Dict[str, Any]:
        """
        Get column settings for a specific file type

        Args:
            file_type: Specific file type to get settings for

        Returns:
            Column settings dictionary
        """
        with self._settings_lock:
            config = self._get_file_type_config(file_type)
            return config['columns']

    def get_dtype_settings(self, file_type: str) -> Dict[str, Any]:
        """
        Get dtype settings for a specific file type

        Args:
            file_type: Specific file type to get settings for

        Returns:
            Dtype settings dictionary
        """
        with self._settings_lock:
            config = self._get_file_type_config(file_type)
            return config['dtypes']

    def save_file_type(self, file_type: str, columns: Dict[str, str], dtypes: Dict[str, str]) -> bool:
        """
        Save file type configuration to new structure

        Args:
            file_type: Name of file type
            columns: Column mappings
            dtypes: Data type mappings

        Returns:
            bool: Success status
        """
        success = json_manager.save_file_type(file_type, columns, dtypes)
        if success:
            # Update cache
            with self._settings_lock:
                self._file_type_cache[file_type] = {"columns": columns, "dtypes": dtypes}
                file_path = os.path.join(PathConstants.FILE_TYPES_DIR, f"{file_type}.json")
                if os.path.exists(file_path):
                    self._file_type_timestamps[file_type] = os.path.getmtime(file_path)
        return success

    def list_file_types(self) -> List[str]:
        """
        List all available file types from new structure

        Returns:
            List of file type names
        """
        return json_manager.list_file_types()

    def delete_file_type(self, file_type: str) -> bool:
        """
        Delete a file type configuration

        Args:
            file_type: Name of file type

        Returns:
            bool: Success status
        """
        success = json_manager.delete_file_type(file_type)
        if success:
            with self._settings_lock:
                self._file_type_cache.pop(file_type, None)
                self._file_type_timestamps.pop(file_type, None)
        return success

    def clear_cache(self) -> None:
        """Clear all cached settings (will reload on next access)"""
        with self._settings_lock:
            self._file_type_cache.clear()
            self._file_type_timestamps.clear()


# Global instance
settings_manager = SettingsManager()
