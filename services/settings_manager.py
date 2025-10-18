"""
Settings Manager Service

Centralizes settings loading, caching, and reloading logic
"""

import json
import os
import threading
from typing import Dict, Any, Optional
from constants import PathConstants


class SettingsManager:
    """
    Centralized settings management with file watching and caching

    Responsibilities:
    - Load column and dtype settings from JSON files
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

        # Settings cache
        self.column_settings: Dict[str, Any] = {}
        self.dtype_settings: Dict[str, Any] = {}

        # File modification timestamps
        self._file_timestamps: Dict[str, float] = {
            'column_settings': 0,
            'dtype_settings': 0
        }

        # Load settings initially
        self.reload_all()

    def reload_all(self, force: bool = False) -> None:
        """
        Reload all settings from disk

        Args:
            force: Force reload even if files haven't changed
        """
        with self._settings_lock:
            self._reload_column_settings(force)
            self._reload_dtype_settings(force)

    def _reload_column_settings(self, force: bool = False) -> None:
        """Reload column settings if file has changed"""
        settings_file = PathConstants.COLUMN_SETTINGS_FILE

        if not os.path.exists(settings_file):
            self.column_settings = {}
            self._file_timestamps['column_settings'] = 0
            return

        current_mtime = os.path.getmtime(settings_file)
        cached_mtime = self._file_timestamps.get('column_settings', 0)

        if force or current_mtime > cached_mtime:
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    self.column_settings = json.load(f)
                self._file_timestamps['column_settings'] = current_mtime
            except Exception:
                self.column_settings = {}
                self._file_timestamps['column_settings'] = 0

    def _reload_dtype_settings(self, force: bool = False) -> None:
        """Reload dtype settings if file has changed"""
        dtype_file = PathConstants.DTYPE_SETTINGS_FILE

        if not os.path.exists(dtype_file):
            self.dtype_settings = {}
            self._file_timestamps['dtype_settings'] = 0
            return

        current_mtime = os.path.getmtime(dtype_file)
        cached_mtime = self._file_timestamps.get('dtype_settings', 0)

        if force or current_mtime > cached_mtime:
            try:
                with open(dtype_file, 'r', encoding='utf-8') as f:
                    self.dtype_settings = json.load(f)
                self._file_timestamps['dtype_settings'] = current_mtime
            except Exception:
                self.dtype_settings = {}
                self._file_timestamps['dtype_settings'] = 0

    def get_column_settings(self, file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get column settings, auto-reload if file changed

        Args:
            file_type: Specific file type to get settings for, or None for all

        Returns:
            Column settings dictionary
        """
        with self._settings_lock:
            self._reload_column_settings()
            if file_type:
                return self.column_settings.get(file_type, {})
            return self.column_settings.copy()

    def get_dtype_settings(self, file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get dtype settings, auto-reload if file changed

        Args:
            file_type: Specific file type to get settings for, or None for all

        Returns:
            Dtype settings dictionary
        """
        with self._settings_lock:
            self._reload_dtype_settings()
            if file_type:
                return self.dtype_settings.get(file_type, {})
            return self.dtype_settings.copy()

    def save_column_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save column settings to file

        Args:
            settings: Column settings to save

        Returns:
            True if successful, False otherwise
        """
        try:
            settings_file = PathConstants.COLUMN_SETTINGS_FILE

            # Ensure directory exists
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)

            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            # Update cache
            with self._settings_lock:
                self.column_settings = settings.copy()
                self._file_timestamps['column_settings'] = os.path.getmtime(settings_file)

            return True
        except Exception:
            return False

    def save_dtype_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save dtype settings to file

        Args:
            settings: Dtype settings to save

        Returns:
            True if successful, False otherwise
        """
        try:
            dtype_file = PathConstants.DTYPE_SETTINGS_FILE

            # Ensure directory exists
            os.makedirs(os.path.dirname(dtype_file), exist_ok=True)

            with open(dtype_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            # Update cache
            with self._settings_lock:
                self.dtype_settings = settings.copy()
                self._file_timestamps['dtype_settings'] = os.path.getmtime(dtype_file)

            return True
        except Exception:
            return False

    def clear_cache(self) -> None:
        """Clear all cached settings (will reload on next access)"""
        with self._settings_lock:
            self._file_timestamps = {
                'column_settings': 0,
                'dtype_settings': 0
            }


# Global instance
settings_manager = SettingsManager()
