"""
UI Helper Functions

Common utilities for UI components including emoji colors and formatting
"""

from typing import Dict


def get_emoji_color_map() -> Dict[str, str]:
    """
    Get mapping of emoji characters to their color tag names

    Returns:
        Dict mapping emoji to color tag name
    """
    return {
        '✅': 'emoji_success',
        '❌': 'emoji_error',
        '⚠️': 'emoji_warning',
        '📊': 'emoji_info',
        '📁': 'emoji_info',
        'ℹ️': 'emoji_info',
        '🔍': 'emoji_search',
        '🎉': 'emoji_highlight',
        '📋': 'emoji_phase',
        '⏳': 'emoji_phase',
        '📦': 'emoji_file',
        '📤': 'emoji_file',
        '⏱️': 'emoji_time',
        '🔄': 'emoji_phase',
        '🚀': 'emoji_highlight',
        '💾': 'emoji_info',
        '🧹': 'emoji_search',
        '🏷️': 'emoji_phase',
    }


def setup_emoji_colors(text_widget) -> None:
    """
    Configure emoji color tags for a text widget

    Args:
        text_widget: CTkTextbox or tkinter Text widget to configure
    """
    text_widget.tag_config("emoji_success", foreground="#41AA41")    # Green
    text_widget.tag_config("emoji_error", foreground="#FF4444")      # Red
    text_widget.tag_config("emoji_warning", foreground="#FFA500")    # Orange
    text_widget.tag_config("emoji_info", foreground="#00BFFF")       # Sky blue
    text_widget.tag_config("emoji_search", foreground="#888888")     # Gray
    text_widget.tag_config("emoji_highlight", foreground="#FFD700")  # Gold
    text_widget.tag_config("emoji_phase", foreground="#FF69B4")      # Pink
    text_widget.tag_config("emoji_file", foreground="#00CED1")       # Dark cyan
    text_widget.tag_config("emoji_time", foreground="#9370DB")       # Purple


def insert_colored_message(text_widget, message: str, emoji_colors: Dict[str, str]) -> None:
    """
    Insert message with colored emojis into text widget

    Args:
        text_widget: Text widget to insert into
        message: Message string to insert
        emoji_colors: Dict mapping emoji to color tag name
    """
    for char in message:
        if char in emoji_colors:
            text_widget.insert("end", char, emoji_colors[char])
        else:
            text_widget.insert("end", char)


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
