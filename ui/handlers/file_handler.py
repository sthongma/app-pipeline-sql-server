"""File Operation Handlers"""
import os
import threading
import time
from datetime import datetime
from tkinter import messagebox, filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Callable, Optional, Any
import pandas as pd
from utils.logger import setup_file_logging, cleanup_old_log_files
from config.json_manager import json_manager, get_log_folder
from performance_optimizations import PerformanceOptimizer
from utils.ui_helpers import format_elapsed_time
from ui.utils.button_utils import ProcessingFlag


class FileHandler:
    def __init__(
        self,
        file_service: Any,
        db_service: Any,
        file_mgmt_service: Any,
        log_callback: Callable[[str], None]
    ) -> None:
        """
        Initialize File Handler

        Args:
            file_service: File service instance
            db_service: Database service instance
            file_mgmt_service: File management service instance
            log_callback: Function to call for logging
        """
        self.file_service = file_service
        self.db_service = db_service
        self.file_mgmt_service = file_mgmt_service
        self.log: Callable[[str], None] = log_callback

        # Processing flags to prevent double-click
        self.is_checking: bool = False  # Flag to prevent multiple check operations
        self.is_uploading: bool = False  # Flag to prevent multiple upload operations

        # Initialize Performance Optimizer for parallel processing
        self.perf_optimizer = PerformanceOptimizer(log_callback=log_callback)
        self.max_workers: int = min(4, os.cpu_count() or 1)  # Number of parallel workers
    
    def browse_excel_path(self, save_callback):
        """Select folder for file search"""
        folder = filedialog.askdirectory()
        if folder:
            self.file_service.set_search_path(folder)
            save_callback(folder)
            self.log(f"📁 Input folder updated: {folder}")
            messagebox.showinfo("Success", f"Set search path for Excel files to\n{folder}")
    
    def run_check_thread(self, ui_callbacks):
        """Start file checking in separate thread"""
        # ป้องกันการกดซ้ำขณะกำลัง check อยู่
        if self.is_checking:
            self.log("⚠️ File scan is already in progress, please wait...")
            return

        # ตั้งค่า flag ทันที
        self.is_checking = True

        # ปิดปุ่มทันทีเพื่อป้องกันการกดซ้ำ (ทำใน main thread ก่อน start thread)
        try:
            ui_callbacks['disable_controls']()
        except Exception:
            pass

        thread = threading.Thread(target=self._check_files, args=(ui_callbacks,))
        thread.start()
    
    def _check_files(self, ui_callbacks):
        """Check files in specified path"""
        try:
            # รีเซ็ต UI
            ui_callbacks['reset_progress']()
            ui_callbacks['set_progress_status']("Starting file scan", "Scanning folders...")

            # โหลดการตั้งค่าใหม่
            self.file_service.load_settings()
            ui_callbacks['clear_file_list']()
            ui_callbacks['reset_select_all']()

            # ค้นหาไฟล์ Excel/CSV
            ui_callbacks['update_progress'](0.2, "Searching for files", "Scanning .xlsx and .csv files...")
            data_files = self.file_service.find_data_files()

            if not data_files:
                ui_callbacks['update_progress'](1.0, "Scan completed", "No .xlsx or .csv files found")
                ui_callbacks['update_status']("No .xlsx or .csv files found in the specified folder", True)
                self.log("⚠️  No .xlsx or .csv files found in the specified folder")
                self.log("============  File scan completed ============")
                return

            found_files_count = 0
            total_files = len(data_files)

            for i, file in enumerate(data_files):
                # คำนวณ progress ที่ถูกต้อง (0.2 - 0.8)
                progress = 0.2 + (0.6 * (i / total_files))  # 20% - 80%
                ui_callbacks['update_progress'](progress, f"Checking file: {os.path.basename(file)}", f"File {i+1} of {total_files}")

                logic_type = self.file_service.detect_file_type(file)
                if logic_type:
                    found_files_count += 1
                    self.log(f"✅ Found matching file: {os.path.basename(file)} [{logic_type}]")
                    ui_callbacks['add_file_to_list'](file, logic_type)

            if found_files_count > 0:
                ui_callbacks['update_progress'](1.0, "Scan completed", f"Found {found_files_count} matching files")
                ui_callbacks['update_status'](f"Found {found_files_count} matching files", False)
                ui_callbacks['enable_select_all']()
            else:
                ui_callbacks['update_progress'](1.0, "Scan completed", "No matching files found")
                ui_callbacks['update_status']("No matching files found", True)
                ui_callbacks['reset_select_all']()

            self.log("============  File scan completed ============")

        except Exception as e:
            self.log(f"❌ An error occurred while scanning files: {e}")
        finally:
            # เปิดปุ่มกลับมาเมื่อเสร็จสิ้น
            ui_callbacks['enable_controls']()
            # ปล่อย flag
            self.is_checking = False
    
    def confirm_upload(self, get_selected_files_callback, ui_callbacks):
        """ยืนยันการอัปโหลดไฟล์ที่เลือก - with double-click protection"""
        # ป้องกันการกดซ้ำขณะกำลัง upload อยู่
        if self.is_uploading:
            self.log("⚠️ Upload is already in progress, please wait...")
            return

        selected = get_selected_files_callback()
        if not selected:
            messagebox.showwarning("No files", "Please select files to upload")
            return

        # โหลดการตั้งค่าใหม่ก่อนอัปโหลด เพื่อให้แน่ใจว่าใช้การตั้งค่าล่าสุด
        self.log("📥 Loading latest settings before upload...")
        self.file_service.load_settings()

        # ตรวจสอบการเชื่อมต่อฐานข้อมูล
        success, message = self.db_service.check_connection()
        if not success:
            messagebox.showerror(
                "Error",
                f"Cannot connect to database:\n{message}\n\nPlease check database settings first"
            )
            return

        # ตั้ง flag ก่อนแสดง confirmation dialog
        self.is_uploading = True

        answer = messagebox.askyesno(
            "Confirm Upload",
            f"Are you sure you want to upload the selected {len(selected)} files?"
        )

        if answer:
            ui_callbacks['reset_progress']()
            ui_callbacks['disable_controls']()
            thread = threading.Thread(target=self._upload_selected_files_wrapper, args=(selected, ui_callbacks))
            thread.start()
        else:
            # ถ้า cancel ให้ปลดล็อก flag
            self.is_uploading = False
            self.log("Upload cancelled by user")

    def _upload_selected_files_wrapper(self, selected_files, ui_callbacks):
        """Wrapper to reset upload flag after upload completes"""
        try:
            self._upload_selected_files(selected_files, ui_callbacks)
        finally:
            # Always reset flag, even if an exception occurred
            self.is_uploading = False

    def _group_files_by_type(self, selected_files: List[Tuple]) -> Dict[str, List[Tuple]]:
        """จัดกลุ่มไฟล์ตามประเภท (logic_type)"""
        files_by_type: Dict[str, List[Tuple]] = {}
        for (file_path, logic_type), chk in selected_files:
            if logic_type not in files_by_type:
                files_by_type[logic_type] = []
            files_by_type[logic_type].append((file_path, chk))
        return files_by_type

    def _init_upload_stats(self, start_time: float) -> Dict[str, Any]:
        """สร้าง initial upload statistics structure"""
        return {
            'total_start_time': start_time,
            'by_type': {},
            'errors': [],
            'successful_files': 0,
            'failed_files': 0,
            'processed_file_list': []
        }

    def _init_type_stats(self, files_count: int, start_time: float) -> Dict[str, Any]:
        """สร้าง statistics structure สำหรับแต่ละประเภทไฟล์"""
        return {
            'start_time': start_time,
            'files_count': files_count,
            'successful_files': 0,
            'failed_files': 0,
            'errors': [],
            'individual_processing_time': 0,
            'successful_file_list': [],
            'failed_file_list': []
        }

    def _validate_single_file(self, file_info):
        """
        Validate a single file (helper function for parallel processing)

        Args:
            file_info: Tuple of (file_path, logic_type)

        Returns:
            Dict with validation results
        """
        file_path, logic_type = file_info
        result = {
            'file_path': file_path,
            'logic_type': logic_type,
            'success': False,
            'df': None,
            'error': None
        }

        try:
            file_start_time = time.time()

            # Check file size for optimization decision
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)

            # Use performance optimizer for large files
            if file_size_mb > 50:
                self.log(f"🚀 Using optimized reader for large file: {os.path.basename(file_path)} ({file_size_mb:.1f} MB)")

                # Determine file type
                if file_path.lower().endswith('.csv'):
                    file_type = 'csv'
                elif file_path.lower().endswith('.xls'):
                    file_type = 'excel_xls'
                else:
                    file_type = 'excel'

                success, df = self.perf_optimizer.read_large_file_chunked(file_path, file_type)
                if not success:
                    result['error'] = "Failed to read large file"
                    return result
            else:
                # Standard reading for smaller files
                # First check columns
                success, preview_result, columns_info = self.file_service.preview_file_columns(file_path, logic_type)
                if not success:
                    result['error'] = f"Column check failed: {preview_result}"
                    return result

                # Read full file
                success, read_result = self.file_service.read_excel_file(file_path, logic_type)
                if not success:
                    result['error'] = f"Failed to read file: {read_result}"
                    return result

                df = read_result

            # Successful validation
            result['success'] = True
            result['df'] = df

            file_processing_time = time.time() - file_start_time
            self.log(f"✅ Validated: {os.path.basename(file_path)} ({file_processing_time:.1f}s)")

        except Exception as e:
            result['error'] = str(e)
            self.log(f"❌ Error validating {os.path.basename(file_path)}: {e}")

        return result

    def _upload_selected_files(self, selected_files, ui_callbacks):
        """
        อัปโหลดไฟล์ที่เลือกไปยัง SQL Server (Enhanced with parallel processing)

        แบ่งเป็น 2 phases:
        - Phase 1: อ่านและ validate ไฟล์แบบ parallel
        - Phase 2: อัปโหลดข้อมูลที่ validated แล้ว
        """
        upload_start_time = time.time()

        # จัดกลุ่มไฟล์และเตรียม stats
        files_by_type = self._group_files_by_type(selected_files)
        total_files = sum(len(files) for files in files_by_type.values())
        total_types = len(files_by_type)

        upload_stats = self._init_upload_stats(upload_start_time)

        # แสดงสถานะเริ่มต้น
        ui_callbacks['set_progress_status']("Starting upload", f"Found {total_files} files from {total_types} types")

        # Phase 1: Read and validate all files with PARALLEL PROCESSING
        self.log("📖 Phase 1: Reading and validating all files in parallel...")
        self.log(f"🚀 Using {self.max_workers} parallel workers for optimal performance")
        all_validated_data = {}  # {logic_type: (combined_df, files_info, required_cols)}
        
        completed_types = 0
        processed_files = 0

        for logic_type, files in files_by_type.items():
            try:
                # เริ่มจับเวลาสำหรับประเภทไฟล์นี้
                type_start_time = time.time()
                upload_stats['by_type'][logic_type] = self._init_type_stats(len(files), type_start_time)

                self.log(f"📖 Validating files of type {logic_type} ({len(files)} files)")

                # อัปเดต Progress Bar ตามความคืบหน้า
                progress = completed_types / total_types
                ui_callbacks['update_progress'](progress, f"Validating type {logic_type}", f"Type {completed_types + 1} of {total_types}")

                # รวมข้อมูลจากทุกไฟล์ในประเภทเดียวกัน
                all_dfs = []
                valid_files_info = []

                # PARALLEL FILE VALIDATION using ThreadPoolExecutor
                file_infos = [(file_path, logic_type) for file_path, chk in files]
                file_chks = {file_path: chk for file_path, chk in files}

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all validation tasks
                    future_to_file = {
                        executor.submit(self._validate_single_file, file_info): file_info
                        for file_info in file_infos
                    }

                    # Collect results as they complete
                    for future in as_completed(future_to_file):
                        file_info = future_to_file[future]
                        file_path, _ = file_info

                        try:
                            processed_files += 1
                            file_progress = (processed_files - 1) / total_files

                            # Get validation result
                            validation_result = future.result()

                            if validation_result['success']:
                                df = validation_result['df']
                                all_dfs.append(df)
                                valid_files_info.append((file_path, file_chks[file_path]))
                                upload_stats['by_type'][logic_type]['successful_files'] += 1
                                upload_stats['by_type'][logic_type]['successful_file_list'].append(os.path.basename(file_path))

                                # Update UI
                                ui_callbacks['update_progress'](
                                    file_progress,
                                    f"✅ Validated: {os.path.basename(file_path)}",
                                    f"File {processed_files} of {total_files}"
                                )
                            else:
                                error = validation_result['error']
                                self.log(f"❌ Validation failed for {os.path.basename(file_path)}: {error}")
                                upload_stats['by_type'][logic_type]['failed_files'] += 1
                                upload_stats['by_type'][logic_type]['failed_file_list'].append(os.path.basename(file_path))
                                upload_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {error}")
                                upload_stats['failed_files'] += 1

                                # Update UI
                                ui_callbacks['update_progress'](
                                    file_progress,
                                    f"❌ Failed: {os.path.basename(file_path)}",
                                    f"File {processed_files} of {total_files}"
                                )

                        except Exception as e:
                            error_msg = f"An error occurred while validating file {os.path.basename(file_path)}: {e}"
                            self.log(f"❌ {error_msg}")
                            upload_stats['by_type'][logic_type]['failed_files'] += 1
                            upload_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {str(e)}")
                            upload_stats['failed_files'] += 1

                # Calculate processing time for this type
                upload_stats['by_type'][logic_type]['individual_processing_time'] = time.time() - type_start_time
                
                if not all_dfs:
                    self.log(f"❌ No valid data from files of type {logic_type}")
                    completed_types += 1
                    continue
                
                # รวม DataFrame ทั้งหมด
                combined_df = pd.concat(all_dfs, ignore_index=True)
                
                # แสดงสถานะการรวมข้อมูล
                ui_callbacks['update_progress'](file_progress, f"Combining data for type {logic_type}", f"Combined {len(all_dfs)} files into {len(combined_df)} rows")
                
                # ใช้ dtype ที่ถูกต้อง
                required_cols = self.file_service.get_required_dtypes(logic_type)
                
                # ตรวจสอบว่า required_cols ไม่ว่างเปล่า
                if not required_cols:
                    self.log(f"❌ No data type configuration found for {logic_type}")
                    completed_types += 1
                    continue
                
                # ตรวจสอบว่าข้อมูลไม่ว่างเปล่า
                if combined_df.empty:
                    self.log(f"❌ No valid data from files of type {logic_type}")
                    completed_types += 1
                    continue
                
                # เก็บข้อมูลที่ผ่านการตรวจสอบแล้ว
                all_validated_data[logic_type] = (combined_df, valid_files_info, required_cols)
                self.log(f"✅ Prepared {len(combined_df)} rows for type {logic_type}")
                    
                completed_types += 1
                
            except Exception as e:
                error_msg = f"An error occurred while validating files of type {logic_type}: {e}"
                self.log(f"❌ {error_msg}")
                upload_stats['by_type'][logic_type]['errors'].append(error_msg)
                completed_types += 1
        
        # Phase 2: Upload all validated data (with proper table clearing sequence)
        if all_validated_data:
            self.log("📤 Phase 2: Uploading all validated data...")
            upload_count = 0
            total_uploads = len(all_validated_data)
            
            for logic_type, (combined_df, valid_files_info, required_cols) in all_validated_data.items():
                try:
                    # จับเวลาเริ่มต้น Phase 2 สำหรับประเภทไฟล์นี้
                    phase2_start_time = time.time()
                    
                    upload_progress = upload_count / total_uploads
                    ui_callbacks['update_progress'](upload_progress, f"Uploading data for type {logic_type}", f"Upload {upload_count + 1} of {total_uploads}")
                    
                    self.log(f"📊 Uploading {len(combined_df)} rows for type {logic_type}")
                    
                    # Clear existing data only for the first upload of each table
                    success, message = self.db_service.upload_data(
                        combined_df, logic_type, required_cols, 
                        log_func=self.log, clear_existing=True
                    )
                    
                    if success:
                        self.log(f"✅ {message}")

                        # เก็บ summary message ไว้แสดงใน report
                        upload_stats['by_type'][logic_type]['summary_message'] = message

                        upload_stats['successful_files'] += len(valid_files_info)
                        for file_path, chk in valid_files_info:
                            ui_callbacks['disable_checkbox'](chk)
                            ui_callbacks['set_file_uploaded'](file_path)
                            # ย้ายไฟล์ทันทีหลังอัปโหลดสำเร็จ
                            try:
                                move_success, move_result = self.file_service.move_uploaded_files([file_path], [logic_type])
                                if move_success:
                                    for original_path, new_path in move_result:
                                        self.log(f"📦 Moved file to: {new_path}")
                                else:
                                    self.log(f"❌ Could not move file: {move_result}")
                            except Exception as move_error:
                                self.log(f"❌ An error occurred while moving file: {move_error}")
                    else:
                        # แสดงเฉพาะข้อความสรุปจากบริการฐานข้อมูล ไม่พิมพ์รายการคอลัมน์ทั้งหมด
                        # ตรวจสอบว่า message เป็น dict หรือ string
                        if isinstance(message, dict):
                            summary = message.get('summary', 'Upload failed')
                            validation_issues = message.get('issues', [])
                            validation_warnings = message.get('warnings', [])

                            self.log(f"❌ {summary}")
                            upload_stats['by_type'][logic_type]['errors'].append(f"Database upload failed: {summary}")
                            upload_stats['by_type'][logic_type]['validation_details'] = {
                                'issues': validation_issues,
                                'warnings': validation_warnings
                            }
                        else:
                            self.log(f"❌ {message}")
                            upload_stats['by_type'][logic_type]['errors'].append(f"Database upload failed: {message}")

                        upload_stats['failed_files'] += len(valid_files_info)

                        # ย้ายไฟล์จาก successful_file_list ไปยัง failed_file_list
                        for file_path, chk in valid_files_info:
                            filename = os.path.basename(file_path)
                            # ลบออกจาก successful_file_list ถ้ามี
                            if filename in upload_stats['by_type'][logic_type]['successful_file_list']:
                                upload_stats['by_type'][logic_type]['successful_file_list'].remove(filename)
                                upload_stats['by_type'][logic_type]['successful_files'] -= 1
                            # เพิ่มเข้าไปใน failed_file_list
                            if filename not in upload_stats['by_type'][logic_type]['failed_file_list']:
                                upload_stats['by_type'][logic_type]['failed_file_list'].append(filename)
                                upload_stats['by_type'][logic_type]['failed_files'] += 1
                        
                    upload_count += 1
                    
                    # คำนวณเวลา Phase 2 และรวมเข้าไปใน individual_processing_time
                    phase2_time = time.time() - phase2_start_time
                    if 'individual_processing_time' in upload_stats['by_type'][logic_type]:
                        upload_stats['by_type'][logic_type]['individual_processing_time'] += phase2_time
                        upload_stats['by_type'][logic_type]['processing_time'] = upload_stats['by_type'][logic_type]['individual_processing_time']
                    
                except Exception as e:
                    error_msg = f"An error occurred while uploading data for type {logic_type}: {e}"
                    self.log(f"❌ {error_msg}")
                    upload_stats['by_type'][logic_type]['errors'].append(error_msg)
                    upload_count += 1
                    
                    # คำนวณเวลา Phase 2 แม้เมื่อมีข้อผิดพลาดและรวมเข้าไปใน individual_processing_time
                    phase2_time = time.time() - phase2_start_time
                    if 'individual_processing_time' in upload_stats['by_type'][logic_type]:
                        upload_stats['by_type'][logic_type]['individual_processing_time'] += phase2_time
                        upload_stats['by_type'][logic_type]['processing_time'] = upload_stats['by_type'][logic_type]['individual_processing_time']
        else:
            self.log("❌ No validated data to upload")
        
        # คำนวณเวลารวม
        total_upload_time = time.time() - upload_start_time
        upload_stats['total_time'] = total_upload_time
        
        # อัปเดต progress เป็น 100% เมื่อเสร็จสิ้น
        ui_callbacks['update_progress'](1.0, "Upload completed", f"Processed {total_files} files successfully")
        
        # แสดงรายงานสรุป
        self._display_upload_summary(upload_stats, total_files)
        
        # เปิดปุ่มทั้งหมดกลับมา
        ui_callbacks['enable_controls']()
    
    def _display_processing_summary(self, stats, total_files, operation_type="Upload"):
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

        self.log(f"📊 Total {operation_type} Time: {time_str}")
        self.log(f"📁 Total Files Processed: {total_files}")

        # แสดงสถิติเฉพาะที่มีค่ามากกว่า 0
        successful_files = stats.get('successful_files', 0)
        failed_files = stats.get('failed_files', 0)

        if successful_files > 0:
            self.log(f"✅ Successful: {successful_files}")
        if failed_files > 0:
            self.log(f"❌ Failed: {failed_files}")

        # รายละเอียดแต่ละประเภทไฟล์
        if stats.get('by_type'):
            self._display_file_type_details(stats, operation_type)

        # สรุปสำคัญ
        self._display_final_summary(stats, total_files, operation_type)

        self.log("=" * 42)

    def _display_file_type_details(self, stats, operation_type):
        """แสดงรายละเอียดแต่ละประเภทไฟล์"""
        self.log("")
        self.log("📋 Details by File Type (Occupation):")
        self.log("-" * 50)

        for file_type, type_stats in stats['by_type'].items():
            # แสดง header ของ file type
            type_time = type_stats.get('processing_time', 0)
            type_time_str = format_elapsed_time(type_time)

            self.log(f"🏷️  Occupation: {file_type}")
            self.log(f"   ⏱️  Processing Time: {type_time_str}")
            self.log(f"   📁 Total Files: {type_stats.get('files_count', 0)}")

            # แสดงผลสำเร็จ
            self._display_successful_files(type_stats, operation_type)

            # แสดงผลล้มเหลว
            self._display_failed_files(type_stats)

            self.log("")

    def _display_successful_files(self, type_stats, operation_type):
        """แสดงรายละเอียดไฟล์ที่สำเร็จ"""
        successful = type_stats.get('successful_files', 0)
        if successful <= 0:
            return

        self.log(f"   ✅ Successful: {successful}")

        # แสดง summary message (มีเฉพาะ Upload operation)
        summary_message = type_stats.get('summary_message', '')
        if summary_message and operation_type == "Upload":
            self.log(f"   📋 Upload Summary:")
            self.log(f"      {summary_message}")

        # แสดงรายชื่อไฟล์ที่สำเร็จ
        successful_file_list = type_stats.get('successful_file_list', [])
        if successful_file_list:
            self.log(f"      Files:")
            for filename in successful_file_list:
                self.log(f"         • {filename}")

    def _display_failed_files(self, type_stats):
        """แสดงรายละเอียดไฟล์ที่ล้มเหลว"""
        failed = type_stats.get('failed_files', 0)
        if failed <= 0:
            return

        self.log(f"   ❌ Failed: {failed}")

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

    def _display_validation_details(self, validation_details):
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
                self.log(f"         ❌ {column}: {error_count:,} invalid rows ({percentage}%) Examples: {examples}")

        if warnings:
            self.log(f"      Validation Warnings:")
            for warning in warnings:
                column = warning.get('column', 'Unknown')
                error_count = warning.get('error_count', 0)
                percentage = warning.get('percentage', 0)
                examples = warning.get('examples', '')
                self.log(f"         ⚠️  {column}: {error_count:,} invalid rows ({percentage}%) Examples: {examples}")

    def _display_final_summary(self, stats, total_files, operation_type):
        """แสดงสรุปสุดท้าย"""
        success_rate = 0
        if total_files > 0:
            success_rate = (stats.get('successful_files', 0) / total_files) * 100

        self.log("📈 Summary:")
        self.log(f"   Success Rate: {success_rate:.1f}%")

        if stats.get('failed_files', 0) > 0:
            action = "upload" if operation_type == "Upload" else "process"
            self.log(f"   ⚠️  Some files failed to {action}. Check the errors above for details.")
        else:
            action = "uploaded" if operation_type == "Upload" else "processed"
            self.log(f"   🎉 All files {action} successfully!")

    def _display_upload_summary(self, upload_stats, total_files):
        """แสดงรายงานสรุปการอัปโหลด (wrapper for backward compatibility)"""
        self._display_processing_summary(upload_stats, total_files, "Upload")
    
    def _display_auto_process_summary(self, process_stats, total_files):
        """แสดงรายงานสรุปการประมวลผลอัตโนมัติ (wrapper for backward compatibility)"""
        self._display_processing_summary(process_stats, total_files, "Processing")
    
    def start_auto_process(self, load_input_folder_callback, column_settings):
        """เริ่มการประมวลผลอัตโนมัติ (ประมวลผลไฟล์)"""
        # ตรวจสอบว่ามีโฟลเดอร์ต้นทางหรือไม่
        input_folder_path = load_input_folder_callback()
        if not input_folder_path or not os.path.isdir(input_folder_path):
            messagebox.showerror(
                "Error",
                f"Invalid source folder: {input_folder_path}\n\nPlease select a source folder first"
            )
            return

        # โหลดการตั้งค่าใหม่ก่อนประมวลผล เพื่อให้แน่ใจว่าใช้การตั้งค่าล่าสุด
        self.file_service.load_settings()

        # ตรวจสอบการเชื่อมต่อฐานข้อมูล
        success, message = self.db_service.check_connection()
        if not success:
            messagebox.showerror(
                "Error",
                f"Cannot connect to database:\n{message}\n\nPlease check database settings first"
            )
            return


        # ตรวจสอบการตั้งค่าประเภทไฟล์
        if not column_settings:
            messagebox.showerror(
                "Error",
                "No file type configuration found\n\nPlease go to Settings tab and add file types first"
            )
            return

        # ยืนยันการทำงาน
        result = messagebox.askyesno(
            "Confirm Auto Processing",
            f"Will perform auto processing in folder:\n{input_folder_path}\n\n"
            "Processing steps:\n"
            "1. Find all data files\n"
            "2. Process and upload all files\n"
            "Do you want to proceed?"
        )

        if not result:
            return

        return input_folder_path  # Return path for further processing
    
    def run_auto_process(self, folder_path, ui_callbacks):
        """รันการประมวลผลอัตโนมัติใน thread แยก"""
        try:
            # ปิดปุ่มต่างๆ ระหว่างการทำงาน
            ui_callbacks['disable_controls']()
            
            # รีเซ็ต progress bar และแสดงสถานะเริ่มต้น
            ui_callbacks['reset_progress']()
            ui_callbacks['set_progress_status']("Starting auto processing", "Preparing system...")
            
            self.log("🤖 Starting auto processing")
            self.log(f"📁 Source folder: {folder_path}")
            
            # === ประมวลผลไฟล์หลัก ===
            self.log("========= Processing files ==========")
            self._auto_process_main_files(folder_path, ui_callbacks)
            
            self.log("==== Auto processing completed ======") 
            ui_callbacks['update_progress'](1.0, "Auto processing completed", "All steps completed successfully")
            messagebox.showinfo("Success", "Auto processing completed successfully")
            
        except Exception as e:
            self.log(f"❌ An error occurred during auto processing: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")
        finally:
            # เปิดปุ่มกลับมา
            ui_callbacks['enable_controls']()
    
    def _record_file_error(self, process_stats, logic_type, file_path, error_msg, file_start_time):
        """บันทึก error และเวลาที่ใช้สำหรับไฟล์ที่ล้มเหลว"""
        basename = os.path.basename(file_path)

        process_stats['by_type'][logic_type]['failed_files'] += 1
        process_stats['by_type'][logic_type]['failed_file_list'].append(basename)
        process_stats['by_type'][logic_type]['errors'].append(f"{basename}: {error_msg}")
        process_stats['failed_files'] += 1

        # คำนวณและบันทึกเวลาที่ใช้
        file_processing_time = time.time() - file_start_time
        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time

        self.log(f"❌ {error_msg}")

    def _record_file_success(self, process_stats, logic_type, file_path, file_start_time):
        """บันทึกความสำเร็จและเวลาที่ใช้สำหรับไฟล์"""
        basename = os.path.basename(file_path)

        process_stats['by_type'][logic_type]['successful_files'] += 1
        process_stats['by_type'][logic_type]['successful_file_list'].append(basename)
        process_stats['successful_files'] += 1

        # คำนวณและบันทึกเวลาที่ใช้
        file_processing_time = time.time() - file_start_time
        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time

    def _process_single_file(self, file_path, logic_type, process_stats, ui_callbacks, file_index, total_files):
        """
        ประมวลผลไฟล์เดียว - อ่าน validate และอัปโหลด

        Returns:
            bool: True if successful, False otherwise
        """
        file_start_time = time.time()
        basename = os.path.basename(file_path)

        # อัปเดตความคืบหน้า
        progress = (file_index - 1) / total_files
        ui_callbacks['update_progress'](progress, f"Processing file: {basename}", f"File {file_index} of {total_files}")

        self.log(f"📁 Processing file: {basename}")

        # ตรวจสอบคอลัมน์ก่อน
        success, result, _ = self.file_service.preview_file_columns(file_path, logic_type)
        if not success:
            self._record_file_error(process_stats, logic_type, file_path, f"Column check failed: {result}", file_start_time)
            return False

        # อ่านไฟล์เต็ม
        success, result = self.file_service.read_excel_file(file_path, logic_type)
        if not success:
            self._record_file_error(process_stats, logic_type, file_path, f"Could not read file: {result}", file_start_time)
            return False

        df = result

        # ตรวจสอบว่าข้อมูลไม่ว่าง
        if df.empty:
            self._record_file_error(process_stats, logic_type, file_path, "File has no data", file_start_time)
            return False

        # ดึง required columns
        required_cols = self.file_service.get_required_dtypes(logic_type)
        if not required_cols:
            self._record_file_error(process_stats, logic_type, file_path, f"No data type configuration found for {logic_type}", file_start_time)
            return False

        # อัปโหลดข้อมูล
        self.log(f"📊 Uploading {len(df)} rows for type {logic_type}")
        success, message = self.db_service.upload_data(df, logic_type, required_cols, log_func=self.log, clear_existing=True)

        if success:
            self.log(f"✅ Upload successful: {message}")
            self._record_file_success(process_stats, logic_type, file_path, file_start_time)

            # ย้ายไฟล์หลังอัปโหลดสำเร็จ
            self._move_uploaded_file(file_path, logic_type)
            return True
        else:
            # จัดการ upload failure
            self._handle_upload_failure(process_stats, logic_type, file_path, message, file_start_time)
            return False

    def _move_uploaded_file(self, file_path, logic_type):
        """ย้ายไฟล์ที่อัปโหลดสำเร็จแล้ว"""
        try:
            move_success, move_result = self.file_service.move_uploaded_files([file_path], [logic_type])
            if move_success:
                for original_path, new_path in move_result:
                    self.log(f"📦 Moved file to: {new_path}")
            else:
                self.log(f"❌ Could not move file: {move_result}")
        except Exception as move_error:
            self.log(f"❌ An error occurred while moving file: {move_error}")

    def _handle_upload_failure(self, process_stats, logic_type, file_path, message, file_start_time):
        """จัดการกรณี upload ล้มเหลว"""
        basename = os.path.basename(file_path)

        if isinstance(message, dict):
            summary = message.get('summary', 'Upload failed')
            validation_issues = message.get('issues', [])
            validation_warnings = message.get('warnings', [])

            error_msg = f"Upload failed: {summary}"
            process_stats['by_type'][logic_type]['validation_details'] = {
                'issues': validation_issues,
                'warnings': validation_warnings
            }
        else:
            error_msg = f"Upload failed: {message}"

        self._record_file_error(process_stats, logic_type, file_path, error_msg, file_start_time)

    def _detect_file_logic_type(self, file_path):
        """ตรวจหา logic_type ของไฟล์"""
        logic_type = self.file_service.detect_file_type(file_path)
        if logic_type:
            return logic_type

        # ลองเดาจากชื่อไฟล์
        filename = os.path.basename(file_path).lower()
        for key in self.file_service.column_settings.keys():
            if key.lower() in filename:
                return key

        return None

    def _auto_process_main_files(self, folder_path, ui_callbacks):
        """ประมวลผลไฟล์หลักอัตโนมัติ (Refactored)"""
        try:
            process_start_time = time.time()

            # ตั้ง search path และค้นหาไฟล์
            self.file_service.set_search_path(folder_path)
            data_files = self.file_service.find_data_files()

            if not data_files:
                self.log("No data files found in source folder")
                return

            self.log(f"Found {len(data_files)} data files, starting processing...")

            total_files = len(data_files)
            process_stats = self._init_upload_stats(process_start_time)

            # ประมวลผลแต่ละไฟล์
            for file_index, file_path in enumerate(data_files, start=1):
                try:
                    # ตรวจหา logic_type
                    logic_type = self._detect_file_logic_type(file_path)
                    if not logic_type:
                        error_msg = f"Could not identify file type: {os.path.basename(file_path)}"
                        self.log(f"❌ {error_msg}")
                        process_stats['failed_files'] += 1
                        process_stats['errors'].append(f"{os.path.basename(file_path)}: {error_msg}")
                        continue

                    # เตรียม stats สำหรับ type นี้ถ้ายังไม่มี
                    if logic_type not in process_stats['by_type']:
                        process_stats['by_type'][logic_type] = self._init_type_stats(0, time.time())

                    process_stats['by_type'][logic_type]['files_count'] += 1
                    self.log(f"📋 Identified file type: {logic_type}")

                    # ประมวลผลไฟล์โดยใช้ helper method
                    self._process_single_file(file_path, logic_type, process_stats, ui_callbacks, file_index, total_files)

                except Exception as e:
                    error_msg = f"An error occurred while processing {os.path.basename(file_path)}: {e}"
                    self.log(f"❌ {error_msg}")
                    if logic_type and logic_type in process_stats['by_type']:
                        process_stats['by_type'][logic_type]['failed_files'] += 1
                        process_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {str(e)}")
                    process_stats['failed_files'] += 1
            
            # ใช้เวลารวมที่คำนวณแยกสำหรับแต่ละประเภท
            for logic_type in process_stats['by_type']:
                if 'individual_processing_time' in process_stats['by_type'][logic_type]:
                    process_stats['by_type'][logic_type]['processing_time'] = process_stats['by_type'][logic_type]['individual_processing_time']
            
            # คำนวณเวลารวม
            process_stats['total_time'] = time.time() - process_start_time
            
            # อัปเดต progress เป็น 100% เมื่อเสร็จสิ้น
            ui_callbacks['update_progress'](1.0, "Processing completed", f"Successfully processed {successful_uploads} of {total_files} files")
            
            # แสดงรายงานสรุป
            self._display_auto_process_summary(process_stats, total_files)
            
            # ล้าง list ไฟล์หลังจากประมวลผลเสร็จ เหมือนการอัปโหลดปกติ
            ui_callbacks['clear_file_list']()
            ui_callbacks['reset_select_all']()
            
        except Exception as e:
            self.log(f"❌ An error occurred while processing files: {e}")
    
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
                self.log("⚠️ Cannot export logs: No valid log folder configured")
                return

            # ตั้งค่า file logging และส่งออก
            log_file_path = setup_file_logging(log_folder_path, enable_export=True)
            if log_file_path:
                self.log(f"📋 Log exported to: {log_file_path}")

                # จัดการไฟล์ log เก่า (ลบไฟล์ที่เก่าเกิน retention period)
                retention_days = app_settings.get('log_retention_days', 30)
                deleted_count = cleanup_old_log_files(log_folder_path, retention_days)

                # แสดงผลการ cleanup เฉพาะเมื่อมีการลบไฟล์
                if deleted_count > 0:
                    self.log(f"🧹 Cleaned up {deleted_count} old log files (older than {retention_days} days)")
            else:
                self.log("⚠️ Failed to export log file")

        except Exception as e:
            self.log(f"❌ Error during auto export logs: {e}")
