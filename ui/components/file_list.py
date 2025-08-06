import os
import customtkinter as ctk
from tkinter import ttk
from datetime import datetime

class FileList(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            scrollbar_button_color="#2B2B2B",  # สีเดียวกับพื้นหลัง
            scrollbar_button_hover_color="#2B2B2B",  # สีเดียวกับพื้นหลัง
            **kwargs
        )
        self.file_checkboxes = []
        self.select_all_var = ctk.BooleanVar(value=False)

    def clear(self):
        """ล้างรายการช่องติ๊กทั้งหมด"""
        for widget in self.winfo_children():
            widget.destroy()
        self.file_checkboxes.clear()

    def add_file(self, file_path, logic_type):
        """เพิ่มช่องติ๊กสำหรับไฟล์ที่พบ"""
        # ดึงเวลาที่ไฟล์ถูกสร้าง
        created_time = datetime.fromtimestamp(os.path.getctime(file_path))
        created_time_str = created_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # สร้าง frame สำหรับจัดวาง
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        frame.grid_columnconfigure(2, weight=1)  # ให้คอลัมน์ชื่อไฟล์ยืดหยุ่น
        
        # checkbox
        var = ctk.IntVar()
        chk = ctk.CTkCheckBox(
            frame,
            text="",
            variable=var,
            width=30
        )
        chk.grid(row=0, column=0, padx=(5, 10))
        
        # ประเภทไฟล์ (สีฟ้า ตัวใหญ่ ตัวหนา)
        type_label = ctk.CTkLabel(
            frame,
            text=logic_type.upper(),
            text_color="#2B86F5",  # สีฟ้าเดียวกับปุ่ม
            font=("Arial Bold", 12)  # ตัวหนา
        )
        type_label.grid(row=0, column=1, padx=(0, 20), sticky="w")
        
        # ชื่อไฟล์ (ตรงกลาง)
        filename_label = ctk.CTkLabel(
            frame,
            text=os.path.basename(file_path)
        )
        filename_label.grid(row=0, column=2, sticky="w")
        
        # เวลาที่สร้างไฟล์
        time_label = ctk.CTkLabel(
            frame,
            text=f"สร้างเมื่อ: {created_time_str}",
            text_color="#666666"  # สีเทาเข้ม
        )
        time_label.grid(row=0, column=3, padx=(10, 5), sticky="e")
        
        self.file_checkboxes.append((var, (file_path, logic_type), chk))

    def get_selected_files(self):
        """ดึงรายการไฟล์ที่ถูกเลือก"""
        return [(entry, chk) for var, entry, chk in self.file_checkboxes if var.get() == 1]

    def select_all(self):
        """เลือกไฟล์ทั้งหมด"""
        for var, entry, chk in self.file_checkboxes:
            if chk.winfo_exists() and chk.cget("state") != "disabled":
                var.set(1)

    def deselect_all(self):
        """ยกเลิกการเลือกไฟล์ทั้งหมด"""
        for var, entry, chk in self.file_checkboxes:
            if chk.winfo_exists() and chk.cget("state") != "disabled":
                var.set(0)

    def disable_checkbox(self, chk_widget):
        """ปิดการใช้งานช่องติ๊ก"""
        try:
            if chk_widget and chk_widget.winfo_exists():
                chk_widget.configure(state="disabled", text_color="gray")
                for v, entry, chk in self.file_checkboxes:
                    if chk == chk_widget:
                        v.set(0)
                        break
        except Exception as e:
            print(f"Error disabling checkbox: {e}")

    def set_file_uploaded(self, file_path):
        """เปลี่ยนชื่อไฟล์เป็นสีเทาเมื่ออัปโหลดแล้ว"""
        for var, (fpath, logic_type), chk in self.file_checkboxes:
            if os.path.basename(fpath) == os.path.basename(file_path):
                parent = chk.master
                for widget in parent.winfo_children():
                    if isinstance(widget, ctk.CTkLabel) and widget.cget("text") == os.path.basename(file_path):
                        widget.configure(text_color="#888888")  # สีเทา
                        break

    def disable_all_checkboxes(self):
        """ปิดการใช้งานช่องติ๊กทั้งหมดชั่วคราว"""
        for var, entry, chk in self.file_checkboxes:
            if chk.winfo_exists() and chk.cget("state") != "disabled":
                chk.configure(state="disabled")

    def enable_all_checkboxes(self):
        """เปิดการใช้งานช่องติ๊กทั้งหมด (ยกเว้นไฟล์ที่อัปโหลดแล้ว)"""
        for var, (file_path, logic_type), chk in self.file_checkboxes:
            if chk.winfo_exists() and chk.cget("state") == "disabled":
                # เปิดเฉพาะไฟล์ที่ยังไม่ถูกอัปโหลด (ชื่อไฟล์ไม่เป็นสีเทา)
                parent = chk.master
                is_uploaded = False
                for widget in parent.winfo_children():
                    if isinstance(widget, ctk.CTkLabel) and widget.cget("text") == os.path.basename(file_path):
                        if widget.cget("text_color") == "#888888":
                            is_uploaded = True
                        break
                if not is_uploaded:
                    chk.configure(state="normal")