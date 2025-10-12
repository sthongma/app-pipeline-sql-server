"""File Operation Handlers"""
import os
import threading
import time
from datetime import datetime
from tkinter import messagebox, filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from utils.logger import setup_file_logging, cleanup_old_log_files
from config.json_manager import json_manager
from performance_optimizations import PerformanceOptimizer


class FileHandler:
    def __init__(self, file_service, db_service, file_mgmt_service, log_callback):
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
        self.log = log_callback
        self.is_checking = False  # Flag to prevent multiple check operations

        # Initialize Performance Optimizer for parallel processing
        self.perf_optimizer = PerformanceOptimizer(log_callback=log_callback)
        self.max_workers = min(4, os.cpu_count() or 1)  # Number of parallel workers
    
    def browse_excel_path(self, save_callback):
        """Select folder for file search"""
        folder = filedialog.askdirectory()
        if folder:
            self.file_service.set_search_path(folder)
            save_callback(folder)
            self.log(f"📂 Input folder updated: {folder}")
            messagebox.showinfo("Success", f"Set search path for Excel files to\n{folder}")
    
    def run_check_thread(self, ui_callbacks):
        """Start file checking in separate thread"""
        # ป้องกันการกดซ้ำขณะกำลัง check อยู่
        if self.is_checking:
            self.log("⚠️ File scan is already in progress, please wait...")
            messagebox.showwarning("In Progress", "File scan is already in progress.\nPlease wait for it to complete.")
            return

        thread = threading.Thread(target=self._check_files, args=(ui_callbacks,))
        thread.start()
    
    def _check_files(self, ui_callbacks):
        """Check files in specified path"""
        # ตั้งค่า flag ว่ากำลัง check อยู่
        self.is_checking = True

        try:
            # รีเซ็ต UI
            ui_callbacks['reset_progress']()
            ui_callbacks['set_progress_status']("Starting file scan", "Scanning folders...")

            # ปิดปุ่ม check ระหว่างการทำงาน
            ui_callbacks['disable_controls']()

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
                self.log("🤷 No .xlsx or .csv files found in the specified folder")
                self.log("--- 🏁 File scan completed ---")
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

            self.log("--- 🏁 File scan completed ---")

        except Exception as e:
            self.log(f"❌ An error occurred while scanning files: {e}")
        finally:
            # เปิดปุ่มกลับมาเมื่อเสร็จสิ้น
            ui_callbacks['enable_controls']()
            # ปล่อย flag
            self.is_checking = False
    
    def confirm_upload(self, get_selected_files_callback, ui_callbacks):
        """ยืนยันการอัปโหลดไฟล์ที่เลือก"""
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
            
            
            
        answer = messagebox.askyesno(
            "Confirm Upload",
            f"Are you sure you want to upload the selected {len(selected)} files?"
        )
        
        if answer:
            ui_callbacks['reset_progress']()
            ui_callbacks['disable_controls']()
            thread = threading.Thread(target=self._upload_selected_files, args=(selected, ui_callbacks))
            thread.start()
    
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
        """อัปโหลดไฟล์ที่เลือกไปยัง SQL Server (Enhanced with parallel processing)"""
        # เริ่มจับเวลา
        upload_start_time = time.time()

        # จัดกลุ่มไฟล์ตาม logic_type
        files_by_type = {}
        for (file_path, logic_type), chk in selected_files:
            if logic_type not in files_by_type:
                files_by_type[logic_type] = []
            files_by_type[logic_type].append((file_path, chk))

        total_types = len(files_by_type)
        completed_types = 0
        total_files = sum(len(files) for files in files_by_type.values())
        processed_files = 0

        # สถิติการอัปโหลด
        upload_stats = {
            'total_start_time': upload_start_time,
            'by_type': {},
            'errors': [],
            'successful_files': 0,
            'failed_files': 0,
            'processed_file_list': []  # เก็บรายชื่อไฟล์ที่ประมวลผลทั้งหมด
        }

        # แสดงสถานะเริ่มต้น
        ui_callbacks['set_progress_status']("Starting upload", f"Found {total_files} files from {total_types} types")

        # Phase 1: Read and validate all files with PARALLEL PROCESSING
        self.log("📖 Phase 1: Reading and validating all files in parallel...")
        self.log(f"🚀 Using {self.max_workers} parallel workers for optimal performance")
        all_validated_data = {}  # {logic_type: (combined_df, files_info, required_cols)}
        
        for logic_type, files in files_by_type.items():
            try:
                # เริ่มจับเวลาสำหรับประเภทไฟล์นี้
                type_start_time = time.time()
                upload_stats['by_type'][logic_type] = {
                    'start_time': type_start_time,
                    'files_count': len(files),
                    'successful_files': 0,
                    'failed_files': 0,
                    'errors': [],
                    'individual_processing_time': 0,  # เก็บเวลารวมของประเภทนี้
                    'successful_file_list': [],  # เก็บชื่อไฟล์ที่สำเร็จ
                    'failed_file_list': []  # เก็บชื่อไฟล์ที่ล้มเหลว
                }

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
                                        self.log(f"📦 Moved file to: {os.path.basename(new_path)}")
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
    
    def _display_upload_summary(self, upload_stats, total_files):
        """แสดงรายงานสรุปการอัปโหลด"""
        self.log("========= Upload Summary Report ==========")

        # เรียกใช้ระบบส่งออก log อัตโนมัติ
        self._auto_export_logs()

        # เวลารวม
        total_time = upload_stats.get('total_time', 0)
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = int(total_time % 60)

        if hours > 0:
            time_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"

        self.log(f"📊 Total Upload Time: {time_str}")
        self.log(f"📁 Total Files Processed: {total_files}")

        # แสดงสถิติเฉพาะที่มีค่ามากกว่า 0
        successful_files = upload_stats.get('successful_files', 0)
        failed_files = upload_stats.get('failed_files', 0)

        if successful_files > 0:
            self.log(f"✅ Successful: {successful_files}")
        if failed_files > 0:
            self.log(f"❌ Failed: {failed_files}")

        # รายละเอียดแต่ละประเภทไฟล์
        if upload_stats.get('by_type'):
            self.log("")
            self.log("📋 Details by File Type (Occupation):")
            self.log("-" * 50)

            for file_type, stats in upload_stats['by_type'].items():
                type_time = stats.get('processing_time', 0)
                type_hours = int(type_time // 3600)
                type_minutes = int((type_time % 3600) // 60)
                type_seconds = int(type_time % 60)

                if type_hours > 0:
                    type_time_str = f"{type_hours}h {type_minutes}m {type_seconds}s"
                elif type_minutes > 0:
                    type_time_str = f"{type_minutes}m {type_seconds}s"
                else:
                    type_time_str = f"{type_seconds}s"

                self.log(f"🏷️  Occupation: {file_type}")
                self.log(f"   ⏱️  Processing Time: {type_time_str}")
                self.log(f"   📂 Total Files: {stats.get('files_count', 0)}")

                # แสดงสถิติเฉพาะที่มีค่ามากกว่า 0
                successful = stats.get('successful_files', 0)
                failed = stats.get('failed_files', 0)

                if successful > 0:
                    self.log(f"   ✅ Successful: {successful}")

                    # แสดง summary message ที่มีข้อมูล deduplication
                    summary_message = stats.get('summary_message', '')
                    if summary_message:
                        self.log(f"   📋 Upload Summary:")
                        self.log(f"      {summary_message}")

                    # แสดงรายชื่อไฟล์ที่สำเร็จ
                    successful_file_list = stats.get('successful_file_list', [])
                    if successful_file_list:
                        self.log(f"      Files:")
                        for filename in successful_file_list:
                            self.log(f"         • {filename}")

                if failed > 0:
                    self.log(f"   ❌ Failed: {failed}")
                    # แสดงรายชื่อไฟล์ที่ล้มเหลวพร้อมรายละเอียด error
                    failed_file_list = stats.get('failed_file_list', [])
                    errors = stats.get('errors', [])
                    validation_details = stats.get('validation_details', {})

                    if failed_file_list:
                        self.log(f"      Files with error details:")
                        # แสดงไฟล์แต่ละไฟล์พร้อมกับ error message
                        for filename in failed_file_list:
                            self.log(f"         • {filename}")
                            # หา error ที่ตรงกับไฟล์นี้
                            matching_errors = [err for err in errors if filename in err or 'Database upload failed' in err]
                            if matching_errors:
                                for err in matching_errors:
                                    # แยก error message ออกจากชื่อไฟล์
                                    if ': ' in err:
                                        error_detail = err.split(': ', 1)[-1]
                                    else:
                                        error_detail = err
                                    self.log(f"           ↳ {error_detail}")
                            else:
                                self.log(f"           ↳ Unknown error")

                    # แสดงรายละเอียด validation issues
                    if validation_details:
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

                self.log("")

        # สรุปสำคัญ
        success_rate = 0
        if total_files > 0:
            success_rate = (upload_stats.get('successful_files', 0) / total_files) * 100
        
        self.log("📈 Summary:")
        self.log(f"   Success Rate: {success_rate:.1f}%")
        
        if upload_stats.get('failed_files', 0) > 0:
            self.log("   ⚠️  Some files failed to upload. Check the errors above for details.")
        else:
            self.log("   🎉 All files uploaded successfully!")
        
        self.log("=========================================")
    
    def _display_auto_process_summary(self, process_stats, total_files):
        """แสดงรายงานสรุปการประมวลผลอัตโนมัติ"""
        self.log("======= Auto Process Summary Report =======")

        # เรียกใช้ระบบส่งออก log อัตโนมัติ
        self._auto_export_logs()

        # เวลารวม
        total_time = process_stats.get('total_time', 0)
        hours = int(total_time // 3600)
        minutes = int((total_time % 3600) // 60)
        seconds = int(total_time % 60)

        if hours > 0:
            time_str = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{seconds}s"

        self.log(f"📊 Total Processing Time: {time_str}")
        self.log(f"📁 Total Files Processed: {total_files}")

        # แสดงสถิติเฉพาะที่มีค่ามากกว่า 0
        successful_files = process_stats.get('successful_files', 0)
        failed_files = process_stats.get('failed_files', 0)

        if successful_files > 0:
            self.log(f"✅ Successful: {successful_files}")
        if failed_files > 0:
            self.log(f"❌ Failed: {failed_files}")

        # รายละเอียดแต่ละประเภทไฟล์
        if process_stats.get('by_type'):
            self.log("")
            self.log("📋 Details by File Type (Occupation):")
            self.log("-" * 50)

            for file_type, stats in process_stats['by_type'].items():
                type_time = stats.get('processing_time', 0)
                type_hours = int(type_time // 3600)
                type_minutes = int((type_time % 3600) // 60)
                type_seconds = int(type_time % 60)

                if type_hours > 0:
                    type_time_str = f"{type_hours}h {type_minutes}m {type_seconds}s"
                elif type_minutes > 0:
                    type_time_str = f"{type_minutes}m {type_seconds}s"
                else:
                    type_time_str = f"{type_seconds}s"

                self.log(f"🏷️  Occupation: {file_type}")
                self.log(f"   ⏱️  Processing Time: {type_time_str}")
                self.log(f"   📂 Total Files: {stats.get('files_count', 0)}")

                # แสดงสถิติเฉพาะที่มีค่ามากกว่า 0
                successful = stats.get('successful_files', 0)
                failed = stats.get('failed_files', 0)

                if successful > 0:
                    self.log(f"   ✅ Successful: {successful}")
                    # แสดงรายชื่อไฟล์ที่สำเร็จ
                    successful_file_list = stats.get('successful_file_list', [])
                    if successful_file_list:
                        self.log(f"      Files:")
                        for filename in successful_file_list:
                            self.log(f"         • {filename}")

                if failed > 0:
                    self.log(f"   ❌ Failed: {failed}")
                    # แสดงรายชื่อไฟล์ที่ล้มเหลวพร้อมรายละเอียด error
                    failed_file_list = stats.get('failed_file_list', [])
                    errors = stats.get('errors', [])
                    validation_details = stats.get('validation_details', {})

                    if failed_file_list:
                        self.log(f"      Files with error details:")
                        # แสดงไฟล์แต่ละไฟล์พร้อมกับ error message
                        for filename in failed_file_list:
                            self.log(f"         • {filename}")
                            # หา error ที่ตรงกับไฟล์นี้
                            matching_errors = [err for err in errors if filename in err or 'Upload failed' in err]
                            if matching_errors:
                                for err in matching_errors:
                                    # แยก error message ออกจากชื่อไฟล์
                                    if ': ' in err:
                                        error_detail = err.split(': ', 1)[-1]
                                    else:
                                        error_detail = err
                                    self.log(f"           ↳ {error_detail}")
                            else:
                                self.log(f"           ↳ Unknown error")

                    # แสดงรายละเอียด validation issues
                    if validation_details:
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

                self.log("")

        # สรุปสำคัญ
        success_rate = 0
        if total_files > 0:
            success_rate = (process_stats.get('successful_files', 0) / total_files) * 100

        self.log("📈 Summary:")
        self.log(f"   Success Rate: {success_rate:.1f}%")
        
        if process_stats.get('failed_files', 0) > 0:
            self.log("   ⚠️  Some files failed to process. Check the errors above for details.")
        else:
            self.log("   🎉 All files processed successfully!")
        
        self.log("==========================================")
    
    def start_auto_process(self, load_last_path_callback, column_settings):
        """เริ่มการประมวลผลอัตโนมัติ (ประมวลผลไฟล์)"""
        # ตรวจสอบว่ามีโฟลเดอร์ต้นทางหรือไม่
        last_path = load_last_path_callback()
        if not last_path or not os.path.isdir(last_path):
            messagebox.showerror(
                "Error",
                f"Invalid source folder: {last_path}\n\nPlease select a source folder first"
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
            f"Will perform auto processing in folder:\n{last_path}\n\n"
            "Processing steps:\n"
            "1. Find all data files\n"
            "2. Process and upload all files\n"
            "Do you want to proceed?"
        )
        
        if not result:
            return
        
        return last_path  # Return path for further processing
    
    def run_auto_process(self, folder_path, ui_callbacks):
        """รันการประมวลผลอัตโนมัติใน thread แยก"""
        try:
            # ปิดปุ่มต่างๆ ระหว่างการทำงาน
            ui_callbacks['disable_controls']()
            
            # รีเซ็ต progress bar และแสดงสถานะเริ่มต้น
            ui_callbacks['reset_progress']()
            ui_callbacks['set_progress_status']("Starting auto processing", "Preparing system...")
            
            self.log("🤖 Starting auto processing")
            self.log(f"📂 Source folder: {folder_path}")
            
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
    
    def _auto_process_main_files(self, folder_path, ui_callbacks):
        """ประมวลผลไฟล์หลักอัตโนมัติ"""
        try:
            # เริ่มจับเวลา
            process_start_time = time.time()
            
            # ตั้ง search path ใหม่
            self.file_service.set_search_path(folder_path)
            
            # ค้นหาไฟล์ข้อมูล
            data_files = self.file_service.find_data_files()
            
            if not data_files:
                self.log("No data files found in source folder")
                return
            
            self.log(f"Found {len(data_files)} data files, starting processing...")
            
            total_files = len(data_files)
            processed_files = 0
            successful_uploads = 0
            
            # สถิติการประมวลผล
            process_stats = {
                'start_time': process_start_time,
                'by_type': {},
                'errors': [],
                'successful_files': 0,
                'failed_files': 0,
                'processed_file_list': []  # เก็บรายชื่อไฟล์ที่ประมวลผลทั้งหมด
            }
            
            for file_path in data_files:
                try:
                    processed_files += 1
                    # คำนวณ progress ที่ถูกต้อง (0.0 - 1.0)
                    progress = (processed_files - 1) / total_files  # เริ่มจาก 0
                    
                    # อัปเดตความคืบหน้าแบบละเอียด
                    ui_callbacks['update_progress'](progress, f"Processing file: {os.path.basename(file_path)}", f"File {processed_files} of {total_files}")
                    
                    self.log(f"📁 Processing file: {os.path.basename(file_path)}")
                    
                    # ตรวจหา logic_type
                    logic_type = self.file_service.detect_file_type(file_path)
                    if not logic_type:
                        # ลองเดาจากชื่อไฟล์
                        filename = os.path.basename(file_path).lower()
                        for key in self.file_service.column_settings.keys():
                            if key.lower() in filename:
                                logic_type = key
                                break
                    
                    if not logic_type:
                        error_msg = f"Could not identify file type: {os.path.basename(file_path)}"
                        self.log(f"❌ {error_msg}")
                        process_stats['failed_files'] += 1
                        process_stats['errors'].append(f"{os.path.basename(file_path)}: {error_msg}")
                        continue
                    
                    # เริ่มจับเวลาสำหรับประเภทไฟล์นี้ (ถ้ายังไม่มี)
                    if logic_type not in process_stats['by_type']:
                        process_stats['by_type'][logic_type] = {
                            'start_time': time.time(),
                            'files_count': 0,
                            'successful_files': 0,
                            'failed_files': 0,
                            'errors': [],
                            'individual_processing_time': 0,  # เก็บเวลารวมของประเภทนี้
                            'successful_file_list': [],  # เก็บชื่อไฟล์ที่สำเร็จ
                            'failed_file_list': []  # เก็บชื่อไฟล์ที่ล้มเหลว
                        }
                    
                    # จับเวลาสำหรับไฟล์นี้เฉพาะ
                    file_start_time = time.time()
                    
                    process_stats['by_type'][logic_type]['files_count'] += 1
                    
                    self.log(f"📋 Identified file type: {logic_type}")
                    
                    # ตรวจสอบคอลัมน์ก่อนโดยการ preview ไฟล์ (ประหยัดเวลา)
                    success, result, columns_info = self.file_service.preview_file_columns(file_path, logic_type)
                    if not success:
                        error_msg = f"Column check failed: {result}"
                        self.log(f"❌ {error_msg}")
                        process_stats['by_type'][logic_type]['failed_files'] += 1
                        process_stats['by_type'][logic_type]['failed_file_list'].append(os.path.basename(file_path))
                        process_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {error_msg}")
                        process_stats['failed_files'] += 1
                        
                        # คำนวณเวลาที่ใช้แม้เมื่อตรวจสอบคอลัมน์ล้มเหลว
                        file_processing_time = time.time() - file_start_time
                        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time
                        continue
                    
                    # อ่านไฟล์เต็มรูปแบบ (หลังจากตรวจสอบคอลัมน์ผ่านแล้ว)
                    success, result = self.file_service.read_excel_file(file_path, logic_type)
                    if not success:
                        error_msg = f"Could not read file: {result}"
                        self.log(f"❌ {error_msg}")
                        process_stats['by_type'][logic_type]['failed_files'] += 1
                        process_stats['by_type'][logic_type]['failed_file_list'].append(os.path.basename(file_path))
                        process_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {error_msg}")
                        process_stats['failed_files'] += 1
                        
                        # คำนวณเวลาที่ใช้แม้เมื่ออ่านไฟล์ล้มเหลว
                        file_processing_time = time.time() - file_start_time
                        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time
                        continue
                    
                    df = result
                    
                    # หมายเหตุ: การตรวจสอบข้อมูลรายละเอียดจะทำใน staging table ด้วย SQL
                    
                    # อัปโหลดข้อมูล
                    required_cols = self.file_service.get_required_dtypes(logic_type)
                    
                    # ตรวจสอบว่า required_cols ไม่ว่างเปล่า
                    if not required_cols:
                        error_msg = f"No data type configuration found for {logic_type}"
                        self.log(f"❌ {error_msg}")
                        process_stats['by_type'][logic_type]['failed_files'] += 1
                        process_stats['by_type'][logic_type]['failed_file_list'].append(os.path.basename(file_path))
                        process_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {error_msg}")
                        process_stats['failed_files'] += 1
                        
                        # คำนวณเวลาที่ใช้แม้เมื่อไม่พบ configuration
                        file_processing_time = time.time() - file_start_time
                        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time
                        continue
                    
                    # ตรวจสอบว่าข้อมูลไม่ว่างเปล่า
                    if df.empty:
                        error_msg = f"File {os.path.basename(file_path)} has no data"
                        self.log(f"❌ {error_msg}")
                        process_stats['by_type'][logic_type]['failed_files'] += 1
                        process_stats['by_type'][logic_type]['failed_file_list'].append(os.path.basename(file_path))
                        process_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {error_msg}")
                        process_stats['failed_files'] += 1
                        
                        # คำนวณเวลาที่ใช้แม้เมื่อไฟล์ว่างเปล่า
                        file_processing_time = time.time() - file_start_time
                        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time
                        continue
                    
                    self.log(f"📊 Uploading {len(df)} rows for type {logic_type}")
                    # Clear existing data on first upload for each type
                    success, message = self.db_service.upload_data(df, logic_type, required_cols, log_func=self.log, clear_existing=True)
                    
                    if success:
                        self.log(f"✅ Upload successful: {message}")
                        successful_uploads += 1
                        process_stats['by_type'][logic_type]['successful_files'] += 1
                        process_stats['by_type'][logic_type]['successful_file_list'].append(os.path.basename(file_path))
                        process_stats['successful_files'] += 1

                        # คำนวณเวลาที่ใช้สำหรับไฟล์นี้และเพิ่มเข้าไปในเวลารวม
                        file_processing_time = time.time() - file_start_time
                        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time
                        
                        # ย้ายไฟล์หลังอัปโหลดสำเร็จ
                        try:
                            move_success, move_result = self.file_service.move_uploaded_files([file_path], [logic_type])
                            if move_success:
                                for original_path, new_path in move_result:
                                    self.log(f"📦 Moved file to: {os.path.basename(new_path)}")
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

                            error_msg = f"Upload failed: {summary}"
                            self.log(f"❌ {error_msg}")
                            process_stats['by_type'][logic_type]['validation_details'] = {
                                'issues': validation_issues,
                                'warnings': validation_warnings
                            }
                        else:
                            error_msg = f"Upload failed: {message}"
                            self.log(f"❌ {error_msg}")

                        process_stats['by_type'][logic_type]['failed_files'] += 1
                        process_stats['by_type'][logic_type]['failed_file_list'].append(os.path.basename(file_path))
                        process_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {error_msg}")
                        process_stats['failed_files'] += 1
                        
                        # คำนวณเวลาที่ใช้สำหรับไฟล์นี้แม้เมื่อล้มเหลว
                        file_processing_time = time.time() - file_start_time
                        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time
                        
                except Exception as e:
                    error_msg = f"An error occurred while processing {os.path.basename(file_path)}: {e}"
                    self.log(f"❌ {error_msg}")
                    if logic_type and logic_type in process_stats['by_type']:
                        process_stats['by_type'][logic_type]['failed_files'] += 1
                        process_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {str(e)}")
                        
                        # คำนวณเวลาที่ใช้สำหรับไฟล์นี้แม้เมื่อเกิดข้อผิดพลาด
                        file_processing_time = time.time() - file_start_time
                        process_stats['by_type'][logic_type]['individual_processing_time'] += file_processing_time
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
    
    def _auto_export_logs(self):
        """ส่งออก log อัตโนมัติไปยังโฟลเดอร์ log_pipeline และจัดการไฟล์เก่า"""
        try:
            from config.json_manager import get_input_folder

            # โหลดการตั้งค่า
            app_settings = json_manager.load('app_settings')

            # ตรวจสอบว่าเปิดใช้งานการส่งออกอัตโนมัติหรือไม่
            auto_export = app_settings.get('auto_export_logs', True)
            if not auto_export:
                return

            # อ่าน input folder path
            input_folder_path = get_input_folder()
            if not input_folder_path or not os.path.exists(input_folder_path):
                self.log("⚠️ Cannot export logs: No valid input folder found")
                return

            # ตั้งค่า file logging และส่งออก
            log_file_path = setup_file_logging(input_folder_path, enable_export=True)
            if log_file_path:
                self.log(f"📋 Log exported to: {log_file_path}")

                # จัดการไฟล์ log เก่า (ลบไฟล์ที่เก่าเกิน retention period)
                retention_days = app_settings.get('log_retention_days', 30)
                deleted_count = cleanup_old_log_files(input_folder_path, retention_days)

                # แสดงผลการ cleanup เฉพาะเมื่อมีการลบไฟล์
                if deleted_count > 0:
                    self.log(f"🧹 Cleaned up {deleted_count} old log files (older than {retention_days} days)")
            else:
                self.log("⚠️ Failed to export log file")

        except Exception as e:
            self.log(f"❌ Error during auto export logs: {e}")
