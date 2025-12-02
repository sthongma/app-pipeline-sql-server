"""File Upload Operations Handler"""
import os
import time
import threading
import uuid
from datetime import datetime
from tkinter import messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Callable, Optional, Any
import pandas as pd
from performance_optimizations import PerformanceOptimizer


class FileUploadHandler:
    """Handles file upload operations to database"""

    def __init__(
        self,
        file_service: Any,
        db_service: Any,
        file_mgmt_service: Any,
        log_callback: Callable[[str], None],
        report_callback: Optional[Callable[[Dict, int], None]] = None
    ) -> None:
        """
        Initialize File Upload Handler

        Args:
            file_service: File service instance
            db_service: Database service instance
            file_mgmt_service: File management service instance
            log_callback: Function to call for logging
            report_callback: Optional callback for displaying reports after upload
        """
        self.file_service = file_service
        self.db_service = db_service
        self.file_mgmt_service = file_mgmt_service
        self.log: Callable[[str], None] = log_callback
        self.report_callback = report_callback
        self.is_uploading: bool = False  # Flag to prevent multiple upload operations

        # Initialize Performance Optimizer for parallel processing
        self.perf_optimizer = PerformanceOptimizer(log_callback=log_callback)
        self.max_workers: int = min(4, os.cpu_count() or 1)  # Number of parallel workers

    def confirm_upload(self, get_selected_files_callback, ui_callbacks):
        """ยืนยันการอัปโหลดไฟล์ที่เลือก - with double-click protection"""
        # ป้องกันการกดซ้ำขณะกำลัง upload อยู่
        if self.is_uploading:
            self.log("Warning: Upload is already in progress, please wait...")
            return

        selected = get_selected_files_callback()
        if not selected:
            messagebox.showwarning("No files", "Please select files to upload")
            return

        # โหลดการตั้งค่าใหม่ก่อนอัปโหลด เพื่อให้แน่ใจว่าใช้การตั้งค่าล่าสุด
        self.log("Loading latest settings before upload...")
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
        """Wrapper to reset upload flag and display report after upload completes"""
        try:
            upload_stats, total_files = self._upload_selected_files(selected_files, ui_callbacks)

            # Display report if callback is provided
            if self.report_callback:
                self.report_callback(upload_stats, total_files)

        finally:
            # Always reset flag and enable controls, even if an exception occurred
            self.is_uploading = False
            ui_callbacks['enable_controls']()

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
                self.log(f"Using optimized reader for large file: {os.path.basename(file_path)} ({file_size_mb:.1f} MB)")

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

            # Add source file tracking to each row
            df['_source_file'] = os.path.basename(file_path)

            # Successful validation
            result['success'] = True
            result['df'] = df

            file_processing_time = time.time() - file_start_time
            self.log(f"Validated: {os.path.basename(file_path)} ({file_processing_time:.1f}s)")

        except Exception as e:
            result['error'] = str(e)
            self.log(f"Error validating {os.path.basename(file_path)}: {e}")

        return result

    def _determine_upload_mode(self, selected_files):
        """
        ตรวจสอบว่าทุกไฟล์ใช้โหมดเดียวกันหรือไม่

        Args:
            selected_files: List of ((file_path, logic_type), checkbox) tuples

        Returns:
            Tuple[str, Dict]: (mode, strategies)
            - mode: 'upsert', 'replace', or 'mixed'
            - strategies: {logic_type: {'strategy': str, 'keys': list}}
        """
        from services.settings_manager import settings_manager

        strategies = {}
        for (file_path, logic_type), chk in selected_files:
            if logic_type not in strategies:
                dtype_cfg = settings_manager.get_dtype_settings(logic_type)
                strategy = dtype_cfg.get('_update_strategy', 'replace')
                upsert_keys = dtype_cfg.get('_upsert_keys', [])
                strategies[logic_type] = {
                    'strategy': strategy,
                    'keys': upsert_keys
                }

        # Determine overall mode
        strategy_set = set(s['strategy'] for s in strategies.values())
        if len(strategy_set) == 1 and 'upsert' in strategy_set:
            return 'upsert', strategies
        elif len(strategy_set) == 1 and 'replace' in strategy_set:
            return 'replace', strategies
        else:
            return 'mixed', strategies

    def _get_files_with_metadata(self, selected_files):
        """
        ดึง metadata ของไฟล์ รวมถึงเวลา modification

        Args:
            selected_files: List of ((file_path, logic_type), checkbox) tuples

        Returns:
            List[Dict]: [{
                'file_path': str,
                'logic_type': str,
                'chk': widget,
                'mod_time': float,
                'mod_time_str': str,
                'filename': str
            }]
        """
        files_with_metadata = []

        for (file_path, logic_type), chk in selected_files:
            try:
                file_stats = os.stat(file_path)
                mod_time = file_stats.st_mtime
                mod_time_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')

                files_with_metadata.append({
                    'file_path': file_path,
                    'logic_type': logic_type,
                    'chk': chk,
                    'mod_time': mod_time,
                    'mod_time_str': mod_time_str,
                    'filename': os.path.basename(file_path)
                })
            except Exception as e:
                self.log(f"Error getting metadata for {file_path}: {e}")
                # Still add file without metadata (default to epoch)
                files_with_metadata.append({
                    'file_path': file_path,
                    'logic_type': logic_type,
                    'chk': chk,
                    'mod_time': 0,
                    'mod_time_str': 'Unknown',
                    'filename': os.path.basename(file_path)
                })

        return files_with_metadata

    def _sort_files_by_modification_time(self, files_with_metadata):
        """
        เรียงไฟล์ตามเวลา modified (น้อยสุดก่อน)

        Args:
            files_with_metadata: List of file metadata dicts

        Returns:
            List[Dict]: Sorted list (oldest first)
        """
        return sorted(files_with_metadata, key=lambda x: x['mod_time'])

    def _upload_single_file_upsert(self, file_metadata, batch_id, file_index, total_files, ui_callbacks, upload_stats):
        """
        Upload ไฟล์เดียวในโหมด Upsert (validation → upload → move)

        Args:
            file_metadata: Dict with file metadata
            batch_id: Batch ID for this upload session
            file_index: Current file index (1-based)
            total_files: Total number of files
            ui_callbacks: UI callback functions
            upload_stats: Upload statistics dict

        Returns:
            bool: True if successful, False otherwise
        """
        file_path = file_metadata['file_path']
        logic_type = file_metadata['logic_type']
        chk = file_metadata['chk']
        filename = file_metadata['filename']
        mod_time_str = file_metadata['mod_time_str']

        # Initialize type stats if needed
        if logic_type not in upload_stats['by_type']:
            upload_stats['by_type'][logic_type] = self._init_type_stats(1, time.time())

        self.log(f"[{file_index}/{total_files}] Processing: {filename} (Modified: {mod_time_str})")

        try:
            # Phase 1: Validation
            progress = (file_index - 1) / total_files
            ui_callbacks['update_progress'](
                progress,
                f"Validating: {filename}",
                f"File {file_index} of {total_files}"
            )

            validation_result = self._validate_single_file((file_path, logic_type))

            if not validation_result['success']:
                error = validation_result['error']
                self.log(f"[{file_index}/{total_files}] Validation failed: {filename}: {error}")
                upload_stats['by_type'][logic_type]['failed_files'] += 1
                upload_stats['by_type'][logic_type]['failed_file_list'].append(filename)
                upload_stats['by_type'][logic_type]['errors'].append(f"{filename}: {error}")
                upload_stats['failed_files'] += 1
                return False

            df = validation_result['df']

            # Phase 2: Upload
            progress = (file_index - 0.5) / total_files
            ui_callbacks['update_progress'](
                progress,
                f"Uploading: {filename}",
                f"File {file_index} of {total_files}"
            )

            required_cols = self.file_service.get_required_dtypes(logic_type)
            if not required_cols:
                error = f"No data type configuration found for {logic_type}"
                self.log(f"[{file_index}/{total_files}] Error: {error}")
                upload_stats['by_type'][logic_type]['failed_files'] += 1
                upload_stats['by_type'][logic_type]['failed_file_list'].append(filename)
                upload_stats['by_type'][logic_type]['errors'].append(f"{filename}: {error}")
                upload_stats['failed_files'] += 1
                return False

            success, message = self.db_service.upload_data(
                df, logic_type, required_cols,
                log_func=self.log,
                clear_existing=True,
                batch_id=batch_id
            )

            if not success:
                # Handle upload failure
                if isinstance(message, dict):
                    summary = message.get('summary', 'Upload failed')
                    self.log(f"[{file_index}/{total_files}] Error: {summary}")
                    upload_stats['by_type'][logic_type]['errors'].append(f"{filename}: {summary}")
                else:
                    self.log(f"[{file_index}/{total_files}] Error: {message}")
                    upload_stats['by_type'][logic_type]['errors'].append(f"{filename}: {message}")

                upload_stats['by_type'][logic_type]['failed_files'] += 1
                upload_stats['by_type'][logic_type]['failed_file_list'].append(filename)
                upload_stats['failed_files'] += 1
                return False

            # Phase 3: Move file immediately on success
            self.log(f"[{file_index}/{total_files}] Success: {message}")
            upload_stats['by_type'][logic_type]['summary_message'] = message

            try:
                move_success, move_result = self.file_mgmt_service.move_uploaded_files([file_path], [logic_type])
                if move_success:
                    for original_path, new_path in move_result:
                        self.log(f"[{file_index}/{total_files}] Moved to: {new_path}")
                    ui_callbacks['disable_checkbox'](chk)
                    ui_callbacks['set_file_uploaded'](file_path)
                else:
                    self.log(f"[{file_index}/{total_files}] Warning: Upload succeeded but move failed: {move_result}")
            except Exception as move_error:
                self.log(f"[{file_index}/{total_files}] Warning: Upload succeeded but move error: {move_error}")

            # Update stats
            upload_stats['by_type'][logic_type]['successful_files'] += 1
            upload_stats['by_type'][logic_type]['successful_file_list'].append(filename)
            upload_stats['successful_files'] += 1

            # Complete progress
            progress = file_index / total_files
            ui_callbacks['update_progress'](
                progress,
                f"Completed: {filename}",
                f"File {file_index} of {total_files}"
            )

            return True

        except Exception as e:
            error_msg = f"Error processing {filename}: {e}"
            self.log(f"[{file_index}/{total_files}] {error_msg}")
            upload_stats['by_type'][logic_type]['failed_files'] += 1
            upload_stats['by_type'][logic_type]['failed_file_list'].append(filename)
            upload_stats['by_type'][logic_type]['errors'].append(f"{filename}: {str(e)}")
            upload_stats['failed_files'] += 1
            return False

    def _upload_files_sequentially_upsert(self, sorted_files, batch_id, ui_callbacks, upload_stats):
        """
        ประมวลผลไฟล์ทีละไฟล์ในโหมด Upsert

        Args:
            sorted_files: List of file metadata dicts (sorted by modification time)
            batch_id: Batch ID for this upload session
            ui_callbacks: UI callback functions
            upload_stats: Upload statistics dict
        """
        total_files = len(sorted_files)

        self.log(f"Sequential Upsert Mode: Processing {total_files} files (oldest first)")
        self.log(f"Batch ID: {batch_id}")

        for file_index, file_metadata in enumerate(sorted_files, start=1):
            try:
                success = self._upload_single_file_upsert(
                    file_metadata, batch_id, file_index, total_files,
                    ui_callbacks, upload_stats
                )
                # Continue regardless of success
            except Exception as e:
                file_path = file_metadata['file_path']
                filename = os.path.basename(file_path)
                self.log(f"[{file_index}/{total_files}] Unexpected error: {filename}: {e}")
                upload_stats['failed_files'] += 1
                # Continue to next file
                continue

    def _upload_selected_files(self, selected_files, ui_callbacks):
        """
        อัปโหลดไฟล์ที่เลือกไปยัง SQL Server

        รองรับ 2 modes:
        - Upsert Mode: Sequential processing (ทีละไฟล์ตามลำดับเวลา modified)
        - Replace Mode: Batch processing (รวมไฟล์แล้ว upload ครั้งเดียว)
        """
        upload_start_time = time.time()
        upload_stats = self._init_upload_stats(upload_start_time)

        # Determine upload mode
        upload_mode, strategies = self._determine_upload_mode(selected_files)
        self.log(f"Upload Mode: {upload_mode.upper()}")

        # Generate single batch_id for entire session
        batch_id = str(uuid.uuid4())
        self.log(f"Batch ID: {batch_id}")

        # Separate files by mode (Upsert vs Replace)
        upsert_files = []
        replace_files = []

        for (file_path, logic_type), chk in selected_files:
            if logic_type in strategies:
                if strategies[logic_type]['strategy'] == 'upsert':
                    upsert_files.append(((file_path, logic_type), chk))
                else:
                    replace_files.append(((file_path, logic_type), chk))

        total_files = len(upsert_files) + len(replace_files)
        self.log(f"Files breakdown: {len(upsert_files)} Upsert, {len(replace_files)} Replace")

        # Process Upsert files first (sequential)
        if upsert_files:
            self.log(f"=== Processing {len(upsert_files)} Upsert files (Sequential Mode) ===")

            # Get files with metadata and sort by modification time
            files_with_metadata = self._get_files_with_metadata(upsert_files)
            sorted_files = self._sort_files_by_modification_time(files_with_metadata)

            # แสดงสถานะเริ่มต้น
            ui_callbacks['set_progress_status']("Starting upload", f"Processing {len(sorted_files)} Upsert files sequentially")

            # Process files sequentially
            self._upload_files_sequentially_upsert(sorted_files, batch_id, ui_callbacks, upload_stats)

        # Process Replace files (batch mode)
        if replace_files:
            self._upload_replace_files_batch(replace_files, batch_id, ui_callbacks, upload_stats)

        # คำนวณเวลารวม
        total_upload_time = time.time() - upload_start_time
        upload_stats['total_time'] = total_upload_time

        # อัปเดต progress เป็น 100% เมื่อเสร็จสิ้น
        ui_callbacks['update_progress'](1.0, "Upload completed", f"Processed {total_files} files successfully")

        # Return stats for reporting
        return upload_stats, total_files

    def _upload_replace_files_batch(self, replace_files, batch_id, ui_callbacks, upload_stats):
        """
        Process Replace mode files in batch

        Args:
            replace_files: List of files in replace mode
            batch_id: Batch ID for this session
            ui_callbacks: UI callback functions
            upload_stats: Upload statistics dict
        """
        self.log(f"=== Processing {len(replace_files)} Replace files (Batch Mode) ===")

        # จัดกลุ่มไฟล์และเตรียม stats
        files_by_type = self._group_files_by_type(replace_files)
        replace_total_files = sum(len(files) for files in files_by_type.values())
        total_types = len(files_by_type)

        # แสดงสถานะเริ่มต้น
        ui_callbacks['set_progress_status']("Processing Replace files", f"Found {replace_total_files} Replace files from {total_types} types")

        # Phase 1: Read and validate Replace files with PARALLEL PROCESSING
        self.log("Phase 1: Reading and validating Replace files in parallel...")
        self.log(f"Using {self.max_workers} parallel workers for optimal performance")
        all_validated_data = {}  # {logic_type: (combined_df, files_info, required_cols)}

        completed_types = 0
        processed_files = 0

        for logic_type, files in files_by_type.items():
            try:
                # เริ่มจับเวลาสำหรับประเภทไฟล์นี้
                type_start_time = time.time()
                upload_stats['by_type'][logic_type] = self._init_type_stats(len(files), type_start_time)

                self.log(f"Validating files of type {logic_type} ({len(files)} files)")

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
                            file_progress = (processed_files - 1) / replace_total_files

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
                                    f"Validated: {os.path.basename(file_path)}",
                                    f"File {processed_files} of {replace_total_files}"
                                )
                            else:
                                error = validation_result['error']
                                self.log(f"Validation failed for {os.path.basename(file_path)}: {error}")
                                upload_stats['by_type'][logic_type]['failed_files'] += 1
                                upload_stats['by_type'][logic_type]['failed_file_list'].append(os.path.basename(file_path))
                                upload_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {error}")
                                upload_stats['failed_files'] += 1

                                # Update UI
                                ui_callbacks['update_progress'](
                                    file_progress,
                                    f"Failed: {os.path.basename(file_path)}",
                                    f"File {processed_files} of {replace_total_files}"
                                )

                        except Exception as e:
                            error_msg = f"An error occurred while validating file {os.path.basename(file_path)}: {e}"
                            self.log(f"Error: {error_msg}")
                            upload_stats['by_type'][logic_type]['failed_files'] += 1
                            upload_stats['by_type'][logic_type]['errors'].append(f"{os.path.basename(file_path)}: {str(e)}")
                            upload_stats['failed_files'] += 1

                # Calculate processing time for this type
                upload_stats['by_type'][logic_type]['individual_processing_time'] = time.time() - type_start_time

                if not all_dfs:
                    self.log(f"Error: No valid data from files of type {logic_type}")
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
                    self.log(f"Error: No data type configuration found for {logic_type}")
                    completed_types += 1
                    continue

                # ตรวจสอบว่าข้อมูลไม่ว่างเปล่า
                if combined_df.empty:
                    self.log(f"Error: No valid data from files of type {logic_type}")
                    completed_types += 1
                    continue

                # เก็บข้อมูลที่ผ่านการตรวจสอบแล้ว
                all_validated_data[logic_type] = (combined_df, valid_files_info, required_cols)
                self.log(f"Prepared {len(combined_df)} rows for type {logic_type}")

                completed_types += 1

            except Exception as e:
                error_msg = f"An error occurred while validating files of type {logic_type}: {e}"
                self.log(f"Error: {error_msg}")
                upload_stats['by_type'][logic_type]['errors'].append(error_msg)
                completed_types += 1

        # Phase 2: Upload all validated data (with proper table clearing sequence)
        if all_validated_data:
            self.log("Phase 2: Uploading all validated data...")
            upload_count = 0
            total_uploads = len(all_validated_data)

            for logic_type, (combined_df, valid_files_info, required_cols) in all_validated_data.items():
                try:
                    # จับเวลาเริ่มต้น Phase 2 สำหรับประเภทไฟล์นี้
                    phase2_start_time = time.time()

                    upload_progress = upload_count / total_uploads
                    ui_callbacks['update_progress'](upload_progress, f"Uploading data for type {logic_type}", f"Upload {upload_count + 1} of {total_uploads}")

                    self.log(f"Uploading {len(combined_df)} rows for type {logic_type}")

                    # Clear existing data only for the first upload of each table
                    success, message = self.db_service.upload_data(
                        combined_df, logic_type, required_cols,
                        log_func=self.log, clear_existing=True, batch_id=batch_id
                    )

                    if success:
                        self.log(f"Success: {message}")

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
                                        self.log(f"Moved file to: {new_path}")
                                else:
                                    self.log(f"Error: Could not move file: {move_result}")
                            except Exception as move_error:
                                self.log(f"Error: An error occurred while moving file: {move_error}")
                    else:
                        # แสดงเฉพาะข้อความสรุปจากบริการฐานข้อมูล ไม่พิมพ์รายการคอลัมน์ทั้งหมด
                        # ตรวจสอบว่า message เป็น dict หรือ string
                        if isinstance(message, dict):
                            summary = message.get('summary', 'Upload failed')
                            validation_issues = message.get('issues', [])
                            validation_warnings = message.get('warnings', [])

                            self.log(f"Error: {summary}")
                            upload_stats['by_type'][logic_type]['errors'].append(f"Database upload failed: {summary}")
                            upload_stats['by_type'][logic_type]['validation_details'] = {
                                'issues': validation_issues,
                                'warnings': validation_warnings
                            }
                        else:
                            self.log(f"Error: {message}")
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
                    self.log(f"Error: {error_msg}")
                    upload_stats['by_type'][logic_type]['errors'].append(error_msg)
                    upload_count += 1

                    # คำนวณเวลา Phase 2 แม้เมื่อมีข้อผิดพลาดและรวมเข้าไปใน individual_processing_time
                    phase2_time = time.time() - phase2_start_time
                    if 'individual_processing_time' in upload_stats['by_type'][logic_type]:
                        upload_stats['by_type'][logic_type]['individual_processing_time'] += phase2_time
                        upload_stats['by_type'][logic_type]['processing_time'] = upload_stats['by_type'][logic_type]['individual_processing_time']
        else:
            self.log("Error: No validated data to upload")
