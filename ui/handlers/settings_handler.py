"""Settings Operation Handlers - Modernized with Settings Manager"""
from config.json_manager import (
    json_manager,
    get_input_folder,
    set_input_folder
)
from services.settings_manager import settings_manager


class SettingsHandler:
    """
    Modernized Settings Handler using centralized Settings Manager.

    Provides backward compatibility while using the new unified system.
    """

    def __init__(self, settings_file, log_callback):
        """
        Initialize Settings Handler

        Args:
            settings_file: Path to settings file (kept for compatibility)
            log_callback: Function to call for logging
        """
        self.settings_file = settings_file  # Kept for compatibility
        self.log = log_callback

    def load_column_settings(self):
        """Load all column settings from settings manager."""
        try:
            # Build legacy-style dictionary from all file types
            column_settings = {}
            file_types = settings_manager.list_file_types()
            for file_type in file_types:
                column_settings[file_type] = settings_manager.get_column_settings(file_type)
            return column_settings
        except Exception as e:
            self.log(f"Cannot load column settings: {e}")
            return {}

    def save_column_settings(self, column_settings):
        """Save column settings for all file types."""
        try:
            # column_settings is a dict of {file_type: {original_col: mapped_col}}
            # Save each file type separately
            for file_type, columns in column_settings.items():
                # Get existing dtypes for this file type
                dtypes = settings_manager.get_dtype_settings(file_type)
                settings_manager.save_file_type(file_type, columns, dtypes)
            self.log("Column settings saved successfully")
        except Exception as e:
            self.log(f"Cannot save column settings: {e}")

    def load_dtype_settings(self):
        """Load all dtype settings from settings manager."""
        try:
            # Build legacy-style dictionary from all file types
            dtype_settings = {}
            file_types = settings_manager.list_file_types()
            for file_type in file_types:
                dtype_settings[file_type] = settings_manager.get_dtype_settings(file_type)
            return dtype_settings
        except Exception as e:
            self.log(f"Cannot load data type settings: {e}")
            return {}

    def save_dtype_settings(self, dtype_settings):
        """Save dtype settings for all file types."""
        try:
            # dtype_settings is a dict of {file_type: {column: dtype}}
            # Save each file type separately
            for file_type, dtypes in dtype_settings.items():
                # Get existing columns for this file type
                columns = settings_manager.get_column_settings(file_type)
                settings_manager.save_file_type(file_type, columns, dtypes)
            self.log("Data type settings saved successfully")
        except Exception as e:
            self.log(f"Cannot save data type settings: {e}")
    
    def load_input_folder(self):
        """Load input folder path using JSON Manager."""
        try:
            return get_input_folder()
        except Exception as e:
            self.log(f"Cannot load input folder path: {e}")
            return None

    def save_input_folder(self, path):
        """Save input folder path using JSON Manager."""
        try:
            success = set_input_folder(path)
            if not success:
                self.log("Failed to save input folder path")
        except Exception as e:
            self.log(f"Save input folder path error: {e}")


# Convenience functions for direct access
def get_column_settings():
    """Get column settings directly."""
    return load_column_config()

def set_column_settings(settings):
    """Set column settings directly."""
    return save_column_config(settings)

def get_dtype_settings():
    """Get data type settings directly."""
    return load_dtype_config()

def set_dtype_settings(settings):
    """Set data type settings directly."""
    return save_dtype_config(settings)
