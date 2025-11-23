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

        # Legacy cache (for backward compatibility)
        self.column_settings: Dict[str, Any] = {}
        self.dtype_settings: Dict[str, Any] = {}
        self._file_timestamps: Dict[str, float] = {
            'column_settings': 0,
            'dtype_settings': 0
        }

        # Load legacy settings initially if they exist
        self.reload_all()

    def reload_all(self, force: bool = False) -> None:
        """
        Reload all settings from disk

        Args:
            force: Force reload even if files haven't changed
        """
        with self._settings_lock:
            self._reload_legacy_settings(force)
            self._file_type_cache.clear()
            self._file_type_timestamps.clear()

    def _reload_legacy_settings(self, force: bool = False) -> None:
        """Reload legacy column and dtype settings files if they exist"""
        # Check for legacy column_settings.json
        column_file = PathConstants.COLUMN_SETTINGS_FILE
        if os.path.exists(column_file):
            current_mtime = os.path.getmtime(column_file)
            cached_mtime = self._file_timestamps.get('column_settings', 0)

            if force or current_mtime > cached_mtime:
                try:
                    with open(column_file, 'r', encoding='utf-8') as f:
                        self.column_settings = json.load(f)
                    self._file_timestamps['column_settings'] = current_mtime
                except Exception:
                    self.column_settings = {}
        else:
            self.column_settings = {}

        # Check for legacy dtype_settings.json
        dtype_file = PathConstants.DTYPE_SETTINGS_FILE
        if os.path.exists(dtype_file):
            current_mtime = os.path.getmtime(dtype_file)
            cached_mtime = self._file_timestamps.get('dtype_settings', 0)

            if force or current_mtime > cached_mtime:
                try:
                    with open(dtype_file, 'r', encoding='utf-8') as f:
                        self.dtype_settings = json.load(f)
                    self._file_timestamps['dtype_settings'] = current_mtime
                except Exception:
                    self.dtype_settings = {}
        else:
            self.dtype_settings = {}

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

    def get_column_settings(self, file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get column settings with support for both legacy and new structure

        Args:
            file_type: Specific file type to get settings for, or None for all

        Returns:
            Column settings dictionary
        """
        with self._settings_lock:
            # Try new structure first
            if file_type and os.path.exists(PathConstants.FILE_TYPES_DIR):
                config = self._get_file_type_config(file_type)
                if config['columns']:
                    return config['columns']

            # Fall back to legacy structure
            self._reload_legacy_settings()
            if file_type:
                return self.column_settings.get(file_type, {})
            return self.column_settings.copy()

    def get_dtype_settings(self, file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get dtype settings with support for both legacy and new structure

        Args:
            file_type: Specific file type to get settings for, or None for all

        Returns:
            Dtype settings dictionary
        """
        with self._settings_lock:
            # Try new structure first
            if file_type and os.path.exists(PathConstants.FILE_TYPES_DIR):
                config = self._get_file_type_config(file_type)
                if config['dtypes']:
                    return config['dtypes']

            # Fall back to legacy structure
            self._reload_legacy_settings()
            if file_type:
                return self.dtype_settings.get(file_type, {})
            return self.dtype_settings.copy()

    def save_column_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save column settings to legacy file (backward compatibility)

        Args:
            settings: Column settings to save (dict of file_type -> columns)

        Returns:
            True if successful, False otherwise
        """
        try:
            settings_file = PathConstants.COLUMN_SETTINGS_FILE
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)

            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            with self._settings_lock:
                self.column_settings = settings.copy()
                self._file_timestamps['column_settings'] = os.path.getmtime(settings_file)

            return True
        except Exception:
            return False

    def save_dtype_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save dtype settings to legacy file (backward compatibility)

        Args:
            settings: Dtype settings to save (dict of file_type -> dtypes)

        Returns:
            True if successful, False otherwise
        """
        try:
            dtype_file = PathConstants.DTYPE_SETTINGS_FILE
            os.makedirs(os.path.dirname(dtype_file), exist_ok=True)

            with open(dtype_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            with self._settings_lock:
                self.dtype_settings = settings.copy()
                self._file_timestamps['dtype_settings'] = os.path.getmtime(dtype_file)

            return True
        except Exception:
            return False

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
            self._file_timestamps = {
                'column_settings': 0,
                'dtype_settings': 0
            }
            self._file_type_cache.clear()
            self._file_type_timestamps.clear()


# Global instance
settings_manager = SettingsManager()
