"""
Error Handling Helper Utilities

Provides consistent error handling patterns across the application
"""

from typing import Callable, Any, Optional, TypeVar
import logging

T = TypeVar('T')


class SafeOperation:
    """
    Wrapper for safe operation execution with consistent error handling

    Provides centralized error handling, logging, and default return values
    """

    @staticmethod
    def execute(
        func: Callable[[], T],
        log_callback: Optional[Callable[[str], None]] = None,
        operation_name: str = "Operation",
        default_return: Optional[T] = None,
        raise_on_error: bool = False
    ) -> T:
        """
        Execute function with consistent error handling

        Args:
            func: Function to execute
            log_callback: Optional logging function
            operation_name: Name of operation for logging
            default_return: Value to return on error
            raise_on_error: If True, re-raise exception after logging

        Returns:
            Result from func() or default_return on error

        Example:
            result = SafeOperation.execute(
                lambda: risky_operation(),
                log_callback=self.log,
                operation_name="Loading settings",
                default_return={}
            )
        """
        try:
            return func()
        except Exception as e:
            error_msg = f"❌ {operation_name} failed: {str(e)}"

            if log_callback:
                log_callback(error_msg)
            else:
                logging.error(error_msg)

            if raise_on_error:
                raise

            return default_return

    @staticmethod
    def execute_with_result(
        func: Callable[[], T],
        log_callback: Optional[Callable[[str], None]] = None,
        operation_name: str = "Operation"
    ) -> tuple[bool, Any]:
        """
        Execute function and return (success, result) tuple

        Args:
            func: Function to execute
            log_callback: Optional logging function
            operation_name: Name of operation for logging

        Returns:
            Tuple of (success: bool, result or error_message)

        Example:
            success, result = SafeOperation.execute_with_result(
                lambda: load_data(),
                log_callback=self.log,
                operation_name="Loading data"
            )
            if success:
                data = result
            else:
                error_msg = result
        """
        try:
            result = func()
            return True, result
        except Exception as e:
            error_msg = f"{operation_name} failed: {str(e)}"

            if log_callback:
                log_callback(f"❌ {error_msg}")
            else:
                logging.error(error_msg)

            return False, error_msg


def safe_file_operation(
    operation: Callable[[], T],
    file_path: str,
    log_callback: Optional[Callable[[str], None]] = None,
    default_return: Optional[T] = None
) -> T:
    """
    Safely execute file operation with automatic error handling

    Args:
        operation: File operation to execute
        file_path: Path to file (for error messages)
        log_callback: Optional logging function
        default_return: Value to return on error

    Returns:
        Result from operation() or default_return on error
    """
    return SafeOperation.execute(
        operation,
        log_callback=log_callback,
        operation_name=f"File operation on '{file_path}'",
        default_return=default_return
    )


def safe_database_operation(
    operation: Callable[[], T],
    operation_desc: str,
    log_callback: Optional[Callable[[str], None]] = None,
    default_return: Optional[T] = None
) -> T:
    """
    Safely execute database operation with automatic error handling

    Args:
        operation: Database operation to execute
        operation_desc: Description of operation (for error messages)
        log_callback: Optional logging function
        default_return: Value to return on error

    Returns:
        Result from operation() or default_return on error
    """
    return SafeOperation.execute(
        operation,
        log_callback=log_callback,
        operation_name=f"Database operation: {operation_desc}",
        default_return=default_return
    )
