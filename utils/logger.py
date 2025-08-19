import logging
import json
import time
from typing import Callable, Optional, Dict, Any

from constants import AppConstants


class _GuiLogHandler(logging.Handler):
    """Logging handler that sends formatted messages to GUI callback"""

    def __init__(self, gui_callback: Callable[[str], None], level: int = logging.INFO, structured: bool = False) -> None:
        super().__init__(level)
        self._gui_callback = gui_callback
        self._structured = structured

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if self._structured:
                # Create structured log entry
                log_entry = {
                    'timestamp': time.time(),
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                msg = json.dumps(log_entry, ensure_ascii=False)
            else:
                msg = self.format(record)
            
            # Send formatted message to GUI
            self._gui_callback(msg)
        except (ValueError, TypeError, OSError):
            # Don't crash app because of log handler
            self.handleError(record)


def setup_logging(level: int = logging.INFO, force: bool = False) -> None:
    """Set up basic logging with standard app format

    Args:
        level: Default log level
        force: If True, will force reconfigure even if already configured
    """
    # ถ้า root logger เคยมี handler แล้ว และไม่ได้ force ให้ข้าม
    if logging.getLogger().handlers and not force:
        return

    logging.basicConfig(level=level, format=AppConstants.LOG_FORMAT)


def create_gui_log_handler(gui_callback: Callable[[str], None],
                           level: int = logging.INFO,
                           formatter: Optional[logging.Formatter] = None,
                           structured: bool = False) -> logging.Handler:
    """Create GUI log handler that sends messages to GUI callback

    Args:
        gui_callback: Function to receive formatted messages (one line)
        level: Log level for handler
        formatter: Formatter to use (if not specified, will use AppConstants.LOG_FORMAT)
        structured: If True, sends JSON formatted logs instead of plain text
    """
    handler = _GuiLogHandler(gui_callback, level, structured)
    if not structured and formatter is None:
        formatter = logging.Formatter(AppConstants.LOG_FORMAT)
    if formatter and not structured:
        handler.setFormatter(formatter)
    return handler


