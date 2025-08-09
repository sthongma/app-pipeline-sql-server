import logging
from typing import Callable, Optional

from constants import AppConstants


class _GuiLogHandler(logging.Handler):
    """Logging handler ที่ส่งข้อความที่ถูก format แล้วไปยัง callback ของ GUI"""

    def __init__(self, gui_callback: Callable[[str], None], level: int = logging.INFO) -> None:
        super().__init__(level)
        self._gui_callback = gui_callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            # ส่งข้อความหนึ่งบรรทัดที่ถูก format แล้วไปยัง GUI
            self._gui_callback(msg)
        except Exception:
            # อย่าทำให้แอปหลุดเพราะ log handler
            self.handleError(record)


def setup_logging(level: int = logging.INFO, force: bool = False) -> None:
    """ตั้งค่า logging พื้นฐานด้วยรูปแบบมาตรฐานของแอป

    Args:
        level: ระดับ log เริ่มต้น
        force: หาก True จะบังคับ reconfigure แม้เคยตั้งค่าไปแล้ว
    """
    # ถ้า root logger เคยมี handler แล้ว และไม่ได้ force ให้ข้าม
    if logging.getLogger().handlers and not force:
        return

    logging.basicConfig(level=level, format=AppConstants.LOG_FORMAT)


def create_gui_log_handler(gui_callback: Callable[[str], None],
                           level: int = logging.INFO,
                           formatter: Optional[logging.Formatter] = None) -> logging.Handler:
    """สร้าง GUI log handler ที่จะส่งข้อความไปยัง callback ของ GUI

    Args:
        gui_callback: ฟังก์ชันรับข้อความที่ถูก format แล้ว (หนึ่งบรรทัด)
        level: ระดับ log ของ handler
        formatter: ตัว formatter ที่จะใช้ (ถ้าไม่ระบุ จะใช้ AppConstants.LOG_FORMAT)
    """
    handler = _GuiLogHandler(gui_callback, level)
    if formatter is None:
        formatter = logging.Formatter(AppConstants.LOG_FORMAT)
    handler.setFormatter(formatter)
    return handler


