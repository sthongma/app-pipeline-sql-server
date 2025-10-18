import os
import customtkinter as ctk
from tkinter import ttk
from datetime import datetime
import logging
from constants import UIConstants

class FileList(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.file_checkboxes = []
        self.select_all_var = ctk.BooleanVar(value=False)

    def clear(self):
        """Clear all checkbox items"""
        for widget in self.winfo_children():
            widget.destroy()
        self.file_checkboxes.clear()

    def add_file(self, file_path, logic_type):
        """Add checkbox for found file"""
        # ดึงเวลาที่ไฟล์ถูกสร้าง
        created_time = datetime.fromtimestamp(os.path.getctime(file_path))
        created_time_str = created_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # สร้าง frame สำหรับจัดวาง
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", pady=6, padx=4)
        frame.grid_columnconfigure(2, weight=1)  # ให้คอลัมน์ชื่อไฟล์ยืดหยุ่น
        
        # checkbox
        var = ctk.IntVar()
        chk = ctk.CTkCheckBox(
            frame,
            text="",
            variable=var,
            width=28
        )
        chk.grid(row=0, column=0, padx=(5, 10))
        
        # ประเภทไฟล์ (สีฟ้า ตัวใหญ่ ตัวหนา)
        type_label = ctk.CTkLabel(
            frame,
            text=logic_type.upper(),
            text_color=UIConstants.COLOR_PRIMARY_BLUE,
        )
        type_label.grid(row=0, column=1, padx=(0, 20), sticky="w")
        
        # ชื่อไฟล์ (ตรงกลาง)
        filename_label = ctk.CTkLabel(
            frame,
            text=os.path.basename(file_path),
        )
        filename_label.grid(row=0, column=2, sticky="w")
        
        # เวลาที่สร้างไฟล์
        time_label = ctk.CTkLabel(
            frame,
            text=f"Created at: {created_time_str}",
            text_color=UIConstants.COLOR_SECONDARY_GRAY,
        )
        time_label.grid(row=0, column=3, padx=(10, 5), sticky="e")

        # เก็บ reference ทั้ง checkbox, type_label และ filename_label
        self.file_checkboxes.append((var, (file_path, logic_type), chk, type_label, filename_label))

    def get_selected_files(self):
        """ดึงรายการไฟล์ที่ถูกเลือก"""
        return [(entry, chk) for var, entry, chk, *_ in self.file_checkboxes if var.get() == 1]

    def select_all(self):
        """เลือกไฟล์ทั้งหมด"""
        for var, entry, chk, *_ in self.file_checkboxes:
            if chk.winfo_exists() and chk.cget("state") != "disabled":
                var.set(1)

    def deselect_all(self):
        """ยกเลิกการเลือกไฟล์ทั้งหมด"""
        for var, entry, chk, *_ in self.file_checkboxes:
            if chk.winfo_exists() and chk.cget("state") != "disabled":
                var.set(0)

    def disable_checkbox(self, chk_widget):
        """ปิดการใช้งานช่องติ๊ก"""
        try:
            if chk_widget and chk_widget.winfo_exists():
                chk_widget.configure(state="disabled", text_color="gray")
                for v, entry, chk, *_ in self.file_checkboxes:
                    if chk == chk_widget:
                        v.set(0)
                        break
        except Exception as e:
            logging.error(f"Error disabling checkbox: {e}")

    def set_file_uploaded(self, file_path):
        """เปลี่ยน type_label และชื่อไฟล์เป็นสีเทาเมื่ออัปโหลดแล้ว"""
        for var, (fpath, logic_type), chk, type_label, filename_label in self.file_checkboxes:
            if os.path.basename(fpath) == os.path.basename(file_path):
                # เปลี่ยนสี type_label และ filename_label เป็นสีเทา
                type_label.configure(text_color=UIConstants.COLOR_TEXT_LIGHT)
                filename_label.configure(text_color=UIConstants.COLOR_TEXT_LIGHT)
                break

    def disable_all_checkboxes(self):
        """ปิดการใช้งานช่องติ๊กทั้งหมดชั่วคราว"""
        for var, entry, chk, *_ in self.file_checkboxes:
            if chk.winfo_exists() and chk.cget("state") != "disabled":
                chk.configure(state="disabled")

    def enable_all_checkboxes(self):
        """เปิดการใช้งานช่องติ๊กทั้งหมด (ยกเว้นไฟล์ที่อัปโหลดแล้ว)"""
        for var, _, chk, _, filename_label in self.file_checkboxes:
            if chk.winfo_exists() and chk.cget("state") == "disabled":
                # เปิดเฉพาะไฟล์ที่ยังไม่ถูกอัปโหลด (เช็คจากสีของ filename_label)
                is_uploaded = filename_label.cget("text_color") == UIConstants.COLOR_TEXT_LIGHT
                if not is_uploaded:
                    chk.configure(state="normal")