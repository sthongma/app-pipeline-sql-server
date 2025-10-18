"""
UI Callbacks Data Structure

Provides type-safe interface for UI callback functions
"""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class UICallbacks:
    """
    Type-safe container for UI callback functions

    This replaces the dictionary-based callbacks with a more maintainable
    and type-safe approach using dataclasses.
    """

    # Progress bar callbacks
    reset_progress: Callable[[], None]
    set_progress_status: Callable[[str, Optional[str]], None]
    update_progress: Callable[[float, str, str], None]

    # File list callbacks
    clear_file_list: Callable[[], None]
    add_file_to_list: Callable[[str, str], None]

    # Select all callbacks
    reset_select_all: Callable[[], None]
    enable_select_all: Callable[[], None]

    # Status bar callbacks
    update_status: Callable[[str, bool], None]

    # Control callbacks
    disable_controls: Callable[[], None]
    enable_controls: Callable[[], None]

    # Checkbox callbacks
    disable_checkbox: Callable[[object], None]
    set_file_uploaded: Callable[[str], None]

    def to_dict(self) -> dict:
        """
        Convert to dictionary format for backward compatibility

        Returns:
            Dictionary with callback names as keys
        """
        return {
            'reset_progress': self.reset_progress,
            'set_progress_status': self.set_progress_status,
            'update_progress': self.update_progress,
            'clear_file_list': self.clear_file_list,
            'add_file_to_list': self.add_file_to_list,
            'reset_select_all': self.reset_select_all,
            'enable_select_all': self.enable_select_all,
            'update_status': self.update_status,
            'disable_controls': self.disable_controls,
            'enable_controls': self.enable_controls,
            'disable_checkbox': self.disable_checkbox,
            'set_file_uploaded': self.set_file_uploaded,
        }

    @classmethod
    def from_dict(cls, callbacks_dict: dict) -> 'UICallbacks':
        """
        Create UICallbacks instance from dictionary

        Args:
            callbacks_dict: Dictionary containing callback functions

        Returns:
            UICallbacks instance
        """
        return cls(
            reset_progress=callbacks_dict['reset_progress'],
            set_progress_status=callbacks_dict['set_progress_status'],
            update_progress=callbacks_dict['update_progress'],
            clear_file_list=callbacks_dict['clear_file_list'],
            add_file_to_list=callbacks_dict['add_file_to_list'],
            reset_select_all=callbacks_dict['reset_select_all'],
            enable_select_all=callbacks_dict['enable_select_all'],
            update_status=callbacks_dict['update_status'],
            disable_controls=callbacks_dict['disable_controls'],
            enable_controls=callbacks_dict['enable_controls'],
            disable_checkbox=callbacks_dict['disable_checkbox'],
            set_file_uploaded=callbacks_dict['set_file_uploaded'],
        )
