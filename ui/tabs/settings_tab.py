"""Settings Tab UI Component"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import pandas as pd
from constants import DatabaseConstants, FileConstants


class SettingsTab:
    def __init__(self, parent, column_settings, dtype_settings, supported_dtypes, callbacks, ui_progress_callback=None, on_all_ui_built=None):
        """
        Initialize Settings Tab
        
        Args:
            parent: Parent widget
            column_settings: Dictionary of column settings
            dtype_settings: Dictionary of dtype settings
            supported_dtypes: List of supported SQL Server data types
            callbacks: Dictionary of callback functions
            ui_progress_callback: Callback for UI building progress
        """
        self.parent = parent
        self.column_settings = column_settings
        self.dtype_settings = dtype_settings
        self.supported_dtypes = supported_dtypes
        self.callbacks = callbacks
        self.ui_progress_callback = ui_progress_callback
        self.on_all_ui_built = on_all_ui_built
        
        # UI variables
        self.dtype_menus = {}
        self.date_format_menus = {}
        
        # แคช UI สำหรับแต่ละประเภทไฟล์
        self.ui_cache = {}
        self.current_file_type = None
        
        # สร้าง UI แบบ step-by-step
        self._create_ui_step_by_step()
    
    def _create_ui_step_by_step(self):
        """สร้าง UI แบบ step-by-step เพื่อไม่บล็อค"""
        if self.ui_progress_callback:
            self.ui_progress_callback("Building Control Panel...")
        
        self.parent.after(10, self._create_control_panel)
    
    def _create_control_panel(self):
        """สร้าง Control Panel"""
        # ปุ่มเพิ่ม/ลบ/บันทึกประเภทไฟล์และ dropdown เลือกประเภทไฟล์
        control_frame = ctk.CTkFrame(self.parent)
        control_frame.pack(fill="x", padx=10, pady=8)
        
        # ปุ่มควบคุมและ dropdown ในแถวเดียวกัน
        button_row = ctk.CTkFrame(control_frame, fg_color="transparent")
        button_row.pack(fill="x", pady=4)
        
        if self.ui_progress_callback:
            self.ui_progress_callback("Building buttons...")
        
        self.parent.after(10, lambda: self._create_buttons(button_row))
    
    def _create_buttons(self, button_row):
        """สร้างปุ่มควบคุม"""
        # ปุ่มควบคุมด้านซ้าย
        add_type_btn = ctk.CTkButton(button_row, text="➕ Add file type", command=self._add_file_type)
        add_type_btn.pack(side="left", padx=5)
        del_type_btn = ctk.CTkButton(button_row, text="➖ Remove file type", command=self._delete_file_type)
        del_type_btn.pack(side="left", padx=5)
        save_dtype_btn = ctk.CTkButton(button_row, text="✅ Save data types", command=self._save_all_dtype_settings)
        save_dtype_btn.pack(side="left", padx=5)
        edit_type_btn = ctk.CTkButton(button_row, text="✏️ Rename file type", command=self._edit_file_type)
        edit_type_btn.pack(side="left", padx=5)
        
        if self.ui_progress_callback:
            self.ui_progress_callback("Building dropdown...")
        
        self.parent.after(10, lambda: self._create_dropdown(button_row))
    
    def _create_dropdown(self, button_row):
        """สร้าง Dropdown"""
        # Dropdown สำหรับเลือกประเภทไฟล์
        self.file_type_var = ctk.StringVar(value="Select a file type...")
        self.file_type_selector = ctk.CTkOptionMenu(
            button_row, 
            variable=self.file_type_var,
            values=["Select a file type..."],
            command=self._on_file_type_selected,
            width=300,
        )
        self.file_type_selector.pack(side="right", padx=5)
        
        if self.ui_progress_callback:
            self.ui_progress_callback("Building content frame...")
        
        self.parent.after(10, self._create_content_frame)
    
    def _create_content_frame(self):
        """สร้าง Content Frame"""
        # สร้าง content frame สำหรับแสดงเนื้อหาของประเภทไฟล์ที่เลือก
        self.content_frame = ctk.CTkFrame(self.parent)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        
        if self.ui_progress_callback:
            self.ui_progress_callback("Loading file type data...")
        
        self.parent.after(10, self._finish_ui_creation)
    
    def _finish_ui_creation(self):
        """เสร็จสิ้นการสร้าง UI"""
        # โหลดข้อมูลประเภทไฟล์ที่มีอยู่
        self.refresh_file_type_tabs()

        if self.ui_progress_callback:
            self.ui_progress_callback("Settings Tab ready")

        # ✅ แจ้ง callback ว่า UI พร้อมแล้วทันที (ไม่ต้องรอ prebuild UI)
        if callable(self.on_all_ui_built):
            try:
                self.parent.after(0, self.on_all_ui_built)
            except Exception:
                self.on_all_ui_built()
    
    def refresh_file_type_tabs(self):
        """รีเฟรช tabs ของประเภทไฟล์ (ไม่ prebuild UI ล่วงหน้า - สร้างเมื่อเลือกเท่านั้น)"""
        # ซิงค์ dtype_settings ก่อนอัปเดต UI
        for file_type in self.column_settings.keys():
            self._sync_dtype_settings(file_type)

        # อัปเดต dropdown ของประเภทไฟล์
        self._update_file_type_selector()

        # ล้าง UI cache เก่าที่ไม่ใช้แล้ว
        self._cleanup_unused_cache()

        # อัปเดต UI ที่แคชไว้ให้ตรงกับข้อมูลใหม่
        self._update_cached_ui()

        # ✅ ลบการ prebuild UI ล่วงหน้า - ให้สร้างเฉพาะเมื่อผู้ใช้เลือกประเภทไฟล์จริงเท่านั้น (Lazy Loading)
    
    def _cleanup_unused_cache(self):
        """ล้าง UI cache ที่ไม่ใช้แล้ว"""
        current_file_types = set(self.column_settings.keys())
        cached_file_types = set(self.ui_cache.keys())
        unused_types = cached_file_types - current_file_types
        
        for file_type in unused_types:
            # ลบ UI elements
            if 'scroll_frame' in self.ui_cache[file_type]:
                self.ui_cache[file_type]['scroll_frame'].destroy()
            
            # ลบจากแคช
            del self.ui_cache[file_type]
            
            # ลบจาก menus
            self.dtype_menus.pop(file_type, None)
            self.date_format_menus.pop(file_type, None)
    
    def _update_cached_ui(self):
        """อัปเดต UI ที่แคชไว้ให้ตรงกับข้อมูลใหม่"""
        for file_type in self.ui_cache.keys():
            # อัปเดต date format menu
            if file_type in self.date_format_menus:
                val = self.dtype_settings.get(file_type, {}).get('_date_format', 'UK')
                self.date_format_menus[file_type].set(val)
    
    def _add_file_type(self):
        """เพิ่มประเภทไฟล์ใหม่โดยเลือกไฟล์ตัวอย่าง"""
        # Popup ให้เลือกไฟล์ตัวอย่างทันที (รองรับทั้ง xlsx/xls/csv)
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Excel/CSV files", "*.xlsx;*.xls;*.csv"), 
                ("Excel XLSX files", "*.xlsx"), 
                ("Excel XLS files", "*.xls"), 
                ("CSV files", "*.csv")
            ]
        )
        if not file_path:
            return
        
        try:
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path, nrows=100, encoding='utf-8')
            elif file_path.lower().endswith('.xls'):
                # สำหรับไฟล์ .xls ใช้ xlrd engine
                df = pd.read_excel(file_path, nrows=100, engine='xlrd')
            else:
                # สำหรับไฟล์ .xlsx
                df = pd.read_excel(file_path, nrows=100)
            
            columns = list(df.columns)
            
            # infer dtype จากข้อมูลจริง
            inferred_dtypes = self._infer_dtypes(df)
            
            # ให้ผู้ใช้ตั้งชื่อประเภทไฟล์ใหม่
            file_type = ctk.CTkInputDialog(text="New file type name:").get_input()
            if not file_type:
                return
            
            if file_type in self.column_settings:
                messagebox.showwarning("Duplicate", "This file type already exists")
                return
            
            self.column_settings[file_type] = {col: col for col in columns}
            # แปลง inferred_dtypes ให้ใช้ target column เป็น key (ในกรณีนี้ source = target)
            self.dtype_settings[file_type] = {col: inferred_dtypes[col] for col in columns}
            
            # บันทึกการตั้งค่า
            if self.callbacks.get('save_column_settings'):
                self.callbacks['save_column_settings']()
            if self.callbacks.get('save_dtype_settings'):
                self.callbacks['save_dtype_settings']()
            
            self.refresh_file_type_tabs()
            messagebox.showinfo("Success", "Imported columns and data types from the sample file")
            
        except Exception as e:
            messagebox.showerror("Error", f"Unable to read file: {e}")
    
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
            messagebox.showinfo("No data", "No file types to remove")
            return
        
        file_types = list(self.column_settings.keys())
        file_type = ctk.CTkInputDialog(
            text=f"Enter the file type name to remove (e.g., {file_types[0]}):"
        ).get_input()
        
        if not file_type or file_type not in self.column_settings:
            return
        
        if messagebox.askyesno("Confirm", f"Remove file type {file_type}?"):
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
            messagebox.showinfo("No data", "No file types to edit")
            return
        
        file_types = list(self.column_settings.keys())
        old_type = ctk.CTkInputDialog(
            text=f"Enter the file type name to edit (e.g., {file_types[0]}):"
        ).get_input()
        
        if not old_type or old_type not in self.column_settings:
            return
        
        new_type = ctk.CTkInputDialog(
            text=f"Enter a new file type name (from: {old_type}):"
        ).get_input()
        
        if not new_type or new_type in self.column_settings:
            messagebox.showwarning("Duplicate", "File type already exists or invalid name")
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
        messagebox.showinfo("Success", f"Renamed file type {old_type} to {new_type}")
    
    def _save_all_dtype_settings(self):
        """บันทึกชนิดข้อมูลสำหรับประเภทไฟล์ที่แสดงอยู่ในขณะนั้น"""
        current_file_type = self.file_type_var.get()
        if current_file_type != "Select a file type..." and current_file_type in self.dtype_menus:
            if current_file_type not in self.dtype_settings:
                self.dtype_settings[current_file_type] = {}

            # บันทึก meta fields ก่อน
            meta_dict = {}

            # 1. Date format
            if hasattr(self, 'date_format_menus') and current_file_type in self.date_format_menus:
                meta_dict["_date_format"] = self.date_format_menus[current_file_type].get()

            # 2. Update strategy
            if hasattr(self, 'strategy_menus') and current_file_type in self.strategy_menus:
                strategy_display = self.strategy_menus[current_file_type].get()
                meta_dict["_update_strategy"] = "upsert" if "Upsert" in strategy_display else "replace"

            # 3. Upsert keys (เก็บไว้ถ้ามี)
            if "_upsert_keys" in self.dtype_settings.get(current_file_type, {}):
                meta_dict["_upsert_keys"] = self.dtype_settings[current_file_type]["_upsert_keys"]

            # ลบ meta fields เก่าออก
            temp_dict = {k: v for k, v in self.dtype_settings[current_file_type].items()
                         if not k.startswith('_')}

            # สร้าง dict ใหม่โดยใส่ meta fields ก่อน
            self.dtype_settings[current_file_type] = meta_dict
            self.dtype_settings[current_file_type].update(temp_dict)

            # บันทึกชนิดข้อมูลแต่ละคอลัมน์ (ใช้ target column เป็น key)
            for source_col, menu in self.dtype_menus[current_file_type].items():
                target_col = self.column_settings[current_file_type][source_col]
                self.dtype_settings[current_file_type][target_col] = menu.get()

            if self.callbacks.get('save_dtype_settings'):
                self.callbacks['save_dtype_settings']()
            messagebox.showinfo("Success", f"Saved data types for {current_file_type}")
        else:
            messagebox.showwarning("Warning", "Please select a file type before saving")
    
    def _on_file_type_selected(self, choice):
        """เมื่อมีการเลือกประเภทไฟล์จาก dropdown"""
        if choice == "Select a file type...":
            return
        self._show_file_type_content(choice)
    
    def _show_file_type_content(self, file_type):
        """แสดงเนื้อหาของประเภทไฟล์ที่เลือก (ใช้แคช UI)"""
        # ถ้าเป็นประเภทไฟล์เดิม ไม่ต้องทำอะไร
        if self.current_file_type == file_type:
            return
            
        # ซ่อน UI เก่า
        self._hide_all_cached_ui()
        
        # ถ้ามี UI แคชอยู่แล้ว ให้แสดง UI นั้น
        if file_type in self.ui_cache:
            self.ui_cache[file_type]['scroll_frame'].pack(fill="both", expand=True, padx=10, pady=(0, 10))
        else:
            # สร้าง UI ใหม่แบบ lazy loading พร้อม loading dialog
            self._create_ui_lazy(file_type)
            
        self.current_file_type = file_type
    
    def _hide_all_cached_ui(self):
        """ซ่อน UI ที่แคชไว้ทั้งหมด"""
        for cached_ui in self.ui_cache.values():
            cached_ui['scroll_frame'].pack_forget()
    
    def _create_ui_lazy(self, file_type):
        """สร้าง UI แบบ lazy loading พร้อม progress indicator"""
        # แสดง loading message
        loading_frame = ctk.CTkFrame(self.content_frame)
        loading_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        loading_label = ctk.CTkLabel(loading_frame, text=f"Building UI for {file_type}...")
        loading_label.pack(expand=True)
        
        # ใช้ after เพื่อสร้าง UI จริงโดยไม่บล็อค
        self.parent.after(10, lambda: self._create_ui_async(file_type, loading_frame))
    
    def _create_ui_async(self, file_type, loading_frame):
        """สร้าง UI จริงแบบ async"""
        try:
            # ลบ loading frame
            loading_frame.destroy()
            
            # สร้าง UI จริง
            self._create_and_cache_ui(file_type)
            
            # แสดง UI ที่สร้างเสร็จ
            self.ui_cache[file_type]['scroll_frame'].pack(fill="both", expand=True, padx=10, pady=(0, 10))
            
        except Exception as e:
            loading_frame.destroy()
            error_frame = ctk.CTkFrame(self.content_frame)
            error_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            ctk.CTkLabel(error_frame, text=f"Error: {e}").pack(expand=True)

    def _create_and_cache_ui(self, file_type):
        """สร้างและแคช UI สำหรับประเภทไฟล์"""
        # สร้าง scrollable frame สำหรับแสดงคอลัมน์
        scroll_frame = ctk.CTkScrollableFrame(self.content_frame, width=820, height=460)

        # --- Date Format Dropdown ---
        date_format_menu = self._create_date_format_section(scroll_frame, file_type)

        # --- Update Strategy Section ---
        strategy_menu = self._create_update_strategy_section(scroll_frame, file_type)

        # --- Column Settings ---
        column_menus = self._create_column_settings_section(scroll_frame, file_type)

        # แคช UI elements
        self.ui_cache[file_type] = {
            'scroll_frame': scroll_frame,
            'date_format_menu': date_format_menu,
            'strategy_menu': strategy_menu,
            'column_menus': column_menus
        }
    
    def _create_date_format_section(self, parent, file_type):
        """สร้างส่วน Date Format"""
        # เพิ่ม outer frame เพื่อครอบและเพิ่มระยะห่าง
        date_outer_frame = ctk.CTkFrame(parent, fg_color="transparent")
        date_outer_frame.pack(fill="x", pady=10, padx=8)
        
        # date_format_frame ที่มีกรอบสีเทาเข้มและมุมโค้งมน
        date_format_frame = ctk.CTkFrame(date_outer_frame, corner_radius=8)
        date_format_frame.pack(fill="x", pady=3, padx=3)
        
        date_format_label = ctk.CTkLabel(
            date_format_frame, 
            text="⏰ Date Format (US / MM-DD or UK / DD-MM)", 
            width=400, 
            anchor="w",
        )
        date_format_label.pack(side="left", padx=(15, 10), pady=12, expand=True, fill="x")
        
        date_format_menu = ctk.CTkOptionMenu(
            date_format_frame,
            values=[FileConstants.DATE_FORMAT_UK, FileConstants.DATE_FORMAT_US],
            width=220,
        )
        date_format_menu.set(
            self.dtype_settings.get(file_type, {}).get("_date_format", FileConstants.DATE_FORMAT_UK)
        )
        date_format_menu.pack(side="right", padx=(0, 15), pady=12)
        
        # เก็บ reference สำหรับบันทึก
        self.date_format_menus[file_type] = date_format_menu

        return date_format_menu

    def _create_update_strategy_section(self, parent, file_type):
        """สร้างส่วน Update Strategy"""
        # เพิ่ม outer frame เพื่อครอบและเพิ่มระยะห่าง
        strategy_outer_frame = ctk.CTkFrame(parent, fg_color="transparent")
        strategy_outer_frame.pack(fill="x", pady=10, padx=8)

        # strategy_frame ที่มีกรอบสีเทาเข้มและมุมโค้งมน
        strategy_frame = ctk.CTkFrame(strategy_outer_frame, corner_radius=8)
        strategy_frame.pack(fill="x", pady=3, padx=3)

        strategy_label = ctk.CTkLabel(
            strategy_frame,
            text="🔄 Update Strategy",
            width=400,
            anchor="w"
        )
        strategy_label.pack(side="left", padx=(15, 10), pady=12, expand=True, fill="x")

        # Container for dropdown and button
        controls_container = ctk.CTkFrame(strategy_frame, fg_color="transparent")
        controls_container.pack(side="right", padx=(0, 15), pady=12)

        # Dropdown
        strategy_menu = ctk.CTkOptionMenu(
            controls_container,
            values=["Replace", "Upsert (Incremental)"],
            width=180,
            command=lambda v: self._on_strategy_changed(file_type, v)
        )
        current_strategy = self.dtype_settings.get(file_type, {}).get(
            '_update_strategy', 'replace'
        )
        strategy_menu.set("Upsert (Incremental)" if current_strategy == "upsert" else "Replace")
        strategy_menu.pack(side="left", padx=(0, 5))

        # Settings button
        settings_btn = ctk.CTkButton(
            controls_container,
            text="⚙️",
            width=40,
            command=lambda: self._open_upsert_keys_dialog(file_type)
        )
        settings_btn.pack(side="left")

        # เก็บ reference
        if not hasattr(self, 'strategy_menus'):
            self.strategy_menus = {}
        if not hasattr(self, 'settings_buttons'):
            self.settings_buttons = {}

        self.strategy_menus[file_type] = strategy_menu
        self.settings_buttons[file_type] = settings_btn

        # Disable settings button if Replace mode
        if current_strategy == "replace":
            settings_btn.configure(state="disabled")

        return strategy_menu

    def _on_strategy_changed(self, file_type, strategy_display_name):
        """เมื่อเปลี่ยน strategy"""
        strategy_value = "upsert" if "Upsert" in strategy_display_name else "replace"

        # Enable/disable settings button
        if file_type in self.settings_buttons:
            if strategy_value == "upsert":
                self.settings_buttons[file_type].configure(state="normal")
            else:
                self.settings_buttons[file_type].configure(state="disabled")

    def _open_upsert_keys_dialog(self, file_type):
        """เปิด dialog สำหรับเลือก upsert keys"""
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title("Upsert Configuration")
        dialog.geometry("400x700")
        dialog.resizable(False, False) 
        dialog.transient(self.parent)
        dialog.grab_set()

        # Header
        header = ctk.CTkLabel(
            dialog,
            text="🔑 Select Upsert Keys",
            font=("", 16, "bold")
        )
        header.pack(pady=20, padx=20)

        # Description
        desc = ctk.CTkLabel(
            dialog,
            text="Selected columns will be used to identify existing records.\n"
                 "Rows matching these keys will be deleted and re-inserted.",
            wraplength=450,
            justify="left"
        )
        desc.pack(pady=10, padx=20)

        # Scrollable frame for checkboxes
        scroll_frame = ctk.CTkScrollableFrame(dialog, width=450, height=350)
        scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Get available columns
        columns = list(self.column_settings.get(file_type, {}).values())
        current_upsert_keys = self.dtype_settings.get(file_type, {}).get('_upsert_keys', [])

        # Create checkboxes
        checkbox_vars = {}
        for col in columns:
            if col == 'updated_at':  # Skip meta columns
                continue

            var = ctk.BooleanVar(value=(col in current_upsert_keys))
            checkbox = ctk.CTkCheckBox(
                scroll_frame,
                text=col,
                variable=var,
                font=("", 12)
            )
            checkbox.pack(anchor="w", pady=5, padx=10)
            checkbox_vars[col] = var

        # Warning
        warning_frame = ctk.CTkFrame(dialog, fg_color=("gray85", "gray25"))
        warning_frame.pack(pady=10, padx=20, fill="x")

        warning_label = ctk.CTkLabel(
            warning_frame,
            text="⚠️ At least one upsert key must be selected for Upsert mode",
            font=("", 11),
            text_color=("orange", "yellow")
        )
        warning_label.pack(pady=10, padx=10)

        # Buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20, padx=20)

        def save_and_close():
            # Collect selected keys
            selected_keys = [col for col, var in checkbox_vars.items() if var.get()]

            # Validate
            if not selected_keys:
                messagebox.showwarning(
                    "Validation Error",
                    "Please select at least one upsert key for Upsert mode",
                    parent=dialog
                )
                return

            # Save to dtype_settings
            if file_type not in self.dtype_settings:
                self.dtype_settings[file_type] = {}

            self.dtype_settings[file_type]['_upsert_keys'] = selected_keys

            messagebox.showinfo(
                "Success",
                f"Upsert keys saved: {', '.join(selected_keys)}",
                parent=dialog
            )
            dialog.destroy()

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            width=100
        )
        cancel_btn.pack(side="left", padx=10)

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=save_and_close,
            width=100
        )
        save_btn.pack(side="left", padx=10)

    def _create_column_settings_section(self, parent, file_type):
        """สร้างส่วนการตั้งค่าคอลัมน์"""
        if file_type not in self.dtype_menus:
            self.dtype_menus[file_type] = {}
        
        supported_dtypes = DatabaseConstants.SUPPORTED_DTYPES
        
        column_menus = {}
        
        for source_col, target_col in self.column_settings.get(file_type, {}).items():
            # เพิ่ม outer frame เพื่อครอบและเพิ่มระยะห่าง
            outer_frame = ctk.CTkFrame(parent, fg_color="transparent")
            outer_frame.pack(fill="x", pady=3, padx=8)
            
            # row_frame ที่มีกรอบสีเทาเข้มและมุมโค้งมน
            row_frame = ctk.CTkFrame(outer_frame, corner_radius=8)
            row_frame.pack(fill="x", pady=3, padx=3)
            
            col_label = ctk.CTkLabel(row_frame, text=source_col, width=400, anchor="w")
            col_label.pack(side="left", padx=(15, 10), pady=12, expand=True, fill="x")
            
            dtype_menu = ctk.CTkOptionMenu(row_frame, values=supported_dtypes, width=220)
            dtype_menu.set(self.dtype_settings.get(file_type, {}).get(target_col, "NVARCHAR(255)"))
            dtype_menu.pack(side="right", padx=(0, 15), pady=12)
            
            self.dtype_menus[file_type][source_col] = dtype_menu
            column_menus[source_col] = dtype_menu
            
        return column_menus
    
    def _update_file_type_selector(self):
        """อัปเดต dropdown ของประเภทไฟล์"""
        file_types = list(self.column_settings.keys()) if self.column_settings else []
        if file_types:
            # เรียงตัวอักษร (alphabetically)
            file_types = sorted(file_types)
            values = ["Select a file type..."] + file_types
            self.file_type_selector.configure(values=values)
            # ถ้ามีเพียงประเภทเดียว ให้เลือกอัตโนมัติ
            if len(file_types) == 1:
                self.file_type_var.set(file_types[0])
                self._show_file_type_content(file_types[0])
            else:
                self.file_type_var.set("Select a file type...")
        else:
            self.file_type_selector.configure(values=["Select a file type..."])
            self.file_type_var.set("Select a file type...")
            # ซ่อน UI ที่แคชไว้ในกรณีไม่มีประเภทไฟล์
            self._hide_all_cached_ui()
            self.current_file_type = None
    
    def _sync_dtype_settings(self, file_type):
        """ซิงค์ dtype_settings ให้ตรงกับ column_settings (เพิ่ม/ลบ key ตาม target column) และเก็บ meta key เช่น _date_format"""
        target_cols = set(self.column_settings.get(file_type, {}).values())
        dtypes = self.dtype_settings.get(file_type, {})
        # เก็บ meta key (ขึ้นต้นด้วย _)
        meta_keys = {k: v for k, v in dtypes.items() if k.startswith('_')}
        # ลบ dtype ที่ไม่มีใน target columns (ยกเว้น meta key)
        dtypes = {col: dtypes[col] for col in target_cols if col in dtypes}
        # เพิ่ม dtype ที่ยังไม่มี
        for col in target_cols:
            if col not in dtypes:
                dtypes[col] = "NVARCHAR(255)"
        # รวม meta key กลับเข้าไป
        dtypes.update(meta_keys)
        self.dtype_settings[file_type] = dtypes
