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
            messagebox.showinfo("สำเร็จ", f"ตั้งค่า path สำหรับค้นหาไฟล์ Excel เป็น\n{folder}")
    
    def run_check_thread(self, ui_callbacks):
        """เริ่มการตรวจสอบไฟล์ใน thread แยก"""
        thread = threading.Thread(target=self._check_files, args=(ui_callbacks,))
        thread.start()
    
    def _check_files(self, ui_callbacks):
        """ตรวจสอบไฟล์ใน Path ที่กำหนด"""
        try:
            # รีเซ็ต UI
            ui_callbacks['reset_progress']()
            ui_callbacks['set_progress_status']("เริ่มการตรวจสอบไฟล์", "กำลังสแกนโฟลเดอร์...")
            
            # โหลดการตั้งค่าใหม่
            self.file_service.load_settings()
            ui_callbacks['clear_file_list']()
            ui_callbacks['disable_auto_process']()
            ui_callbacks['reset_select_all']()
            
            # ค้นหาไฟล์ Excel/CSV
            ui_callbacks['update_progress'](0.2, "กำลังค้นหาไฟล์", "สแกนไฟล์ .xlsx และ .csv...")
            data_files = self.file_service.find_data_files()
            
            if not data_files:
                ui_callbacks['update_progress'](1.0, "การตรวจสอบเสร็จสิ้น", "ไม่พบไฟล์ .xlsx หรือ .csv")
                ui_callbacks['update_status']("ไม่พบไฟล์ .xlsx หรือ .csv ในโฟลเดอร์ที่กำหนด", True)
                self.log("🤷 ไม่พบไฟล์ .xlsx หรือ .csv ในโฟลเดอร์ที่กำหนด")
                self.log("--- 🏁 ตรวจสอบไฟล์เสร็จสิ้น ---")
                ui_callbacks['enable_auto_process']()
                return
            
            found_files_count = 0
            total_files = len(data_files)
            
            for i, file in enumerate(data_files):
                # คำนวณ progress ที่ถูกต้อง (0.2 - 0.8)
                progress = 0.2 + (0.6 * (i / total_files))  # 20% - 80%
                ui_callbacks['update_progress'](progress, f"กำลังตรวจสอบไฟล์: {os.path.basename(file)}", f"ไฟล์ที่ {i+1} จาก {total_files}")
                
                logic_type = self.file_service.detect_file_type(file)
                if logic_type:
                    found_files_count += 1
                    self.log(f"✅ พบไฟล์ตรงเงื่อนไข: {os.path.basename(file)} [{logic_type}]")
                    ui_callbacks['add_file_to_list'](file, logic_type)
            
            if found_files_count > 0:
                ui_callbacks['update_progress'](1.0, "การตรวจสอบเสร็จสิ้น", f"พบไฟล์ที่ตรงเงื่อนไข {found_files_count} ไฟล์")
                ui_callbacks['update_status'](f"พบไฟล์ที่ตรงเงื่อนไข {found_files_count} ไฟล์", False)
                ui_callbacks['enable_select_all']()
            else:
                ui_callbacks['update_progress'](1.0, "การตรวจสอบเสร็จสิ้น", "ไม่พบไฟล์ที่ตรงเงื่อนไข")
                ui_callbacks['update_status']("ไม่พบไฟล์ที่ตรงเงื่อนไข", True)
                ui_callbacks['reset_select_all']()
            
            self.log("--- 🏁 ตรวจสอบไฟล์เสร็จสิ้น ---")
            ui_callbacks['enable_auto_process']()
            
        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดขณะตรวจสอบไฟล์: {e}")
            ui_callbacks['enable_auto_process']()
    
    def confirm_upload(self, get_selected_files_callback, ui_callbacks):
        """ยืนยันการอัปโหลดไฟล์ที่เลือก"""
        selected = get_selected_files_callback()
        if not selected:
            messagebox.showwarning("ไม่มีไฟล์", "กรุณาเลือกไฟล์ที่ต้องการอัปโหลด")
            return
        
        # ตรวจสอบการเชื่อมต่อฐานข้อมูล
        success, message = self.db_service.check_connection()
        if not success:
            messagebox.showerror(
                "ข้อผิดพลาด", 
                f"ไม่สามารถเชื่อมต่อกับฐานข้อมูลได้:\n{message}\n\nกรุณาตรวจสอบการตั้งค่าฐานข้อมูลก่อน"
            )
            return
            
            
            
        answer = messagebox.askyesno(
            "ยืนยันการอัปโหลด",
            f"คุณแน่ใจหรือไม่ว่าต้องการอัปโหลดไฟล์ที่เลือก {len(selected)} ไฟล์?"
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
        ui_callbacks['set_progress_status']("เริ่มการอัปโหลด", f"พบไฟล์ {total_files} ไฟล์ จาก {total_types} ประเภท")
        
        for logic_type, files in files_by_type.items():
            try:
                self.log(f"📤 กำลังอัปโหลดไฟล์ประเภท {logic_type}")
                
                # อัปเดต Progress Bar ตามความคืบหน้า
                progress = completed_types / total_types
                ui_callbacks['update_progress'](progress, f"กำลังประมวลผลประเภท {logic_type}", f"ประเภทที่ {completed_types + 1} จาก {total_types}")
                
                # รวมข้อมูลจากทุกไฟล์ในประเภทเดียวกัน
                all_dfs = []
                for file_path, chk in files:
                    try:
                        processed_files += 1
                        # คำนวณ progress ที่ถูกต้อง (0.0 - 1.0)
                        file_progress = (processed_files - 1) / total_files  # เริ่มจาก 0
                        
                        # อัปเดตความคืบหน้าระดับไฟล์
                        ui_callbacks['update_progress'](file_progress, f"กำลังอ่านไฟล์: {os.path.basename(file_path)}", f"ไฟล์ที่ {processed_files} จาก {total_files}")
                        
                        # อ่านไฟล์ Excel
                        success, result = self.file_service.read_excel_file(file_path, logic_type)
                        if not success:
                            self.log(f"❌ {result}")
                            continue
                        
                        df = result
                        
                        # ตรวจสอบคอลัมน์
                        success, result = self.file_service.validate_columns(df, logic_type)
                        if not success:
                            self.log(f"❌ {result}")
                            continue
                        
                        all_dfs.append(df)
                        self.log(f"✅ อ่านข้อมูลจากไฟล์: {os.path.basename(file_path)}")
                        
                    except Exception as e:
                        self.log(f"❌ เกิดข้อผิดพลาดขณะอ่านไฟล์ {os.path.basename(file_path)}: {e}")
                
                if not all_dfs:
                    self.log(f"❌ ไม่มีข้อมูลที่ถูกต้องจากไฟล์ประเภท {logic_type}")
                    continue
                
                # รวม DataFrame ทั้งหมด
                combined_df = pd.concat(all_dfs, ignore_index=True)
                
                # แสดงสถานะการรวมข้อมูล
                ui_callbacks['update_progress'](file_progress, f"กำลังรวมข้อมูลประเภท {logic_type}", f"รวม {len(all_dfs)} ไฟล์ เป็น {len(combined_df)} แถว")
                
                # ใช้ dtype ที่ถูกต้อง
                required_cols = self.file_service.get_required_dtypes(logic_type)
                
                # ตรวจสอบว่า required_cols ไม่ว่างเปล่า
                if not required_cols:
                    self.log(f"❌ ไม่พบการตั้งค่าประเภทข้อมูลสำหรับ {logic_type}")
                    continue
                
                # ตรวจสอบว่าข้อมูลไม่ว่างเปล่า
                if combined_df.empty:
                    self.log(f"❌ ไม่มีข้อมูลที่ถูกต้องจากไฟล์ประเภท {logic_type}")
                    continue
                
                # อัปโหลดข้อมูล
                ui_callbacks['update_progress'](file_progress, f"กำลังอัปโหลดข้อมูลประเภท {logic_type}", f"ส่งข้อมูล {len(combined_df)} แถว ไปยัง SQL Server")
                self.log(f"📊 กำลังอัปโหลดข้อมูล {len(combined_df)} แถว สำหรับประเภท {logic_type}")
                success, message = self.db_service.upload_data(combined_df, logic_type, required_cols, log_func=self.log)
                
                if success:
                    self.log(f"✅ {message}")
                    for file_path, chk in files:
                        ui_callbacks['disable_checkbox'](chk)
                        ui_callbacks['set_file_uploaded'](file_path)
                        # ย้ายไฟล์ทันทีหลังอัปโหลดสำเร็จ
                        try:
                            move_success, move_result = self.file_service.move_uploaded_files([file_path], [logic_type])
                            if move_success:
                                for original_path, new_path in move_result:
                                    self.log(f"📦 ย้ายไฟล์ไปยัง: {os.path.basename(new_path)}")
                            else:
                                self.log(f"❌ ไม่สามารถย้ายไฟล์: {move_result}")
                        except Exception as move_error:
                            self.log(f"❌ เกิดข้อผิดพลาดในการย้ายไฟล์: {move_error}")
                else:
                    self.log(f"❌ {message}")
                    # ลองตรวจสอบ error เพิ่มเติม
                    self.log(f"🔍 ตรวจสอบข้อมูล: แถว {len(combined_df)}, คอลัมน์ {list(combined_df.columns)}")
                
                completed_types += 1
                
            except Exception as e:
                self.log(f"❌ เกิดข้อผิดพลาดขณะอัปโหลดไฟล์ประเภท {logic_type}: {e}")
        
        # อัปเดต progress เป็น 100% เมื่อเสร็จสิ้น
        successfully_uploaded = sum(1 for files in files_by_type.values() for _ in files)  # Count all processed files
        ui_callbacks['update_progress'](1.0, "การอัปโหลดเสร็จสิ้น", f"ประมวลผล {total_files} ไฟล์เสร็จสิ้น")
        self.log("--- 🏁 การอัปโหลดเสร็จสิ้น ---")
        
        # เปิดปุ่มทั้งหมดกลับมา
        ui_callbacks['enable_controls']()
    
    def start_auto_process(self, load_last_path_callback, column_settings):
        """เริ่มการประมวลผลอัตโนมัติ (ประมวลผลไฟล์)"""
        # ตรวจสอบว่ามีโฟลเดอร์ต้นทางหรือไม่
        last_path = load_last_path_callback()
        if not last_path or not os.path.isdir(last_path):
            messagebox.showerror(
                "ข้อผิดพลาด", 
                f"โฟลเดอร์ต้นทางไม่ถูกต้อง: {last_path}\n\nกรุณาเลือกโฟลเดอร์ต้นทางก่อน"
            )
            return
        
        # ตรวจสอบการเชื่อมต่อฐานข้อมูล
        success, message = self.db_service.check_connection()
        if not success:
            messagebox.showerror(
                "ข้อผิดพลาด", 
                f"ไม่สามารถเชื่อมต่อกับฐานข้อมูลได้:\n{message}\n\nกรุณาตรวจสอบการตั้งค่าฐานข้อมูลก่อน"
            )
            return
            
        
        # ตรวจสอบการตั้งค่าประเภทไฟล์
        if not column_settings:
            messagebox.showerror(
                "ข้อผิดพลาด", 
                "ไม่พบการตั้งค่าประเภทไฟล์\n\nกรุณาไปที่แท็บ Settings และเพิ่มประเภทไฟล์ก่อน"
            )
            return
        
        # ยืนยันการทำงาน
        result = messagebox.askyesno(
            "ยืนยันการประมวลผลอัตโนมัติ",
            f"จะดำเนินการประมวลผลอัตโนมัติในโฟลเดอร์:\n{last_path}\n\n"
            "ขั้นตอนการทำงาน:\n"
            "1. ค้นหาไฟล์ข้อมูลทั้งหมด\n"
            "2. ประมวลผลและอัปโหลดไฟล์ทั้งหมด\n"
            "ต้องการดำเนินการหรือไม่?"
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
            ui_callbacks['set_progress_status']("เริ่มการประมวลผลอัตโนมัติ", "กำลังเตรียมระบบ...")
            
            self.log("🤖 เริ่มการประมวลผลอัตโนมัติ")
            self.log(f"📂 โฟลเดอร์ต้นทาง: {folder_path}")
            
            # === ประมวลผลไฟล์หลัก ===
            self.log("=== กำลังประมวลผลไฟล์ ===")
            self._auto_process_main_files(folder_path, ui_callbacks)
            
            self.log("=== 🏁 การประมวลผลอัตโนมัติเสร็จสิ้น ===")
            ui_callbacks['update_progress'](1.0, "การประมวลผลอัตโนมัติเสร็จสิ้น", "ทุกขั้นตอนเสร็จสิ้นเรียบร้อย")
            messagebox.showinfo("สำเร็จ", "การประมวลผลอัตโนมัติเสร็จสิ้นแล้ว")
            
        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดในการประมวลผลอัตโนมัติ: {e}")
            messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาด: {e}")
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
                self.log("ไม่พบไฟล์ข้อมูลในโฟลเดอร์ต้นทาง")
                return
            
            self.log(f"พบไฟล์ข้อมูล {len(data_files)} ไฟล์ กำลังประมวลผล...")
            
            total_files = len(data_files)
            processed_files = 0
            successful_uploads = 0
            
            for file_path in data_files:
                try:
                    processed_files += 1
                    # คำนวณ progress ที่ถูกต้อง (0.0 - 1.0)
                    progress = (processed_files - 1) / total_files  # เริ่มจาก 0
                    
                    # อัปเดตความคืบหน้าแบบละเอียด
                    ui_callbacks['update_progress'](progress, f"กำลังประมวลผล: {os.path.basename(file_path)}", f"ไฟล์ที่ {processed_files} จาก {total_files}")
                    
                    self.log(f"📁 กำลังประมวลผล: {os.path.basename(file_path)}")
                    
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
                        self.log(f"❌ ไม่สามารถระบุประเภทไฟล์: {os.path.basename(file_path)}")
                        continue
                    
                    self.log(f"📋 ระบุประเภทไฟล์: {logic_type}")
                    
                    # อ่านไฟล์
                    success, result = self.file_service.read_excel_file(file_path, logic_type)
                    if not success:
                        self.log(f"❌ ไม่สามารถอ่านไฟล์: {result}")
                        continue
                    
                    df = result
                    
                    # ตรวจสอบคอลัมน์
                    success, result = self.file_service.validate_columns(df, logic_type)
                    if not success:
                        self.log(f"❌ คอลัมน์ไม่ถูกต้อง: {result}")
                        continue
                    
                    # อัปโหลดข้อมูล
                    required_cols = self.file_service.get_required_dtypes(logic_type)
                    
                    # ตรวจสอบว่า required_cols ไม่ว่างเปล่า
                    if not required_cols:
                        self.log(f"❌ ไม่พบการตั้งค่าประเภทข้อมูลสำหรับ {logic_type}")
                        continue
                    
                    # ตรวจสอบว่าข้อมูลไม่ว่างเปล่า
                    if df.empty:
                        self.log(f"❌ ไฟล์ {os.path.basename(file_path)} ไม่มีข้อมูล")
                        continue
                    
                    self.log(f"📊 กำลังอัปโหลดข้อมูล {len(df)} แถว สำหรับประเภท {logic_type}")
                    success, message = self.db_service.upload_data(df, logic_type, required_cols, log_func=self.log)
                    
                    if success:
                        self.log(f"✅ อัปโหลดสำเร็จ: {message}")
                        successful_uploads += 1
                        
                        # ย้ายไฟล์หลังอัปโหลดสำเร็จ
                        try:
                            move_success, move_result = self.file_service.move_uploaded_files([file_path], [logic_type])
                            if move_success:
                                for original_path, new_path in move_result:
                                    self.log(f"📦 ย้ายไฟล์ไปยัง: {os.path.basename(new_path)}")
                            else:
                                self.log(f"❌ ไม่สามารถย้ายไฟล์: {move_result}")
                        except Exception as move_error:
                            self.log(f"❌ เกิดข้อผิดพลาดในการย้ายไฟล์: {move_error}")
                    else:
                        self.log(f"❌ อัปโหลดไม่สำเร็จ: {message}")
                        # ลองตรวจสอบ error เพิ่มเติม
                        self.log(f"🔍 ตรวจสอบข้อมูล: แถว {len(df)}, คอลัมน์ {list(df.columns)}")
                        
                except Exception as e:
                    self.log(f"❌ เกิดข้อผิดพลาดขณะประมวลผล {os.path.basename(file_path)}: {e}")
            
            # อัปเดต progress เป็น 100% เมื่อเสร็จสิ้น
            ui_callbacks['update_progress'](1.0, "การประมวลผลเสร็จสิ้น", f"สำเร็จ {successful_uploads} ไฟล์ จาก {total_files} ไฟล์")
            self.log(f"✅ ประมวลผลไฟล์เสร็จสิ้น: {successful_uploads}/{total_files} ไฟล์สำเร็จ")
            
        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
