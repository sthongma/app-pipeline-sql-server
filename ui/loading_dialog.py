import customtkinter as ctk
import threading
import time
from typing import Callable, Any

class LoadingDialog(ctk.CTkToplevel):
    """Loading dialog สำหรับแสดงสถานะการโหลด"""
    
    def __init__(self, parent, title="กำลังโหลด...", message="กรุณารอสักครู่"):
        super().__init__(parent)
        
        self.parent = parent
        self.result = None
        self.error = None
        self.task_thread = None
        
        # ตั้งค่าหน้าต่าง
        self.title(title)
        self.geometry("350x150")
        self.resizable(False, False)
        self.transient(parent)  # ทำให้เป็น dialog ของ parent
        self.grab_set()  # ทำให้ dialog เป็น modal
        
        # จัดกึ่งกลางหน้าจอ
        self._center_window()
        
        # สร้าง UI
        self._create_ui(message)
        
    def _center_window(self):
        """จัดหน้าต่างให้อยู่กึ่งกลางของ parent window"""
        # รอให้หน้าต่าง update ก่อน
        self.update_idletasks()
        
        # ได้ขนาดของ parent
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # คำนวณตำแหน่งกึ่งกลาง
        x = parent_x + (parent_width // 2) - (350 // 2)
        y = parent_y + (parent_height // 2) - (150 // 2)
        
        self.geometry(f"350x150+{x}+{y}")
        
    def _create_ui(self, message):
        """สร้าง UI ของ dialog"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(main_frame, mode="indeterminate")
        self.progress.pack(pady=(10, 15))
        self.progress.start()
        
        # ข้อความ
        self.message_label = ctk.CTkLabel(
            main_frame, 
            text=message, 
            font=("Arial", 12),
            wraplength=300
        )
        self.message_label.pack(pady=5)
        
        # ปุ่ม Cancel (ซ่อนไว้ก่อน)
        self.cancel_button = ctk.CTkButton(
            main_frame, 
            text="ยกเลิก", 
            command=self._cancel_task,
            width=100
        )
        # ไม่แสดงปุ่ม cancel เพื่อความง่าย
        
    def update_message(self, message):
        """อัพเดทข้อความ"""
        if hasattr(self, 'message_label'):
            self.message_label.configure(text=message)
            
    def run_task(self, task_func: Callable, *args, **kwargs):
        """รันงานใน background thread"""
        def worker():
            try:
                self.result = task_func(*args, **kwargs)
            except Exception as e:
                self.error = e
            finally:
                # ปิด dialog เมื่อเสร็จ
                self.after(100, self._finish_task)
                
        self.task_thread = threading.Thread(target=worker)
        self.task_thread.daemon = True
        self.task_thread.start()
        
    def _finish_task(self):
        """เสร็จสิ้นงานและปิด dialog"""
        self.progress.stop()
        self.grab_release()
        self.destroy()
        
    def _cancel_task(self):
        """ยกเลิกงาน (ถ้าต้องการ)"""
        self.error = "ยกเลิกโดยผู้ใช้"
        self._finish_task()
        
    def get_result(self):
        """คืนค่าผลลัพธ์ของงาน"""
        if self.error:
            raise self.error
        return self.result