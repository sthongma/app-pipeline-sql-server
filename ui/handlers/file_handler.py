"""File Operation Handlers"""
import os
import threading
from datetime import datetime
from tkinter import messagebox, filedialog
import pandas as pd


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
    
    def browse_excel_path(self, save_callback):
        """เลือกโฟลเดอร์สำหรับค้นหาไฟล์"""
        folder = filedialog.askdirectory()
        if folder:
            self.file_service.set_search_path(folder)
            save_callback(folder)
            messagebox.showinfo("Success", f"Set search path for Excel files to\n{folder}")
    
    def run_check_thread(self, ui_callbacks):
        """เริ่มการตรวจสอบไฟล์ใน thread แยก"""
        thread = threading.Thread(target=self._check_files, args=(ui_callbacks,))
        thread.start()
    
    def _check_files(self, ui_callbacks):
        """ตรวจสอบไฟล์ใน Path ที่กำหนด"""
        try:
            # รีเซ็ต UI
            ui_callbacks['reset_progress']()
            ui_callbacks['set_progress_status']("Starting file scan", "Scanning folders...")
            
            # โหลดการตั้งค่าใหม่
            self.file_service.load_settings()
            ui_callbacks['clear_file_list']()
            ui_callbacks['disable_auto_process']()
            ui_callbacks['reset_select_all']()
            
            # ค้นหาไฟล์ Excel/CSV
            ui_callbacks['update_progress'](0.2, "Searching for files", "Scanning .xlsx and .csv files...")
            data_files = self.file_service.find_data_files()
            
            if not data_files:
                ui_callbacks['update_progress'](1.0, "Scan completed", "No .xlsx or .csv files found")
                ui_callbacks['update_status']("No .xlsx or .csv files found in the specified folder", True)
                self.log("🤷 No .xlsx or .csv files found in the specified folder")
                self.log("--- 🏁 File scan completed ---")
                ui_callbacks['enable_auto_process']()
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
            ui_callbacks['enable_auto_process']()
            
        except Exception as e:
            self.log(f"❌ An error occurred while scanning files: {e}")
            ui_callbacks['enable_auto_process']()
    
    def confirm_upload(self, get_selected_files_callback, ui_callbacks):
        """ยืนยันการอัปโหลดไฟล์ที่เลือก"""
        selected = get_selected_files_callback()
        if not selected:
            messagebox.showwarning("No files", "Please select files to upload")
            return
        
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
    
    def _upload_selected_files(self, selected_files, ui_callbacks):
        """อัปโหลดไฟล์ที่เลือกไปยัง SQL Server"""
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
        
        # แสดงสถานะเริ่มต้น
        ui_callbacks['set_progress_status']("Starting upload", f"Found {total_files} files from {total_types} types")
        
        # Phase 1: Read and validate all files first
        self.log("📖 Phase 1: Reading and validating all files...")
        all_validated_data = {}  # {logic_type: (combined_df, files_info, required_cols)}
        
        for logic_type, files in files_by_type.items():
            try:
                self.log(f"📖 Validating files of type {logic_type}")
                
                # อัปเดต Progress Bar ตามความคืบหน้า
                progress = completed_types / total_types
                ui_callbacks['update_progress'](progress, f"Validating type {logic_type}", f"Type {completed_types + 1} of {total_types}")
                
                # รวมข้อมูลจากทุกไฟล์ในประเภทเดียวกัน
                all_dfs = []
                valid_files_info = []
                
                for file_path, chk in files:
                    try:
                        processed_files += 1
                        # คำนวณ progress ที่ถูกต้อง (0.0 - 1.0)
                        file_progress = (processed_files - 1) / total_files  # เริ่มจาก 0
                        
                        # อัปเดตความคืบหน้าระดับไฟล์
                        ui_callbacks['update_progress'](file_progress, f"Reading file: {os.path.basename(file_path)}", f"File {processed_files} of {total_files}")
                        
                        # อ่านไฟล์ Excel
                        success, result = self.file_service.read_excel_file(file_path, logic_type)
                        if not success:
                            self.log(f"❌ {result}")
                            continue
                        
                        df = result
                        
                        # ตรวจสอบคอลัมน์เบื้องต้น (เฉพาะ column existence)
                        success, result = self.file_service.validate_columns(df, logic_type)
                        if not success:
                            self.log(f"❌ {result}")
                            continue
                        
                        # หมายเหตุ: การตรวจสอบข้อมูลรายละเอียดจะทำใน staging table ด้วย SQL
                        
                        all_dfs.append(df)
                        valid_files_info.append((file_path, chk))
                        self.log(f"✅ Validated file: {os.path.basename(file_path)}")
                        
                    except Exception as e:
                        self.log(f"❌ An error occurred while reading file {os.path.basename(file_path)}: {e}")
                
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
                self.log(f"❌ An error occurred while validating files of type {logic_type}: {e}")
                completed_types += 1
        
        # Phase 2: Upload all validated data (with proper table clearing sequence)
        if all_validated_data:
            self.log("📤 Phase 2: Uploading all validated data...")
            upload_count = 0
            total_uploads = len(all_validated_data)
            
            for logic_type, (combined_df, valid_files_info, required_cols) in all_validated_data.items():
                try:
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
                        self.log(f"❌ {message}")
                        
                    upload_count += 1
                    
                except Exception as e:
                    self.log(f"❌ An error occurred while uploading data for type {logic_type}: {e}")
                    upload_count += 1
        else:
            self.log("❌ No validated data to upload")
        
        # อัปเดต progress เป็น 100% เมื่อเสร็จสิ้น
        successfully_uploaded = sum(1 for files in files_by_type.values() for _ in files)  # Count all processed files
        ui_callbacks['update_progress'](1.0, "Upload completed", f"Processed {total_files} files successfully")
        self.log("========= Upload Ended ==========")
        
        # เปิดปุ่มทั้งหมดกลับมา
        ui_callbacks['enable_controls']()
    
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
                        self.log(f"❌ Could not identify file type: {os.path.basename(file_path)}")
                        continue
                    
                    self.log(f"📋 Identified file type: {logic_type}")
                    
                    # อ่านไฟล์
                    success, result = self.file_service.read_excel_file(file_path, logic_type)
                    if not success:
                        self.log(f"❌ Could not read file: {result}")
                        continue
                    
                    df = result
                    
                    # ตรวจสอบคอลัมน์เบื้องต้น (เฉพาะ column existence)
                    success, result = self.file_service.validate_columns(df, logic_type)
                    if not success:
                        self.log(f"❌ Invalid columns: {result}")
                        continue
                    
                    # หมายเหตุ: การตรวจสอบข้อมูลรายละเอียดจะทำใน staging table ด้วย SQL
                    
                    # อัปโหลดข้อมูล
                    required_cols = self.file_service.get_required_dtypes(logic_type)
                    
                    # ตรวจสอบว่า required_cols ไม่ว่างเปล่า
                    if not required_cols:
                        self.log(f"❌ No data type configuration found for {logic_type}")
                        continue
                    
                    # ตรวจสอบว่าข้อมูลไม่ว่างเปล่า
                    if df.empty:
                        self.log(f"❌ File {os.path.basename(file_path)} has no data")
                        continue
                    
                    self.log(f"📊 Uploading {len(df)} rows for type {logic_type}")
                    # Clear existing data on first upload for each type
                    success, message = self.db_service.upload_data(df, logic_type, required_cols, log_func=self.log, clear_existing=True)
                    
                    if success:
                        self.log(f"✅ Upload successful: {message}")
                        successful_uploads += 1
                        
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
                        self.log(f"❌ Upload failed: {message}")
                        
                except Exception as e:
                    self.log(f"❌ An error occurred while processing {os.path.basename(file_path)}: {e}")
            
            # อัปเดต progress เป็น 100% เมื่อเสร็จสิ้น
            ui_callbacks['update_progress'](1.0, "Processing completed", f"Successfully processed {successful_uploads} of {total_files} files")
            self.log(f"✅ File processing completed: {successful_uploads}/{total_files} files successful")
            
        except Exception as e:
            self.log(f"❌ An error occurred while processing files: {e}")
