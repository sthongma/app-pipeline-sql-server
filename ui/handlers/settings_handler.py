"""Settings Operation Handlers - Modernized with JSON Manager"""
from config.json_manager import (
    json_manager,
    load_column_settings as load_column_config,
    save_column_settings as save_column_config,
    load_dtype_settings as load_dtype_config,
    save_dtype_settings as save_dtype_config,
    get_last_path,
    set_last_path
)


class SettingsHandler:
    """
    Modernized Settings Handler using centralized JSON Manager.
    
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
        """Load column settings using JSON Manager."""
        try:
            settings = load_column_config()
            return settings
        except Exception as e:
            self.log(f"Cannot load column settings: {e}")
            return {}
    
    def save_column_settings(self, column_settings):
        """Save column settings using JSON Manager."""
        try:
            success = save_column_config(column_settings)
            if success:
                self.log("Column settings saved successfully")
            else:
                self.log("Failed to save column settings")
        except Exception as e:
            self.log(f"Cannot save column settings: {e}")
    
    def load_dtype_settings(self):
        """Load data type settings using JSON Manager."""
        try:
            settings = load_dtype_config()
            return settings
        except Exception as e:
            self.log(f"Cannot load data type settings: {e}")
            return {}
    
    def save_dtype_settings(self, dtype_settings):
        """Save data type settings using JSON Manager."""
        try:
            success = save_dtype_config(dtype_settings)
            if success:
                self.log("Data type settings saved successfully")
            else:
                self.log("Failed to save data type settings")
        except Exception as e:
            self.log(f"Cannot save data type settings: {e}")
    
    def load_last_path(self):
        """Load last search path using JSON Manager."""
        try:
            return get_last_path()
        except Exception as e:
            self.log(f"Cannot load last path: {e}")
            return None
    
    def save_last_path(self, path):
        """Save last search path using JSON Manager."""
        try:
            success = set_last_path(path)
            if not success:
                self.log("Failed to save last path")
        except Exception as e:
            self.log(f"Save last path error: {e}")


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
