"""
UI Helper Functions

Common utilities for UI components
"""
import os

# Cache สำหรับ icon path
_app_icon_path = None


def get_app_icon_path() -> str:
    """
    Get the path to app_icon.ico
    
    Returns:
        Path to app_icon.ico or empty string if not found
    """
    global _app_icon_path
    if _app_icon_path is None:
        # หา path จาก utils folder ไปยัง build_resources
        base_dir = os.path.dirname(os.path.dirname(__file__))
        _app_icon_path = os.path.join(base_dir, "build_resources", "app_icon.ico")
        if not os.path.exists(_app_icon_path):
            _app_icon_path = ""
    return _app_icon_path


def set_window_icon(window, delay_ms: int = 0) -> None:
    """
    Set window icon to app_icon.ico
    
    Args:
        window: Tkinter/CTk window instance
        delay_ms: Delay in milliseconds before setting icon (useful for CTkToplevel)
    """
    icon_path = get_app_icon_path()
    if icon_path:
        if delay_ms > 0:
            window.after(delay_ms, lambda: window.iconbitmap(icon_path))
        else:
            window.iconbitmap(icon_path)


def format_elapsed_time(total_seconds: float) -> str:
    """
    Format elapsed time into human-readable string

    Args:
        total_seconds: Total seconds elapsed

    Returns:
        Formatted string like "2h 30m 45s", "5m 30s", or "45s"
    """
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"
