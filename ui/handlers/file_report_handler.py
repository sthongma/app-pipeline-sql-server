"""File Processing Report and Summary Handler"""
from typing import Callable, Dict, Any
from utils.ui_helpers import format_elapsed_time
from utils.logger import setup_file_logging, cleanup_old_log_files
from config.json_manager import json_manager, get_log_folder
import os


class FileReportHandler:
    """Handles reporting and summary display for file operations"""

    def __init__(self, log_callback: Callable[[str], None]) -> None:
        """
        Initialize File Report Handler

        Args:
            log_callback: Function to call for logging
        """
        self.log: Callable[[str], None] = log_callback

    def display_processing_summary(self, stats: Dict[str, Any], total_files: int, operation_type: str = "Upload"):
        """
        แสดงรายงานสรุปการประมวลผล (ใช้ร่วมกันสำหรับ Upload และ Auto Process)

        Args:
            stats: Dictionary containing processing statistics
            total_files: Total number of files processed
            operation_type: Type of operation ("Upload" or "Processing")
        """
        separator = "=" * 42
        self.log(f"{separator[:9]} {operation_type} Summary Report {separator[:9]}")

        # เรียกใช้ระบบส่งออก log อัตโนมัติ
        self._auto_export_logs()

        # เวลารวม
        total_time = stats.get('total_time', 0)
        time_str = format_elapsed_time(total_time)

        self.log(f"Total {operation_type} Time: {time_str}")
        self.log(f"Total Files Processed: {total_files}")

        # แสดงสถิติเฉพาะที่มีค่ามากกว่า 0
        successful_files = stats.get('successful_files', 0)
        failed_files = stats.get('failed_files', 0)

        if successful_files > 0:
            self.log(f"Successful: {successful_files}")
        if failed_files > 0:
            self.log(f"Failed: {failed_files}")

        # รายละเอียดแต่ละประเภทไฟล์
        if stats.get('by_type'):
            self._display_file_type_details(stats, operation_type)

        # สรุปสำคัญ
        self._display_final_summary(stats, total_files, operation_type)

        self.log("=" * 42)

    def _display_file_type_details(self, stats: Dict[str, Any], operation_type: str):
        """แสดงรายละเอียดแต่ละประเภทไฟล์"""
        self.log("")
        self.log("Details by File Type (Occupation):")
        self.log("-" * 50)

        for file_type, type_stats in stats['by_type'].items():
            # แสดง header ของ file type
            type_time = type_stats.get('processing_time', 0)
            type_time_str = format_elapsed_time(type_time)

            self.log(f"Occupation: {file_type}")
            self.log(f"   Processing Time: {type_time_str}")
            self.log(f"   Total Files: {type_stats.get('files_count', 0)}")

            # แสดงผลสำเร็จ
            self._display_successful_files(type_stats, operation_type)

            # แสดงผลล้มเหลว
            self._display_failed_files(type_stats)

            self.log("")

    def _display_successful_files(self, type_stats: Dict[str, Any], operation_type: str):
        """แสดงรายละเอียดไฟล์ที่สำเร็จ"""
        successful = type_stats.get('successful_files', 0)
        if successful <= 0:
            return

        self.log(f"   Successful: {successful}")

        # แสดง summary message (มีเฉพาะ Upload operation)
        summary_message = type_stats.get('summary_message', '')
        if summary_message and operation_type == "Upload":
            self.log(f"   Upload Summary:")
            self.log(f"      {summary_message}")

        # แสดงรายชื่อไฟล์ที่สำเร็จ
        successful_file_list = type_stats.get('successful_file_list', [])
        if successful_file_list:
            self.log(f"      Files:")
            for filename in successful_file_list:
                self.log(f"         • {filename}")

    def _display_failed_files(self, type_stats: Dict[str, Any]):
        """แสดงรายละเอียดไฟล์ที่ล้มเหลว"""
        failed = type_stats.get('failed_files', 0)
        if failed <= 0:
            return

        self.log(f"   Failed: {failed}")

        failed_file_list = type_stats.get('failed_file_list', [])
        errors = type_stats.get('errors', [])
        validation_details = type_stats.get('validation_details', {})

        if failed_file_list:
            self.log(f"      Files with error details:")
            for filename in failed_file_list:
                self.log(f"         • {filename}")
                # หา error ที่ตรงกับไฟล์นี้
                matching_errors = [
                    err for err in errors
                    if filename in err or 'upload failed' in err.lower()
                ]
                if matching_errors:
                    for err in matching_errors:
                        error_detail = err.split(': ', 1)[-1] if ': ' in err else err
                        self.log(f"           ↳ {error_detail}")
                else:
                    self.log(f"           ↳ Unknown error")

        # แสดงรายละเอียด validation issues
        if validation_details:
            self._display_validation_details(validation_details)

    def _display_validation_details(self, validation_details: Dict[str, Any]):
        """แสดงรายละเอียด validation issues และ warnings"""
        issues = validation_details.get('issues', [])
        warnings = validation_details.get('warnings', [])

        if issues:
            self.log(f"      Validation Issues (Serious):")
            for issue in issues:
                column = issue.get('column', 'Unknown')
                error_count = issue.get('error_count', 0)
                percentage = issue.get('percentage', 0)
                examples = issue.get('examples', '')
                self.log(f"         Error: {column}: {error_count:,} invalid rows ({percentage}%) Examples: {examples}")

        if warnings:
            self.log(f"      Validation Warnings:")
            for warning in warnings:
                column = warning.get('column', 'Unknown')
                error_count = warning.get('error_count', 0)
                percentage = warning.get('percentage', 0)
                examples = warning.get('examples', '')
                self.log(f"         Warning: {column}: {error_count:,} invalid rows ({percentage}%) Examples: {examples}")

    def _display_final_summary(self, stats: Dict[str, Any], total_files: int, operation_type: str):
        """แสดงสรุปสุดท้าย"""
        success_rate = 0
        if total_files > 0:
            success_rate = (stats.get('successful_files', 0) / total_files) * 100

        self.log("Summary:")
        self.log(f"   Success Rate: {success_rate:.1f}%")

        if stats.get('failed_files', 0) > 0:
            action = "upload" if operation_type == "Upload" else "process"
            self.log(f"   Warning: Some files failed to {action}. Check the errors above for details.")
        else:
            action = "uploaded" if operation_type == "Upload" else "processed"
            self.log(f"   All files {action} successfully!")

    def display_upload_summary(self, upload_stats: Dict[str, Any], total_files: int):
        """แสดงรายงานสรุปการอัปโหลด (wrapper for backward compatibility)"""
        self.display_processing_summary(upload_stats, total_files, "Upload")

    def display_auto_process_summary(self, process_stats: Dict[str, Any], total_files: int):
        """แสดงรายงานสรุปการประมวลผลอัตโนมัติ (wrapper for backward compatibility)"""
        self.display_processing_summary(process_stats, total_files, "Processing")

    def _load_log_folder_from_config(self):
        """Load log folder path using JSONManager"""
        try:
            return get_log_folder()
        except Exception:
            return None

    def _auto_export_logs(self):
        """ส่งออก log อัตโนมัติไปยังโฟลเดอร์ log_pipeline และจัดการไฟล์เก่า"""
        try:
            # โหลดการตั้งค่า
            app_settings = json_manager.load('app_settings')

            # ตรวจสอบว่าเปิดใช้งานการส่งออกอัตโนมัติหรือไม่
            auto_export = app_settings.get('auto_export_logs', True)
            if not auto_export:
                return

            # อ่าน log folder path จาก log_folder_config.json
            log_folder_path = self._load_log_folder_from_config()
            if not log_folder_path or not os.path.exists(log_folder_path):
                self.log("Warning: Cannot export logs: No valid log folder configured")
                return

            # ตั้งค่า file logging และส่งออก
            log_file_path = setup_file_logging(log_folder_path, enable_export=True)
            if log_file_path:
                self.log(f"Log exported to: {log_file_path}")

                # จัดการไฟล์ log เก่า (ลบไฟล์ที่เก่าเกิน retention period)
                retention_days = app_settings.get('log_retention_days', 30)
                deleted_count = cleanup_old_log_files(log_folder_path, retention_days)

                # แสดงผลการ cleanup เฉพาะเมื่อมีการลบไฟล์
                if deleted_count > 0:
                    self.log(f"Cleaned up {deleted_count} old log files (older than {retention_days} days)")
            else:
                self.log("Warning: Failed to export log file")

        except Exception as e:
            self.log(f"Error: Error during auto export logs: {e}")
