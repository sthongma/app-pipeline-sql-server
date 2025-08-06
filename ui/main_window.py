import os
import json
import customtkinter as ctk
from tkinter import messagebox
import threading
from datetime import datetime
from ui.components.file_list import FileList
from ui.components.progress_bar import ProgressBar
from ui.components.status_bar import StatusBar
from services.file_service import FileService
from services.database_service import DatabaseService
from services.file_management_service import FileManagementService
from config.database import DatabaseConfig
import pandas as pd
from tkinter import filedialog, simpledialog

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # ตั้งค่าหน้าต่างแอปพลิเคชัน
        self.title("ตรวจสอบและอัปโหลดไฟล์")
        self.geometry("900x800")
        self.resizable(False, False)
        
        # กำหนดประเภทข้อมูลที่รองรับ (SQL Server data types)
        self.supported_dtypes = [
            "VARCHAR(255)",
            "NVARCHAR(100)",
            "NVARCHAR(255)",
            "NVARCHAR(500)",
            "NVARCHAR(1000)",
            "NVARCHAR(MAX)",
            "INT",
            "BIGINT",
            "DECIMAL(18,2)",
            "FLOAT",
            "DATE",
            "DATETIME",
            "BIT"
        ]
        
        # โหลดการตั้งค่าคอลัมน์
        self.settings_file = "config/column_settings.json"
        self.column_settings = self._load_column_settings()
        self.dtype_settings = self._load_dtype_settings()
        
        # โหลดการตั้งค่า SQL Server
        self.db_config = DatabaseConfig()
        self.sql_config = self.db_config.config
        
        # สร้างบริการ
        self.file_service = FileService(log_callback=self.log)
        self.db_service = DatabaseService()
        self.file_mgmt_service = FileManagementService()
        
        # Initialize UI variables
        self.file_type_tabs = {}
        self.column_entries = {}
        self.dtype_menus = {}
        self.date_format_menus = {}
        
        # ตรวจสอบการเชื่อมต่อ SQL Server
        self.check_sql_connection()
        
        # โหลด path ล่าสุด ถ้ามี
        last_path = self._load_last_path()
        if last_path and os.path.isdir(last_path):
            self.file_service.set_search_path(last_path)
        
        # สร้างส่วนประกอบ UI
        self._create_ui()
        
    def _create_ui(self):
        """สร้างส่วนประกอบ UI ทั้งหมด"""
        # สร้าง Tab View
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # สร้าง Tab
        self.main_tab = self.tabview.add("Main")
        self.log_tab = self.tabview.add("Log")
        self.settings_tab = self.tabview.add("Settings")
        
        # สร้างส่วนประกอบในแต่ละ Tab
        self._create_main_tab()
        self._create_log_tab()
        self._create_settings_tab()
        
    def _create_main_tab(self):
        """สร้างส่วนประกอบใน Main Tab"""
        # --- Status Bar ---
        self.status_bar = StatusBar(self.main_tab)
        self.status_bar.pack(pady=10)
        
        # --- Control Buttons (Import/Upload) ---
        self._create_control_buttons()
        
        # --- File List ---
        self.file_list = FileList(self.main_tab, width=850, height=350)
        self.file_list.pack(pady=10)
        
        # --- Progress Bar ---
        self.progress_bar = ProgressBar(self.main_tab)
        self.progress_bar.pack(pady=5, fill="x", padx=10)
        
        # --- Log Textbox ---
        self.textbox = ctk.CTkTextbox(self.main_tab, width=850, height=200)
        self.textbox.pack(pady=10)
        
    def _create_log_tab(self):
        """สร้างส่วนประกอบใน Log Tab"""
        # กล่องข้อความสำหรับแสดง Log
        self.log_textbox = ctk.CTkTextbox(self.log_tab, width=850, height=600)
        self.log_textbox.pack(pady=10, padx=10, fill="both", expand=True)

        # ปุ่มคัดลอก Log
        copy_btn = ctk.CTkButton(
            self.log_tab,
            text="คัดลอก Log",
            command=self._copy_log_to_clipboard
        )
        copy_btn.pack(pady=(0, 0))
        
    def _copy_log_to_clipboard(self):
        """คัดลอกข้อความ log ทั้งหมดไปยัง clipboard"""
        log_text = self.log_textbox.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(log_text)
        self.update()  # เพื่อให้ clipboard ทำงาน
        messagebox.showinfo("คัดลอกแล้ว", "คัดลอก Log เรียบร้อยแล้ว!")
        
    def _create_settings_tab(self):
        """สร้างส่วนประกอบใน Settings Tab (dynamic file types/columns)"""
        # ปุ่มเพิ่ม/ลบ/บันทึกประเภทไฟล์และ dropdown เลือกประเภทไฟล์
        control_frame = ctk.CTkFrame(self.settings_tab)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # ปุ่มควบคุมและ dropdown ในแถวเดียวกัน
        button_row = ctk.CTkFrame(control_frame, fg_color="transparent")
        button_row.pack(fill="x", pady=5)
        
        # ปุ่มควบคุมด้านซ้าย
        add_type_btn = ctk.CTkButton(button_row, text="➕ เพิ่มประเภทไฟล์", command=self._add_file_type)
        add_type_btn.pack(side="left", padx=5)
        del_type_btn = ctk.CTkButton(button_row, text="🗑️ ลบประเภทไฟล์", command=self._delete_file_type)
        del_type_btn.pack(side="left", padx=5)
        save_dtype_btn = ctk.CTkButton(button_row, text="บันทึกชนิดข้อมูล", command=self._save_all_dtype_settings)
        save_dtype_btn.pack(side="left", padx=5)
        edit_type_btn = ctk.CTkButton(button_row, text="✏️ แก้ไขชื่อประเภทไฟล์", command=self._edit_file_type)
        edit_type_btn.pack(side="left", padx=5)
        
        # Dropdown สำหรับเลือกประเภทไฟล์
        self.file_type_var = ctk.StringVar(value="เลือกประเภทไฟล์...")
        self.file_type_selector = ctk.CTkOptionMenu(
            button_row, 
            variable=self.file_type_var,
            values=["เลือกประเภทไฟล์..."],
            command=self._on_file_type_selected,
            width=300
        )
        self.file_type_selector.pack(side="right", padx=5)
        
        # สร้าง content frame สำหรับแสดงเนื้อหาของประเภทไฟล์ที่เลือก
        self.content_frame = ctk.CTkFrame(self.settings_tab)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # โหลดข้อมูลประเภทไฟล์ที่มีอยู่
        self._refresh_file_type_tabs()

    def _refresh_file_type_tabs(self):
        # ซิงค์ dtype_settings ก่อนอัปเดต UI
        for file_type in self.column_settings.keys():
            self._sync_dtype_settings(file_type)
        
        # อัปเดต dropdown ของประเภทไฟล์
        self._update_file_type_selector()
        
        # ล้างข้อมูลเก่า
        if hasattr(self, 'date_format_menus'):
            self.date_format_menus.clear()
        
        # --- sync dropdown กับ config หลังอัปเดต ---
        if hasattr(self, 'date_format_menus'):
            for file_type, menu in self.date_format_menus.items():
                val = self.dtype_settings.get(file_type, {}).get('_date_format', 'UK')
                menu.set(val)

    def _add_file_type(self):
        import tkinter.filedialog as fd
        import pandas as pd
        # Popup ให้เลือกไฟล์ตัวอย่างทันที (รองรับทั้ง xlsx/csv)
        file_path = fd.askopenfilename(filetypes=[("Excel/CSV files", "*.xlsx;*.csv"), ("Excel files", "*.xlsx"), ("CSV files", "*.csv")])
        if not file_path:
            return
        try:
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path, nrows=100, encoding='utf-8')
            else:
                df = pd.read_excel(file_path, nrows=100)
            columns = list(df.columns)
            # infer dtype จากข้อมูลจริง
            inferred_dtypes = {}
            for col in columns:
                dtype = pd.api.types.infer_dtype(df[col], skipna=True)
                if dtype in ["integer", "mixed-integer"]:
                    inferred_dtypes[col] = "INT"
                elif dtype in ["floating", "mixed-integer-float"]:
                    inferred_dtypes[col] = "FLOAT"
                elif dtype == "boolean":
                    inferred_dtypes[col] = "BIT"
                elif dtype.startswith("datetime"):
                    inferred_dtypes[col] = "DATETIME"
                elif dtype == "date":
                    inferred_dtypes[col] = "DATE"
                elif dtype == "string":
                    maxlen = df[col].astype(str).str.len().max()
                    if pd.isna(maxlen) or maxlen < 1 or maxlen < 255:
                        maxlen = 255
                    elif maxlen > 1000:
                        maxlen = "MAX"
                    inferred_dtypes[col] = f"NVARCHAR({maxlen})" if maxlen != "MAX" else "NVARCHAR(MAX)"
                else:
                    inferred_dtypes[col] = "NVARCHAR(255)"
            # ให้ผู้ใช้ตั้งชื่อประเภทไฟล์ใหม่
            file_type = ctk.CTkInputDialog(text="ชื่อประเภทไฟล์ใหม่:").get_input()
            if not file_type:
                return
            if file_type in self.column_settings:
                messagebox.showwarning("ซ้ำ", "มีประเภทไฟล์นี้อยู่แล้ว")
                return
            self.column_settings[file_type] = {col: col for col in columns}
            self.dtype_settings[file_type] = inferred_dtypes
            
            # บันทึกข้อมูลลงไฟล์โดยตรงเพื่อให้แน่ใจว่าจะไม่หายไป
            self._save_column_settings()
            
            # บันทึก dtype_settings โดยตรงลงไฟล์
            try:
                dtype_file = "config/dtype_settings.json"
                os.makedirs(os.path.dirname(dtype_file), exist_ok=True)
                
                # โหลดข้อมูลเดิมก่อน
                existing_dtype_settings = {}
                if os.path.exists(dtype_file):
                    with open(dtype_file, 'r', encoding='utf-8') as f:
                        existing_dtype_settings = json.load(f)
                
                # เพิ่มข้อมูลใหม่
                existing_dtype_settings[file_type] = inferred_dtypes
                
                # บันทึกลงไฟล์
                with open(dtype_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_dtype_settings, f, ensure_ascii=False, indent=2)
                
                # อัปเดต self.dtype_settings จากไฟล์
                self.dtype_settings = self._load_dtype_settings()
                
            except Exception as e:
                self.log(f"ไม่สามารถบันทึกการตั้งค่าประเภทข้อมูลได้: {e}")
            
            self._refresh_file_type_tabs()
            messagebox.showinfo("สำเร็จ", "นำเข้าคอลัมน์และชนิดข้อมูลจากไฟล์ตัวอย่างสำเร็จ!")
        except Exception as e:
            messagebox.showerror("ผิดพลาด", f"ไม่สามารถอ่านไฟล์: {e}")

    def _delete_file_type(self):
        # Popup เลือกประเภทไฟล์ที่จะลบ
        if not self.column_settings:
            messagebox.showinfo("ไม่มีข้อมูล", "ยังไม่มีประเภทไฟล์ให้ลบ")
            return
        file_types = list(self.column_settings.keys())
        # CTkInputDialog ไม่รองรับ initialvalue ให้แสดงชื่อแรกใน text แทน
        file_type = ctk.CTkInputDialog(text=f"พิมพ์ชื่อประเภทไฟล์ที่จะลบ (ตัวอย่าง: {file_types[0]}):").get_input()
        if not file_type or file_type not in self.column_settings:
            return
        if messagebox.askyesno("ยืนยัน", f"ลบประเภทไฟล์ {file_type}?"):
            self.column_settings.pop(file_type)
            self.dtype_settings.pop(file_type, None)
            self._save_column_settings()
            self._save_dtype_settings()
            self._refresh_file_type_tabs()

    def _save_dtype_settings_for_type(self, file_type):
        # อัปเดต dtype_settings จาก dropdown
        if file_type not in self.dtype_settings:
            self.dtype_settings[file_type] = {}
        
        # บันทึก date format ก่อนเป็นอันดับแรก
        if hasattr(self, 'date_format_menus') and file_type in self.date_format_menus:
            # ลบ _date_format เก่าออกก่อน (ถ้ามี) แล้วค่อยเพิ่มใหม่ในตำแหน่งแรก
            temp_dict = self.dtype_settings[file_type].copy()
            if "_date_format" in temp_dict:
                del temp_dict["_date_format"]
            self.dtype_settings[file_type] = {"_date_format": self.date_format_menus[file_type].get()}
            self.dtype_settings[file_type].update(temp_dict)
        
        # จากนั้นค่อยบันทึกคอลัมน์อื่นๆ
        for col, menu in self.dtype_menus[file_type].items():
            self.dtype_settings[file_type][col] = menu.get()
        self._save_dtype_settings()
        messagebox.showinfo("สำเร็จ", f"บันทึกชนิดข้อมูลสำหรับ {file_type} เรียบร้อยแล้ว")

    def _save_all_dtype_settings(self):
        # บันทึกชนิดข้อมูลสำหรับประเภทไฟล์ที่แสดงอยู่ในขณะนั้น
        current_file_type = self.file_type_var.get()
        if current_file_type != "เลือกประเภทไฟล์..." and current_file_type in self.dtype_menus:
            if current_file_type not in self.dtype_settings:
                self.dtype_settings[current_file_type] = {}
            
            # บันทึก date format ก่อนเป็นอันดับแรก
            if hasattr(self, 'date_format_menus') and current_file_type in self.date_format_menus:
                # ลบ _date_format เก่าออกก่อน (ถ้ามี) แล้วค่อยเพิ่มใหม่ในตำแหน่งแรก
                temp_dict = self.dtype_settings[current_file_type].copy()
                if "_date_format" in temp_dict:
                    del temp_dict["_date_format"]
                self.dtype_settings[current_file_type] = {"_date_format": self.date_format_menus[current_file_type].get()}
                self.dtype_settings[current_file_type].update(temp_dict)
            
            # จากนั้นค่อยบันทึกชนิดข้อมูลแต่ละคอลัมน์
            for col, menu in self.dtype_menus[current_file_type].items():
                self.dtype_settings[current_file_type][col] = menu.get()
            
            self._save_dtype_settings()
            messagebox.showinfo("สำเร็จ", f"บันทึกชนิดข้อมูลสำหรับ {current_file_type} เรียบร้อยแล้ว")
        else:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกประเภทไฟล์ก่อนบันทึก")

    def _create_sql_settings_tab(self):
        """สร้างส่วนประกอบใน SQL Server Settings Tab"""
        # สร้างเฟรมสำหรับปุ่ม
        button_frame = ctk.CTkFrame(self.sql_tab)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        # สร้างเฟรมย่อยสำหรับจัดกลุ่มปุ่มให้อยู่ตรงกลาง
        inner_button_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        inner_button_frame.pack(expand=True)
        
        # ปุ่มบันทึก
        save_button = ctk.CTkButton(
            inner_button_frame,
            text="บันทึกการตั้งค่า",
            command=self._save_sql_settings
        )
        save_button.pack(side="left", padx=5)
        
        # ปุ่มทดสอบการเชื่อมต่อ
        test_button = ctk.CTkButton(
            inner_button_frame,
            text="ทดสอบการเชื่อมต่อ",
            command=self._test_sql_connection
        )
        test_button.pack(side="left", padx=5)
        
        # สร้างเฟรมสำหรับฟอร์ม
        form_frame = ctk.CTkFrame(self.sql_tab)
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # สร้าง Entry สำหรับแต่ละการตั้งค่า
        self.sql_entries = {}
        settings = [
            ("server", "ชื่อเซิร์ฟเวอร์"),
            ("database", "ชื่อฐานข้อมูล"),
            ("auth_type", "วิธีการยืนยันตัวตน"),
            ("username", "ชื่อผู้ใช้"),
            ("password", "รหัสผ่าน")
        ]
        
        for i, (key, label) in enumerate(settings):
            # Label
            ctk.CTkLabel(form_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            
            if key == "auth_type":
                # Dropdown สำหรับเลือกวิธีการยืนยันตัวตน
                auth_menu = ctk.CTkOptionMenu(
                    form_frame,
                    values=["Windows", "SQL Server"],
                    width=300,
                    command=self._on_auth_type_change,
                    fg_color="#2B2B2B",  # สีพื้นหลังของปุ่ม
                    button_color="#2B2B2B",  # สีพื้นหลังของปุ่มลูกศร
                    button_hover_color="#404040"  # สีเมื่อ hover ที่ปุ่มลูกศร
                )
                auth_menu.grid(row=i, column=1, padx=5, pady=5, sticky="w")
                auth_menu.set(self.sql_config.get(key, "Windows"))
                self.sql_entries[key] = auth_menu
            else:
                # Entry สำหรับข้อมูลอื่นๆ
                entry = ctk.CTkEntry(form_frame, width=300)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
                entry.insert(0, self.sql_config.get(key, ""))
                
                # ถ้าเป็นรหัสผ่าน ให้ซ่อนข้อความ
                if key == "password":
                    entry.configure(show="*")
                
                self.sql_entries[key] = entry
        
        # อัปเดตสถานะของ username และ password fields
        self._update_auth_fields()
    
    def _on_auth_type_change(self, choice):
        """เมื่อมีการเปลี่ยนวิธีการยืนยันตัวตน"""
        self._update_auth_fields()
    
    def _update_auth_fields(self):
        """อัปเดตสถานะของ username และ password fields"""
        auth_type = self.sql_entries["auth_type"].get()
        username_entry = self.sql_entries["username"]
        password_entry = self.sql_entries["password"]
        
        if auth_type == "Windows":
            # ปิดการใช้งาน username และ password
            username_entry.configure(state="disabled", fg_color="#2B2B2B")
            password_entry.configure(state="disabled", fg_color="#2B2B2B")
        else:
            # เปิดการใช้งาน username และ password
            username_entry.configure(state="normal", fg_color="#343638")
            password_entry.configure(state="normal", fg_color="#343638")
    
    def _save_sql_settings(self):
        """บันทึกการตั้งค่า SQL Server"""
        try:
            # อัปเดตค่าจาก Entry
            for key, entry in self.sql_entries.items():
                if isinstance(entry, ctk.CTkOptionMenu):
                    self.sql_config[key] = entry.get()
                else:
                    self.sql_config[key] = entry.get()
            
            # บันทึกการตั้งค่า
            self.db_service.update_config(
                server=self.sql_config["server"],
                database=self.sql_config["database"],
                auth_type=self.sql_config["auth_type"],
                username=self.sql_config["username"] if self.sql_config["auth_type"] == "SQL Server" else None,
                password=self.sql_config["password"] if self.sql_config["auth_type"] == "SQL Server" else None
            )
            
            messagebox.showinfo("สำเร็จ", "บันทึกการตั้งค่า SQL Server เรียบร้อยแล้ว")
            
            # ทดสอบการเชื่อมต่อใหม่
            self.check_sql_connection()
            
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถบันทึกการตั้งค่าได้: {str(e)}")
    
    def _test_sql_connection(self):
        """ทดสอบการเชื่อมต่อ SQL Server"""
        try:
            # อัปเดตค่าจาก Entry
            for key, entry in self.sql_entries.items():
                if isinstance(entry, ctk.CTkOptionMenu):
                    self.sql_config[key] = entry.get()
                else:
                    self.sql_config[key] = entry.get()
            
            # บันทึกการตั้งค่า
            self.db_service.update_config(
                server=self.sql_config["server"],
                database=self.sql_config["database"],
                auth_type=self.sql_config["auth_type"],
                username=self.sql_config["username"] if self.sql_config["auth_type"] == "SQL Server" else None,
                password=self.sql_config["password"] if self.sql_config["auth_type"] == "SQL Server" else None
            )
            
            # ทดสอบการเชื่อมต่อ
            if self.db_service.test_connection():
                messagebox.showinfo("สำเร็จ", "การเชื่อมต่อ SQL Server สำเร็จ")
            else:
                messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถเชื่อมต่อกับ SQL Server ได้")
                
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาดในการทดสอบการเชื่อมต่อ: {str(e)}")
    
    def _load_column_settings(self):
        """โหลดการตั้งค่าคอลัมน์จากไฟล์"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"ไม่สามารถโหลดการตั้งค่าคอลัมน์ได้: {e}")
        return {}
    
    def _save_column_settings(self):
        """บันทึกการตั้งค่าคอลัมน์ลงไฟล์"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.column_settings, f, ensure_ascii=False, indent=2)
            self.log("บันทึกการตั้งค่าคอลัมน์เรียบร้อย")
        except Exception as e:
            self.log(f"ไม่สามารถบันทึกการตั้งค่าคอลัมน์ได้: {e}")
    
    def _save_dtype_settings(self):
        """บันทึกการตั้งค่าประเภทข้อมูลลงไฟล์ รวมทั้ง _date_format ของแต่ละประเภทไฟล์"""
        try:
            dtype_file = "config/dtype_settings.json"
            os.makedirs(os.path.dirname(dtype_file), exist_ok=True)
            dtype_settings = {}
            for file_type, menus in self.dtype_menus.items():
                # สร้าง dict เปล่าก่อน
                dtype_settings[file_type] = {}
                
                # เพิ่ม _date_format ก่อนเป็นอันดับแรก
                if hasattr(self, 'date_format_menus') and file_type in self.date_format_menus:
                    dtype_settings[file_type]["_date_format"] = self.date_format_menus[file_type].get()
                
                # จากนั้นค่อยเพิ่มคอลัมน์อื่นๆ
                for col, menu in menus.items():
                    dtype_settings[file_type][col] = menu.get()
                    
            with open(dtype_file, 'w', encoding='utf-8') as f:
                json.dump(dtype_settings, f, ensure_ascii=False, indent=2)
            self.log("บันทึกการตั้งค่าประเภทข้อมูลเรียบร้อย")
        except Exception as e:
            self.log(f"ไม่สามารถบันทึกการตั้งค่าประเภทข้อมูลได้: {e}")

    def _load_dtype_settings(self):
        """โหลดการตั้งค่าประเภทข้อมูลจากไฟล์ รวมทั้ง _date_format"""
        try:
            dtype_file = "config/dtype_settings.json"
            if os.path.exists(dtype_file):
                with open(dtype_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # sync date_format_menus ถ้ามี
                    if hasattr(self, 'date_format_menus'):
                        for file_type, d in loaded.items():
                            if file_type in self.date_format_menus and "_date_format" in d:
                                self.date_format_menus[file_type].set(d["_date_format"])
                    return loaded
        except Exception as e:
            self.log(f"ไม่สามารถโหลดการตั้งค่าประเภทข้อมูลได้: {e}")
        return {}

    def _save_columns(self, file_type, show_message=True):
        """บันทึกการตั้งค่าคอลัมน์และประเภทข้อมูล"""
        # ตรวจสอบว่ามีการเปลี่ยนแปลงหรือไม่
        current_settings = {
            col: entry.get()
            for col, entry in self.column_entries[file_type].items()
        }
        
        current_dtypes = {
            col: menu.get()
            for col, menu in self.dtype_menus[file_type].items()
        }
        
        old_settings = self.column_settings.get(file_type, {})
        old_dtypes = self.dtype_settings.get(file_type, {})
        
        # เปรียบเทียบการตั้งค่าเก่าและใหม่
        if current_settings == old_settings and current_dtypes == old_dtypes:
            if show_message:
                messagebox.showinfo("แจ้งเตือน", f"ไม่มีการเปลี่ยนแปลงการตั้งค่าของ {file_type}")
            return
            
        # ถ้ามีการเปลี่ยนแปลง แสดง popup ยืนยัน
        answer = messagebox.askyesno(
            "ยืนยันการบันทึก",
            f"คุณแน่ใจหรือไม่ว่าต้องการบันทึกการเปลี่ยนแปลงของ {file_type}?"
        )
        
        if answer:
            self.column_settings[file_type] = current_settings
            
            # สร้าง dtype_settings ใหม่โดยให้ _date_format อยู่ในตำแหน่งแรก
            new_dtype_settings = {}
            if hasattr(self, 'date_format_menus') and file_type in self.date_format_menus:
                new_dtype_settings["_date_format"] = self.date_format_menus[file_type].get()
            new_dtype_settings.update(current_dtypes)
            self.dtype_settings[file_type] = new_dtype_settings
            
            self._save_column_settings()
            self._save_dtype_settings()
            if show_message:
                messagebox.showinfo("สำเร็จ", "บันทึกการตั้งค่าเรียบร้อยแล้ว")
        
    def _create_control_buttons(self):
        """สร้างปุ่มควบคุมและปุ่มจัดการโฟลเดอร์ในแถวเดียวกัน"""
        button_frame = ctk.CTkFrame(self.main_tab)
        button_frame.pack(pady=5)
        
         # ปุ่มเลือก/ยกเลิกการเลือกทั้งหมด
        self.select_all_var = ctk.BooleanVar(value=False)
        self.select_all_button = ctk.CTkButton(
            button_frame,
            text="เลือกทั้งหมด",
            command=self._toggle_select_all,
            state="disabled"
        )
        self.select_all_button.pack(side="left", padx=5)

        # ปุ่มเลือกโฟลเดอร์
        self.folder_btn = ctk.CTkButton(
            button_frame,
            text="📁 เลือกโฟลเดอร์",
            command=self._browse_excel_path
        )
        self.folder_btn.pack(side="left", padx=5)

        # ปุ่มตรวจสอบไฟล์ในโฟลเดอร์
        self.check_btn = ctk.CTkButton(
            button_frame,
            text="🔍 ตรวจสอบไฟล์ในโฟลเดอร์",
            command=self._run_check_thread,
            width=160
        )
        self.check_btn.pack(side="left", padx=5)

       

        # ปุ่มอัปโหลดไฟล์
        self.upload_button = ctk.CTkButton(
            button_frame,
            text="📤 อัปโหลดไฟล์ที่เลือก",
            command=self._confirm_upload
        )
        self.upload_button.pack(side="left", padx=5)

        # ปุ่มประมวลผลอัตโนมัติ
        self.auto_process_button = ctk.CTkButton(
            button_frame,
            text="🤖 ประมวลผลอัตโนมัติ",
            command=self._start_auto_process,
            width=160
        )
        self.auto_process_button.pack(side="left", padx=5)
        
        # ปุ่มยกเลิกการทำงาน
        self.cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._cancel_operation,
            width=100,
            state="disabled"
        )
        self.cancel_button.pack(side="left", padx=5)
        
        # สร้าง cancellation token สำหรับการยกเลิกการทำงาน
        self.cancellation_token = threading.Event()

    def _cancel_operation(self):
        """ยกเลิกการทำงานที่กำลังดำเนินการอยู่"""
        self.cancellation_token.set()
        self.log("❌ การทำงานถูกยกเลิกโดยผู้ใช้")
        self.after(0, lambda: self.progress_bar.update(0.0, "การทำงานถูกยกเลิก", ""))

    def _start_auto_process(self):
        """เริ่มการประมวลผลอัตโนมัติ (รวม ZIP, ประมวลผลไฟล์, ย้ายไฟล์เก่า)"""
        # ตรวจสอบว่ามีโฟลเดอร์ต้นทางหรือไม่
        last_path = self._load_last_path()
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
        if not self.column_settings:
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
            "1. รวมไฟล์ Excel จากไฟล์ ZIP\n"
            "2. ประมวลผลและอัปโหลดไฟล์ทั้งหมด\n"
            "3. ย้ายไฟล์เก่ามากว่า 90 วันไปถังขยะ\n\n"
            "ต้องการดำเนินการหรือไม่?"
        )
        
        if not result:
            return
        
        # เริ่มการทำงานใน thread แยก
        thread = threading.Thread(target=self._run_auto_process, daemon=True)
        thread.start()
        
        # เปิดปุ่มยกเลิก
        self.cancel_button.configure(state="normal")

    def _run_auto_process(self):
        """รันการประมวลผลอัตโนมัติใน thread แยก"""
        try:
            # รีเซ็ต cancellation token
            self.cancellation_token.clear()
            
            # ปิดปุ่มต่างๆ ระหว่างการทำงาน (เหมือนกับการอัปโหลด)
            self.after(0, lambda: self.auto_process_button.configure(state="disabled"))
            self.after(0, lambda: self.check_btn.configure(state="disabled"))
            self.after(0, lambda: self.upload_button.configure(state="disabled"))
            self.after(0, lambda: self.folder_btn.configure(state="disabled"))
            self.after(0, lambda: self.select_all_button.configure(state="disabled"))
            self.after(0, lambda: self.file_list.disable_all_checkboxes())
            
            # รีเซ็ต progress bar และแสดงสถานะเริ่มต้น
            self.after(0, lambda: self.progress_bar.reset())
            self.after(0, lambda: self.progress_bar.set_status("เริ่มการประมวลผลอัตโนมัติ", "กำลังเตรียมระบบ..."))
            
            last_path = self._load_last_path()
            self.log("🤖 เริ่มการประมวลผลอัตโนมัติ")
            self.log(f"📂 โฟลเดอร์ต้นทาง: {last_path}")
            
            # ตรวจสอบการยกเลิกก่อนเริ่มขั้นตอนที่ 1
            if self.cancellation_token.is_set():
                self.log("❌ การทำงานถูกยกเลิก")
                return
            
            # === ขั้นตอนที่ 1: รวมไฟล์ ZIP ===
            self.log("=== ขั้นตอนที่ 1: รวมไฟล์ ZIP ===")
            self._auto_process_zip_merger(last_path)
            
            # ตรวจสอบการยกเลิกก่อนเริ่มขั้นตอนที่ 2
            if self.cancellation_token.is_set():
                self.log("❌ การทำงานถูกยกเลิก")
                return
            
            # === ขั้นตอนที่ 2: ประมวลผลไฟล์หลัก ===
            self.log("=== ขั้นตอนที่ 2: ประมวลผลไฟล์หลัก ===")
            self._auto_process_main_files(last_path)
            
            # ตรวจสอบการยกเลิกก่อนเริ่มขั้นตอนที่ 3
            if self.cancellation_token.is_set():
                self.log("❌ การทำงานถูกยกเลิก")
                return
            
            # === ขั้นตอนที่ 3: ย้ายไฟล์เก่า ===
            self.log("=== ขั้นตอนที่ 3: ย้ายไฟล์เก่าไปถังขยะ ===")
            self._auto_process_archive_old_files(last_path)
            
            if not self.cancellation_token.is_set():
                self.log("=== 🏁 การประมวลผลอัตโนมัติเสร็จสิ้น ===")
                self.after(0, lambda: self.progress_bar.update(1.0, "การประมวลผลอัตโนมัติเสร็จสิ้น", "ทุกขั้นตอนเสร็จสิ้นเรียบร้อย"))
                self.after(0, lambda: messagebox.showinfo("สำเร็จ", "การประมวลผลอัตโนมัติเสร็จสิ้นแล้ว"))
            else:
                self.log("❌ การทำงานถูกยกเลิก")
                self.after(0, lambda: self.progress_bar.update(0.0, "การทำงานถูกยกเลิก", ""))
            
        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดในการประมวลผลอัตโนมัติ: {e}")
            self.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", f"เกิดข้อผิดพลาด: {e}"))
        finally:
            # เปิดปุ่มกลับมา (เหมือนกับการอัปโหลด)
            self.after(0, lambda: self.auto_process_button.configure(state="normal"))
            self.after(0, lambda: self.check_btn.configure(state="normal"))
            self.after(0, lambda: self.upload_button.configure(state="normal"))
            self.after(0, lambda: self.folder_btn.configure(state="normal"))
            self.after(0, lambda: self.select_all_button.configure(state="normal"))
            self.after(0, lambda: self.file_list.enable_all_checkboxes())
            self.after(0, lambda: self.cancel_button.configure(state="disabled"))

    def _auto_process_zip_merger(self, folder_path):
        """ขั้นตอนที่ 1: รวมไฟล์ ZIP อัตโนมัติ"""
        try:
            # ค้นหาไฟล์ ZIP ในโฟลเดอร์ (รวม subfolder)
            zip_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.zip'):
                        zip_files.append(os.path.join(root, file))
            
            if not zip_files:
                self.log("ไม่พบไฟล์ ZIP ในโฟลเดอร์ต้นทาง ข้ามขั้นตอนนี้")
                return
            
            self.log(f"พบไฟล์ ZIP {len(zip_files)} ไฟล์ กำลังรวมไฟล์ Excel...")
            
            def progress_callback(value, status):
                self.log(f"ความคืบหน้า: {value*100:.1f}% - {status}")
            
            result = self.file_mgmt_service.process_zip_excel_merger(
                folder_path=folder_path,
                progress_callback=progress_callback
            )
            
            if result["success"]:
                self.log("✅ รวมไฟล์ Excel จาก ZIP เสร็จสิ้น")
                if result["saved_files"]:
                    for filename, rows in result["saved_files"]:
                        self.log(f"  บันทึก: {filename} ({rows} แถว)")
            else:
                self.log("⚠️ การรวมไฟล์ ZIP ไม่สำเร็จ แต่จะดำเนินการต่อ")
                
            if result["errors"]:
                for error in result["errors"]:
                    self.log(f"⚠️ ข้อผิดพลาดใน ZIP merger: {error}")
                    
        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดในการรวมไฟล์ ZIP: {e}")
            self.log("จะดำเนินการต่อด้วยการประมวลผลไฟล์หลัก")

    def _auto_process_main_files(self, folder_path):
        """ขั้นตอนที่ 2: ประมวลผลไฟล์หลักอัตโนมัติ"""
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
                    self.after(0, lambda p=progress, f=os.path.basename(file_path), current=processed_files, total=total_files: 
                        self.progress_bar.update(p, f"กำลังประมวลผล: {f}", f"ไฟล์ที่ {current} จาก {total}"))
                    
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
            self.after(0, lambda: self.progress_bar.update(1.0, "การประมวลผลเสร็จสิ้น", f"สำเร็จ {successful_uploads} ไฟล์ จาก {total_files} ไฟล์"))
            self.log(f"✅ ประมวลผลไฟล์เสร็จสิ้น: {successful_uploads}/{total_files} ไฟล์สำเร็จ")
            
        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")

    def _auto_process_archive_old_files(self, folder_path):
        """ขั้นตอนที่ 3: ย้ายไฟล์เก่าไปถังขยะอัตโนมัติ"""
        try:
            # กำหนดโฟลเดอร์ปลายทางในไดร์ D
            archive_path = "D:/Archived_Files"
            
            self.log(f"กำลังย้ายไฟล์เก่ามากว่า 90 วันจาก {folder_path} ไปยัง {archive_path}")
            
            result = self.file_mgmt_service.archive_old_files(
                source_path=folder_path,
                archive_path=archive_path,
                days=90,  # ย้ายไฟล์เก่ามากว่า 90 วัน
                delete_archive_days=90  # ย้ายไฟล์ใน archive ที่เก่ามากว่า 90 วันไปถังขยะ
            )
            
            # แสดงผลลัพธ์
            if result["moved_files"]:
                self.log(f"✅ ย้ายไฟล์ {len(result['moved_files'])} ไฟล์ไปยัง archive")
                
            if result["moved_dirs"]:
                self.log(f"✅ ย้ายโฟลเดอร์ว่าง {len(result['moved_dirs'])} โฟลเดอร์ไปยัง archive")
                
            if result["deleted_files"]:
                self.log(f"🗑️ ย้ายไฟล์เก่า {len(result['deleted_files'])} ไฟล์ไปถังขยะ")
                
            if result["errors"]:
                for error in result["errors"]:
                    self.log(f"⚠️ ข้อผิดพลาดในการจัดการไฟล์: {error}")
            
            self.log("✅ การย้ายไฟล์เก่าเสร็จสิ้น")
            
        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดในการย้ายไฟล์เก่า: {e}")
        
    def log(self, message):
        """เพิ่มข้อความลงในกล่องข้อความพร้อมเวลา"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        formatted_message = f"{timestamp} {message}\n"
        self.after(0, self._update_textbox, formatted_message)
        self.after(0, self._update_log_textbox, formatted_message)
        
    def _update_textbox(self, message):
        """อัปเดตกล่องข้อความในแท็บหลัก"""
        self.textbox.insert("end", message)
        self.textbox.see("end")
        
    def _update_log_textbox(self, message):
        """อัปเดตกล่องข้อความในแท็บ Log"""
        self.log_textbox.insert("end", message)
        self.log_textbox.see("end")
        
    def _run_check_thread(self):
        """เริ่มการตรวจสอบไฟล์ใน thread แยก"""
        thread = threading.Thread(target=self._check_files)
        thread.start()
        
    def _check_files(self):
        """ตรวจสอบไฟล์ใน Path ที่กำหนด"""
        try:
            # รีเซ็ต progress bar และแสดงสถานะเริ่มต้น
            self.progress_bar.reset()
            self.progress_bar.set_status("เริ่มการตรวจสอบไฟล์", "กำลังสแกนโฟลเดอร์...")
            
            # โหลดการตั้งค่าใหม่
            self.file_service.load_settings()
            # ล้างรายการไฟล์เก่า
            self.file_list.clear()
            # ปิดการใช้งานปุ่มเลือกทั้งหมด
            self.select_all_button.configure(state="disabled")
            self.select_all_button.configure(text="เลือกทั้งหมด")
            self.select_all_var.set(False)
            
            # ปิดปุ่มประมวลผลอัตโนมัติระหว่างตรวจสอบไฟล์
            self.auto_process_button.configure(state="disabled")
            
            # ค้นหาไฟล์ Excel/CSV
            self.progress_bar.update(0.2, "กำลังค้นหาไฟล์", "สแกนไฟล์ .xlsx และ .csv...")
            data_files = self.file_service.find_data_files()
            if not data_files:
                self.progress_bar.update(1.0, "การตรวจสอบเสร็จสิ้น", "ไม่พบไฟล์ .xlsx หรือ .csv")
                self.status_bar.update_status("ไม่พบไฟล์ .xlsx หรือ .csv", is_error=True)
                self.log("🤷 ไม่พบไฟล์ .xlsx หรือ .csv ในโฟลเดอร์ที่กำหนด")
                self.log("--- 🏁 ตรวจสอบไฟล์เสร็จสิ้น ---")
                # ปิดปุ่มเลือกทั้งหมดซ้ำอีกครั้งเพื่อความแน่ใจ
                self.select_all_button.configure(state="disabled")
                self.select_all_button.configure(text="เลือกทั้งหมด")
                self.select_all_var.set(False)
                # เปิดปุ่มประมวลผลอัตโนมัติกลับมา
                self.auto_process_button.configure(state="normal")
                return
            found_files_count = 0
            total_files = len(data_files)
            
            for i, file in enumerate(data_files):
                # คำนวณ progress ที่ถูกต้อง (0.2 - 0.8)
                progress = 0.2 + (0.6 * (i / total_files))  # 20% - 80%
                self.progress_bar.update(progress, f"กำลังตรวจสอบไฟล์: {os.path.basename(file)}", f"ไฟล์ที่ {i+1} จาก {total_files}")
                
                logic_type = self.file_service.detect_file_type(file)
                if logic_type:
                    found_files_count += 1
                    self.log(f"✅ พบไฟล์ตรงเงื่อนไข: {os.path.basename(file)} [{logic_type}]")
                    self.file_list.add_file(file, logic_type)
            if found_files_count > 0:
                self.progress_bar.update(1.0, "การตรวจสอบเสร็จสิ้น", f"พบไฟล์ที่ตรงเงื่อนไข {found_files_count} ไฟล์")
                self.status_bar.update_status(f"พบไฟล์ที่ตรงเงื่อนไข {found_files_count} ไฟล์")
                # เปิดการใช้งานปุ่มเลือกทั้งหมด
                self.select_all_button.configure(state="normal")
                # เลือกไฟล์ทั้งหมดอัตโนมัติ
                self.select_all_var.set(True)
                self.file_list.select_all()
                self.select_all_button.configure(text="ยกเลิกการเลือกทั้งหมด")
                # เปิดปุ่มประมวลผลอัตโนมัติกลับมา
                self.auto_process_button.configure(state="normal")
            else:
                self.progress_bar.update(1.0, "การตรวจสอบเสร็จสิ้น", "ไม่พบไฟล์ที่ตรงเงื่อนไข")
                self.status_bar.update_status("ไม่พบไฟล์ที่ตรงเงื่อนไข", is_error=True)
                # ปิดปุ่มเลือกทั้งหมดถ้าไม่พบไฟล์ที่ตรงเงื่อนไข
                self.select_all_button.configure(state="disabled")
                self.select_all_button.configure(text="เลือกทั้งหมด")
                self.select_all_var.set(False)
                # เปิดปุ่มประมวลผลอัตโนมัติกลับมา
                self.auto_process_button.configure(state="normal")
            self.log("--- 🏁 ตรวจสอบไฟล์เสร็จสิ้น ---")
            # เปิดปุ่มประมวลผลอัตโนมัติกลับมา
            self.auto_process_button.configure(state="normal")
        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาดขณะตรวจสอบไฟล์: {e}")
            # เปิดปุ่มประมวลผลอัตโนมัติกลับมาแม้เกิดข้อผิดพลาด
            self.auto_process_button.configure(state="normal")
        
    def _toggle_select_all(self):
        """สลับระหว่างเลือกทั้งหมดและยกเลิกการเลือกทั้งหมด"""
        self.select_all_var.set(not self.select_all_var.get())
        if self.select_all_var.get():
            self.file_list.select_all()
            self.select_all_button.configure(text="ยกเลิกการเลือกทั้งหมด")
        else:
            self.file_list.deselect_all()
            self.select_all_button.configure(text="เลือกทั้งหมด")
            
    def _confirm_upload(self):
        """ยืนยันการอัปโหลดไฟล์ที่เลือก"""
        selected = self.file_list.get_selected_files()
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
            self.progress_bar.reset()
            # ปิดปุ่มที่เกี่ยวข้องระหว่างอัปโหลด
            self.select_all_button.configure(state="disabled")
            self.upload_button.configure(state="disabled")
            self.folder_btn.configure(state="disabled")
            self.check_btn.configure(state="disabled")
            self.auto_process_button.configure(state="disabled")
            self.file_list.disable_all_checkboxes()
            thread = threading.Thread(target=self._upload_selected_files, args=(selected,))
            thread.start()
            
    def _upload_selected_files(self, selected_files):
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
        
        # เก็บรายการไฟล์ที่อัปโหลดสำเร็จและ logic_type
        successfully_uploaded_files = []
        successfully_uploaded_types = []
        
        # แสดงสถานะเริ่มต้น
        self.progress_bar.set_status("เริ่มการอัปโหลด", f"พบไฟล์ {total_files} ไฟล์ จาก {total_types} ประเภท")
        
        for logic_type, files in files_by_type.items():
            try:
                self.log(f"📤 กำลังอัปโหลดไฟล์ประเภท {logic_type}")
                
                # อัปเดต Progress Bar ตามความคืบหน้า
                progress = completed_types / total_types
                self.progress_bar.update(progress, f"กำลังประมวลผลประเภท {logic_type}", f"ประเภทที่ {completed_types + 1} จาก {total_types}")
                
                # รวมข้อมูลจากทุกไฟล์ในประเภทเดียวกัน
                all_dfs = []
                for file_path, chk in files:
                    try:
                        processed_files += 1
                        # คำนวณ progress ที่ถูกต้อง (0.0 - 1.0)
                        file_progress = (processed_files - 1) / total_files  # เริ่มจาก 0
                        
                        # อัปเดตความคืบหน้าระดับไฟล์
                        self.progress_bar.update(file_progress, f"กำลังอ่านไฟล์: {os.path.basename(file_path)}", f"ไฟล์ที่ {processed_files} จาก {total_files}")
                        
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
                self.progress_bar.update(file_progress, f"กำลังรวมข้อมูลประเภท {logic_type}", f"รวม {len(all_dfs)} ไฟล์ เป็น {len(combined_df)} แถว")
                
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
                self.progress_bar.update(file_progress, f"กำลังอัปโหลดข้อมูลประเภท {logic_type}", f"ส่งข้อมูล {len(combined_df)} แถว ไปยัง SQL Server")
                self.log(f"📊 กำลังอัปโหลดข้อมูล {len(combined_df)} แถว สำหรับประเภท {logic_type}")
                success, message = self.db_service.upload_data(combined_df, logic_type, required_cols, log_func=self.log)
                if success:
                    self.log(f"✅ {message}")
                    for file_path, chk in files:
                        self.file_list.disable_checkbox(chk)
                        self.file_list.set_file_uploaded(file_path)
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
                        successfully_uploaded_files.append(file_path)
                        successfully_uploaded_types.append(logic_type)
                else:
                    self.log(f"❌ {message}")
                    # ลองตรวจสอบ error เพิ่มเติม
                    self.log(f"🔍 ตรวจสอบข้อมูล: แถว {len(combined_df)}, คอลัมน์ {list(combined_df.columns)}")
                
                completed_types += 1
                
            except Exception as e:
                self.log(f"❌ เกิดข้อผิดพลาดขณะอัปโหลดไฟล์ประเภท {logic_type}: {e}")
        
        # อัปเดต progress เป็น 100% เมื่อเสร็จสิ้น
        self.progress_bar.update(1.0, "การอัปโหลดเสร็จสิ้น", f"สำเร็จ {len(successfully_uploaded_files)} ไฟล์ จาก {total_files} ไฟล์")
        self.log("--- 🏁 การอัปโหลดเสร็จสิ้น ---")
        
        # เปิดปุ่มทั้งหมดกลับมา
        self.select_all_button.configure(state="normal")
        self.upload_button.configure(state="normal")
        self.folder_btn.configure(state="normal")
        self.check_btn.configure(state="normal")
        self.auto_process_button.configure(state="normal")
        self.file_list.enable_all_checkboxes()
        
    def check_sql_connection(self):
        """ตรวจสอบการเชื่อมต่อกับ SQL Server"""
        success, message = self.db_service.check_connection()
        if success:
            self.log("✅ " + message)
        else:
            self.log("❌ " + message)
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถเชื่อมต่อกับ SQL Server ได้:\n{message}\n\nกรุณาตรวจสอบการเชื่อมต่อและลองใหม่อีกครั้ง")
            self.after(2000, self.destroy)
    
    def _edit_file_type(self):
        # Popup เลือกประเภทไฟล์ที่จะเปลี่ยนชื่อ
        if not self.column_settings:
            messagebox.showinfo("ไม่มีข้อมูล", "ยังไม่มีประเภทไฟล์ให้แก้ไข")
            return
        file_types = list(self.column_settings.keys())
        old_type = ctk.CTkInputDialog(text=f"พิมพ์ชื่อประเภทไฟล์ที่ต้องการแก้ไข (ตัวอย่าง: {file_types[0]}):").get_input()
        if not old_type or old_type not in self.column_settings:
            return
        new_type = ctk.CTkInputDialog(text=f"พิมพ์ชื่อประเภทไฟล์ใหม่ (จาก: {old_type}):").get_input()
        if not new_type or new_type in self.column_settings:
            messagebox.showwarning("ซ้ำ", "มีประเภทไฟล์นี้อยู่แล้วหรือชื่อไม่ถูกต้อง")
            return
        # เปลี่ยนชื่อ key ใน column_settings และ dtype_settings
        self.column_settings[new_type] = self.column_settings.pop(old_type)
        if old_type in self.dtype_settings:
            self.dtype_settings[new_type] = self.dtype_settings.pop(old_type)
        self._save_column_settings()
        self._save_dtype_settings()
        self._refresh_file_type_tabs()
        messagebox.showinfo("สำเร็จ", f"เปลี่ยนชื่อประเภทไฟล์ {old_type} เป็น {new_type} เรียบร้อยแล้ว")
    
    def _sync_dtype_settings(self, file_type):
        """ซิงค์ dtype_settings ให้ตรงกับ column_settings (เพิ่ม/ลบ key ตาม column) และเก็บ meta key เช่น _date_format"""
        cols = set(self.column_settings.get(file_type, {}).keys())
        dtypes = self.dtype_settings.get(file_type, {})
        # เก็บ meta key (ขึ้นต้นด้วย _)
        meta_keys = {k: v for k, v in dtypes.items() if k.startswith('_')}
        # ลบ dtype ที่ไม่มีใน columns (ยกเว้น meta key)
        dtypes = {col: dtypes[col] for col in cols if col in dtypes}
        # เพิ่ม dtype ที่ยังไม่มี
        for col in cols:
            if col not in dtypes:
                dtypes[col] = "NVARCHAR(255)"
        # รวม meta key กลับเข้าไป
        dtypes.update(meta_keys)
        self.dtype_settings[file_type] = dtypes

    def _browse_excel_path(self):
        import tkinter.filedialog as fd
        folder = fd.askdirectory()
        if folder:
            self.file_service.set_search_path(folder)
            self._save_last_path(folder)
            messagebox.showinfo("สำเร็จ", f"ตั้งค่า path สำหรับค้นหาไฟล์ Excel เป็น\n{folder}")

    def _refresh_file_list(self):
        # สมมติว่า FileList มีเมธอด refresh หรือ set_files
        files = self.file_service.find_excel_files()
        if hasattr(self.file_list, 'set_files'):
            self.file_list.set_files(files)
        else:
            # หรือจะรีเฟรชด้วยวิธีอื่นตามที่ใช้งานจริง
            pass

    def _save_last_path(self, path):
        try:
            os.makedirs('config', exist_ok=True)
            with open('config/last_path.json', 'w', encoding='utf-8') as f:
                json.dump({'last_path': path}, f)
        except Exception as e:
            print(f"Save last path error: {e}")

    def _load_last_path(self):
        try:
            with open('config/last_path.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('last_path', None)
        except Exception:
            return None

    def _truncate_tab_name(self, name, max_length=15):
        """ปรับแต่งชื่อ tab ให้สั้นลงเพื่อป้องกันการเบียดกัน"""
        if len(name) <= max_length:
            return name
        return name[:max_length-3] + "..."

    def _on_file_type_selected(self, choice):
        """เมื่อมีการเลือกประเภทไฟล์จาก dropdown"""
        if choice == "เลือกประเภทไฟล์...":
            return
        self._show_file_type_content(choice)
    
    def _show_file_type_content(self, file_type):
        """แสดงเนื้อหาของประเภทไฟล์ที่เลือก"""
        # ลบเนื้อหาเดิม
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # สร้าง scrollable frame สำหรับแสดงคอลัมน์
        scroll_frame = ctk.CTkScrollableFrame(self.content_frame, width=820, height=450)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # --- Date Format Dropdown ---
        # เพิ่ม outer frame เพื่อครอบและเพิ่มระยะห่าง
        date_outer_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        date_outer_frame.pack(fill="x", pady=12, padx=8)
        
        # date_format_frame ที่มีกรอบสีเทาเข้มและมุมโค้งมน
        date_format_frame = ctk.CTkFrame(date_outer_frame, corner_radius=8)
        date_format_frame.pack(fill="x", pady=3, padx=3)
        
        date_format_label = ctk.CTkLabel(date_format_frame, text="Date Format (US/MM-DD-YYYY หรือ UK/DD-MM-YYYY)", width=400, anchor="w")
        date_format_label.pack(side="left", padx=(15, 10), pady=12, expand=True, fill="x")
        
        date_format_menu = ctk.CTkOptionMenu(date_format_frame, values=["UK", "US"], width=200)
        date_format_menu.set(self.dtype_settings.get(file_type, {}).get("_date_format", "UK"))
        date_format_menu.pack(side="right", padx=(0, 15), pady=12)
        
        # เก็บ reference สำหรับบันทึก
        if not hasattr(self, 'date_format_menus'):
            self.date_format_menus = {}
        self.date_format_menus[file_type] = date_format_menu
        # --- End Date Format Dropdown ---
        
        # สร้างฟิลด์สำหรับแต่ละคอลัมน์
        if not hasattr(self, 'dtype_menus'):
            self.dtype_menus = {}
        if file_type not in self.dtype_menus:
            self.dtype_menus[file_type] = {}
        
        supported_dtypes = [
            "NVARCHAR(100)", "NVARCHAR(255)", "NVARCHAR(500)", "NVARCHAR(1000)", "NVARCHAR(MAX)",
            "INT", "FLOAT", "DECIMAL(18,2)", "DATE", "DATETIME", "BIT"
        ]
        
        for col in self.column_settings.get(file_type, {}):
            # เพิ่ม outer frame เพื่อครอบและเพิ่มระยะห่าง
            outer_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            outer_frame.pack(fill="x", pady=3, padx=8)
            
            # row_frame ที่มีกรอบสีเทาเข้มและมุมโค้งมน
            row_frame = ctk.CTkFrame(outer_frame, corner_radius=8)
            row_frame.pack(fill="x", pady=3, padx=3)
            
            col_label = ctk.CTkLabel(row_frame, text=col, width=400, anchor="w")
            col_label.pack(side="left", padx=(15, 10), pady=12, expand=True, fill="x")
            
            dtype_menu = ctk.CTkOptionMenu(row_frame, values=supported_dtypes, width=200)
            dtype_menu.set(self.dtype_settings.get(file_type, {}).get(col, "NVARCHAR(255)"))
            dtype_menu.pack(side="right", padx=(0, 15), pady=12)
            
            self.dtype_menus[file_type][col] = dtype_menu
    
    def _update_file_type_selector(self):
        """อัปเดต dropdown ของประเภทไฟล์"""
        if hasattr(self, 'file_type_selector'):
            file_types = list(self.column_settings.keys()) if self.column_settings else []
            if file_types:
                values = ["เลือกประเภทไฟล์..."] + file_types
                self.file_type_selector.configure(values=values)
                # ถ้ามีเพียงประเภทเดียว ให้เลือกอัตโนมัติ
                if len(file_types) == 1:
                    self.file_type_var.set(file_types[0])
                    self._show_file_type_content(file_types[0])
                else:
                    self.file_type_var.set("เลือกประเภทไฟล์...")
            else:
                self.file_type_selector.configure(values=["เลือกประเภทไฟล์..."])
                self.file_type_var.set("เลือกประเภทไฟล์...")
                # ลบเนื้อหาในกรณีไม่มีประเภทไฟล์
                if hasattr(self, 'content_frame'):
                    for widget in self.content_frame.winfo_children():
                        widget.destroy()