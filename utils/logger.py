import logging
import json
import time
import os
import warnings
from datetime import datetime
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

    # ซ่อน warning ที่ไม่สำคัญจาก openpyxl และ libraries อื่นๆ
    configure_warning_filters()


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


def setup_file_logging(base_path: str, enable_export: bool = True) -> Optional[str]:
    """Set up file logging to export logs directly to selected folder

    Args:
        base_path: Directory path where log file will be saved
        enable_export: Whether to enable file export logging

    Returns:
        Log file path if successful, None if failed
    """
    if not enable_export or not base_path or not os.path.exists(base_path):
        return None

    try:
        # สร้างชื่อไฟล์ log ตามรูปแบบ log_pipeline_{วันที่}.log (ไม่มีเวลา เพื่อให้บันทึกต่อท้ายในวันเดียวกัน)
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_filename = f"log_pipeline_{date_str}.log"
        log_file_path = os.path.join(base_path, log_filename)

        # สร้าง FileHandler (mode='a' เพื่อ append ต่อท้ายไฟล์เดิม)
        file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(AppConstants.LOG_FORMAT))

        # เพิ่ม FileHandler ไปยัง root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        return log_file_path

    except Exception as e:
        # ถ้าเกิดข้อผิดพลาด ใช้ logging แบบปกติไปก่อน (ไม่ให้ระบบล้ม)
        try:
            logging.error(f"Failed to setup file logging: {e}")
        except:
            pass
        return None


def export_current_logs_to_file(log_file_path: str, log_content: str) -> bool:
    """Export current log content to specified file
    
    Args:
        log_file_path: Path to the log file to write to
        log_content: Log content to write
        
    Returns:
        True if export successful, False otherwise
    """
    try:
        with open(log_file_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        return True
    except Exception:
        return False


def configure_warning_filters() -> None:
    """กำหนดการกรอง warning จาก libraries ต่างๆ ให้แสดงเฉพาะที่สำคัญ"""

    # ซ่อน UserWarning จาก openpyxl เกี่ยวกับ default style
    warnings.filterwarnings(
        'ignore',
        category=UserWarning,
        module='openpyxl.styles.stylesheet',
        message='.*Workbook contains no default style.*'
    )

    # ซ่อน warning อื่นๆ จาก openpyxl ที่ไม่สำคัญ
    warnings.filterwarnings(
        'ignore',
        category=UserWarning,
        module='openpyxl.*',
        message='.*Data Validation.*'
    )

    # ปรับ logging level ของ openpyxl ให้แสดงเฉพาะ ERROR
    logging.getLogger('openpyxl').setLevel(logging.ERROR)

    # ปรับ logging level ของ xlrd ให้แสดงเฉพาะ ERROR
    logging.getLogger('xlrd').setLevel(logging.ERROR)


class FriendlyLogFormatter(logging.Formatter):
    """
    Custom log formatter ที่แสดงข้อความให้เป็นมิตรและอ่านง่ายขึ้น

    Features:
    - ใช้สัญลักษณ์ที่เข้าใจง่าย (✓, ✗, ⚠, ℹ)
    - แปลข้อความภาษาอังกฤษเป็นภาษาไทย (ถ้าต้องการ)
    - จัดกลุ่มข้อมูลให้อ่านง่าย
    """

    # สัญลักษณ์สำหรับแต่ละ log level
    LEVEL_ICONS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }

    # รูปแบบข้อความที่สั้นและกระชับ
    FRIENDLY_FORMAT = '%(asctime)s | %(levelicon)s %(message)s'
    DATE_FORMAT = '%H:%M:%S'

    def __init__(self, use_icons: bool = True, date_format: str = None):
        """
        Initialize formatter

        Args:
            use_icons: แสดงไอคอนหรือไม่ (default: True)
            date_format: รูปแบบวันที่/เวลา (default: HH:MM:SS)
        """
        super().__init__(
            fmt=self.FRIENDLY_FORMAT,
            datefmt=date_format or self.DATE_FORMAT
        )
        self.use_icons = use_icons

    def format(self, record: logging.LogRecord) -> str:
        """Format log record ให้เป็นมิตรกับผู้ใช้"""

        # เพิ่ม icon ตาม level
        if self.use_icons:
            record.levelicon = self.LEVEL_ICONS.get(record.levelname, '•')
        else:
            record.levelicon = f'[{record.levelname}]'

        # ทำการ format ตามปกติ
        formatted = super().format(record)

        return formatted


def create_friendly_formatter(use_icons: bool = True) -> FriendlyLogFormatter:
    """
    สร้าง formatter ที่เป็นมิตรกับผู้ใช้

    Args:
        use_icons: ใช้ icon แทน level text (default: True)

    Returns:
        FriendlyLogFormatter instance
    """
    return FriendlyLogFormatter(use_icons=use_icons)


def cleanup_old_log_files(base_path: str, retention_days: int = 30) -> int:
    """Clean up old log files older than retention period

    Args:
        base_path: Directory path where log files are stored (user-selected log folder)
        retention_days: Number of days to retain log files (default: 30)

    Returns:
        Number of files deleted
    """
    if not base_path or not os.path.exists(base_path):
        return 0

    try:
        deleted_count = 0
        cutoff_time = time.time() - (retention_days * 24 * 60 * 60)  # Convert days to seconds

        # ค้นหาไฟล์ log ที่เก่าเกิน retention period
        for filename in os.listdir(base_path):
            # ตรวจสอบว่าเป็นไฟล์ log ของระบบเท่านั้น (ป้องกันการลบไฟล์อื่น)
            if filename.startswith('log_pipeline_') and filename.endswith('.log'):
                file_path = os.path.join(base_path, filename)
                try:
                    # ตรวจสอบว่าเป็นไฟล์จริง (ไม่ใช่โฟลเดอร์)
                    if not os.path.isfile(file_path):
                        continue

                    # ตรวจสอบเวลาที่แก้ไขไฟล์ล่าสุด
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        logging.info(f"Deleted old log file: {filename}")
                except (OSError, PermissionError) as e:
                    logging.warning(f"Could not delete log file {filename}: {e}")

        if deleted_count > 0:
            logging.info(f"Log cleanup completed: {deleted_count} old files deleted")

        return deleted_count

    except Exception as e:
        logging.error(f"Error during log cleanup: {e}")
        return 0


