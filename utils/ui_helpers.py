"""
UI Helper Functions

Common utilities for UI components
"""


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
