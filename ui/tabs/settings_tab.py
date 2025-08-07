"""Settings Tab UI Component"""
import os
import json
import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd


class SettingsTab:
    def __init__(self, parent, column_settings, dtype_settings, supported_dtypes, callbacks):
        """
        Initialize Settings Tab
        
        Args:
            parent: Parent widget
            column_settings: Dictionary of column settings
            dtype_settings: Dictionary of dtype settings
            supported_dtypes: List of supported SQL Server data types
            callbacks: Dictionary of callback functions
        """
        self.parent = parent
        self.column_settings = column_settings
        self.dtype_settings = dtype_settings
        self.supported_dtypes = supported_dtypes
        self.callbacks = callbacks
        
        # UI variables
        self.dtype_menus = {}
        self.date_format_menus = {}
        
        # Create UI components
        self._create_ui()
    
    def _create_ui(self):
        """สร้างส่วนประกอบใน Settings Tab (dynamic file types/columns)"""
        # ปุ่มเพิ่ม/ลบ/บันทึกประเภทไฟล์และ dropdown เลือกประเภทไฟล์
        control_frame = ctk.CTkFrame(self.parent)
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
        self.content_frame = ctk.CTkFrame(self.parent)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # โหลดข้อมูลประเภทไฟล์ที่มีอยู่
        self.refresh_file_type_tabs()
    
    def refresh_file_type_tabs(self):
        """รีเฟรช tabs ของประเภทไฟล์"""
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
        """เพิ่มประเภทไฟล์ใหม่โดยเลือกไฟล์ตัวอย่าง"""
        # Popup ให้เลือกไฟล์ตัวอย่างทันที (รองรับทั้ง xlsx/csv)
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel/CSV files", "*.xlsx;*.csv"), ("Excel files", "*.xlsx"), ("CSV files", "*.csv")]
        )
        if not file_path:
            return
        
        try:
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path, nrows=100, encoding='utf-8')
            else:
                df = pd.read_excel(file_path, nrows=100)
            
            columns = list(df.columns)
            
            # infer dtype จากข้อมูลจริง
            inferred_dtypes = self._infer_dtypes(df)
            
            # ให้ผู้ใช้ตั้งชื่อประเภทไฟล์ใหม่
            file_type = ctk.CTkInputDialog(text="ชื่อประเภทไฟล์ใหม่:").get_input()
            if not file_type:
                return
            
            if file_type in self.column_settings:
                messagebox.showwarning("ซ้ำ", "มีประเภทไฟล์นี้อยู่แล้ว")
                return
            
            self.column_settings[file_type] = {col: col for col in columns}
            self.dtype_settings[file_type] = inferred_dtypes
            
            # บันทึกการตั้งค่า
            if self.callbacks.get('save_column_settings'):
                self.callbacks['save_column_settings']()
            if self.callbacks.get('save_dtype_settings'):
                self.callbacks['save_dtype_settings']()
            
            self.refresh_file_type_tabs()
            messagebox.showinfo("สำเร็จ", "นำเข้าคอลัมน์และชนิดข้อมูลจากไฟล์ตัวอย่างสำเร็จ!")
            
        except Exception as e:
            messagebox.showerror("ผิดพลาด", f"ไม่สามารถอ่านไฟล์: {e}")
    
    def _infer_dtypes(self, df):
        """อนุมานประเภทข้อมูลจาก DataFrame"""
        inferred_dtypes = {}
        for col in df.columns:
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
        return inferred_dtypes
    
    def _delete_file_type(self):
        """ลบประเภทไฟล์"""
        if not self.column_settings:
            messagebox.showinfo("ไม่มีข้อมูล", "ยังไม่มีประเภทไฟล์ให้ลบ")
            return
        
        file_types = list(self.column_settings.keys())
        file_type = ctk.CTkInputDialog(
            text=f"พิมพ์ชื่อประเภทไฟล์ที่จะลบ (ตัวอย่าง: {file_types[0]}):"
        ).get_input()
        
        if not file_type or file_type not in self.column_settings:
            return
        
        if messagebox.askyesno("ยืนยัน", f"ลบประเภทไฟล์ {file_type}?"):
            self.column_settings.pop(file_type)
            self.dtype_settings.pop(file_type, None)
            
            if self.callbacks.get('save_column_settings'):
                self.callbacks['save_column_settings']()
            if self.callbacks.get('save_dtype_settings'):
                self.callbacks['save_dtype_settings']()
            
            self.refresh_file_type_tabs()
    
    def _edit_file_type(self):
        """แก้ไขชื่อประเภทไฟล์"""
        if not self.column_settings:
            messagebox.showinfo("ไม่มีข้อมูล", "ยังไม่มีประเภทไฟล์ให้แก้ไข")
            return
        
        file_types = list(self.column_settings.keys())
        old_type = ctk.CTkInputDialog(
            text=f"พิมพ์ชื่อประเภทไฟล์ที่ต้องการแก้ไข (ตัวอย่าง: {file_types[0]}):"
        ).get_input()
        
        if not old_type or old_type not in self.column_settings:
            return
        
        new_type = ctk.CTkInputDialog(
            text=f"พิมพ์ชื่อประเภทไฟล์ใหม่ (จาก: {old_type}):"
        ).get_input()
        
        if not new_type or new_type in self.column_settings:
            messagebox.showwarning("ซ้ำ", "มีประเภทไฟล์นี้อยู่แล้วหรือชื่อไม่ถูกต้อง")
            return
        
        # เปลี่ยนชื่อ key ใน column_settings และ dtype_settings
        self.column_settings[new_type] = self.column_settings.pop(old_type)
        if old_type in self.dtype_settings:
            self.dtype_settings[new_type] = self.dtype_settings.pop(old_type)
        
        if self.callbacks.get('save_column_settings'):
            self.callbacks['save_column_settings']()
        if self.callbacks.get('save_dtype_settings'):
            self.callbacks['save_dtype_settings']()
        
        self.refresh_file_type_tabs()
        messagebox.showinfo("สำเร็จ", f"เปลี่ยนชื่อประเภทไฟล์ {old_type} เป็น {new_type} เรียบร้อยแล้ว")
    
    def _save_all_dtype_settings(self):
        """บันทึกชนิดข้อมูลสำหรับประเภทไฟล์ที่แสดงอยู่ในขณะนั้น"""
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
            
            if self.callbacks.get('save_dtype_settings'):
                self.callbacks['save_dtype_settings']()
            messagebox.showinfo("สำเร็จ", f"บันทึกชนิดข้อมูลสำหรับ {current_file_type} เรียบร้อยแล้ว")
        else:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกประเภทไฟล์ก่อนบันทึก")
    
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
        self._create_date_format_section(scroll_frame, file_type)
        
        # --- Column Settings ---
        self._create_column_settings_section(scroll_frame, file_type)
    
    def _create_date_format_section(self, parent, file_type):
        """สร้างส่วน Date Format"""
        # เพิ่ม outer frame เพื่อครอบและเพิ่มระยะห่าง
        date_outer_frame = ctk.CTkFrame(parent, fg_color="transparent")
        date_outer_frame.pack(fill="x", pady=12, padx=8)
        
        # date_format_frame ที่มีกรอบสีเทาเข้มและมุมโค้งมน
        date_format_frame = ctk.CTkFrame(date_outer_frame, corner_radius=8)
        date_format_frame.pack(fill="x", pady=3, padx=3)
        
        date_format_label = ctk.CTkLabel(
            date_format_frame, 
            text="Date Format (US/MM-DD-YYYY หรือ UK/DD-MM-YYYY)", 
            width=400, 
            anchor="w"
        )
        date_format_label.pack(side="left", padx=(15, 10), pady=12, expand=True, fill="x")
        
        date_format_menu = ctk.CTkOptionMenu(date_format_frame, values=["UK", "US"], width=200)
        date_format_menu.set(self.dtype_settings.get(file_type, {}).get("_date_format", "UK"))
        date_format_menu.pack(side="right", padx=(0, 15), pady=12)
        
        # เก็บ reference สำหรับบันทึก
        self.date_format_menus[file_type] = date_format_menu
    
    def _create_column_settings_section(self, parent, file_type):
        """สร้างส่วนการตั้งค่าคอลัมน์"""
        if file_type not in self.dtype_menus:
            self.dtype_menus[file_type] = {}
        
        supported_dtypes = [
            "NVARCHAR(100)", "NVARCHAR(255)", "NVARCHAR(500)", "NVARCHAR(1000)", "NVARCHAR(MAX)",
            "INT", "FLOAT", "DECIMAL(18,2)", "DATE", "DATETIME", "BIT"
        ]
        
        for col in self.column_settings.get(file_type, {}):
            # เพิ่ม outer frame เพื่อครอบและเพิ่มระยะห่าง
            outer_frame = ctk.CTkFrame(parent, fg_color="transparent")
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
            for widget in self.content_frame.winfo_children():
                widget.destroy()
    
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
