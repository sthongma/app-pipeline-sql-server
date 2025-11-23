"""
Utility functions for preventing double-click on buttons
"""
import functools
from typing import Callable, Optional, Any


def with_button_disabled(func: Callable) -> Callable:
    """
    Decorator to disable button while function executes.

    Use this for simple operations like opening dialogs.
    The button reference must be passed as the first argument after self.

    Example:
        @with_button_disabled
        def _browse_folder(self, button):
            # button will be disabled during this function
            folder = filedialog.askdirectory()
            ...

    Args:
        func: Function to wrap

    Returns:
        Wrapped function with button disable/enable logic
    """
    @functools.wraps(func)
    def wrapper(self, button, *args, **kwargs):
        # Check if button is already disabled
        if button.cget('state') == 'disabled':
            return  # Already processing, ignore this click

        # Disable button immediately
        button.configure(state='disabled')

        try:
            # Execute the original function
            return func(self, button, *args, **kwargs)
        finally:
            # Always re-enable button
            button.configure(state='normal')

    return wrapper


class ProcessingFlag:
    """
    Context manager for processing flags with optional button disable.

    Use this for complex operations like uploads, connections, or long-running tasks.
    Provides both flag checking and button state management.

    Example:
        def upload(self):
            with ProcessingFlag(
                self,
                'is_uploading',
                button=self.upload_btn,
                on_abort=lambda: self.log("Already uploading...")
            ) as can_proceed:
                if not can_proceed:
                    return

                # Your upload logic here
                ...

    Args:
        obj: Object that contains the flag attribute
        flag_name: Name of the flag attribute (e.g., 'is_uploading')
        button: Optional button to disable during processing
        on_abort: Optional callback function to call if already processing
    """

    def __init__(
        self,
        obj: Any,
        flag_name: str,
        button: Optional[Any] = None,
        on_abort: Optional[Callable] = None
    ):
        self.obj = obj
        self.flag_name = flag_name
        self.button = button
        self.on_abort = on_abort
        self.should_continue = False

    def __enter__(self) -> bool:
        """
        Enter the context manager.

        Returns:
            bool: True if processing can proceed, False if already processing
        """
        # Check if already processing
        if getattr(self.obj, self.flag_name, False):
            # Already processing, call abort callback if provided
            if self.on_abort:
                self.on_abort()
            return False

        # Set flag to indicate processing has started
        setattr(self.obj, self.flag_name, True)

        # Disable button if provided
        if self.button:
            self.button.configure(state='disabled')

        self.should_continue = True
        return True

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager.

        Always resets flag and re-enables button, even if an exception occurred.
        """
        # Reset flag
        setattr(self.obj, self.flag_name, False)

        # Re-enable button if provided
        if self.button:
            self.button.configure(state='normal')

        # Don't suppress exceptions
        return False
