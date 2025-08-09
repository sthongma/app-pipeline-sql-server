import customtkinter as ctk
import threading
import time
from typing import Callable, Any

class LoadingDialog(ctk.CTkToplevel):
    """Loading dialog สำหรับแสดงสถานะการโหลด พร้อมรายการขั้นตอน, เคล็ดลับ และเวลา"""
    
    def __init__(
        self,
        parent,
        title: str = "กำลังโหลด...",
        message: str = "กรุณารอสักครู่",
        min_display_ms: int = 600,
        steps: list | None = None,
        show_tips: bool = True,
        tips: list | None = None,
    ):
        super().__init__(parent)
        
        self.parent = parent
        self.result = None
        self.error = None
        self.task_thread = None
        self._min_display_ms = int(min_display_ms)
        self._start_ts = None
        self.steps = steps or []
        self._step_labels = []
        self._current_step_index = None
        self._show_tips = bool(show_tips)
        self._tips = tips or [
            "เคล็ดลับ: คุณสามารถปรับธีม UI ได้จาก Settings",
            "เคล็ดลับ: ตั้งค่า Date Format ให้ตรงกับไฟล์ใน Settings",
            "เคล็ดลับ: ใช้ ‘ประมวลผลอัตโนมัติ’ เพื่อลดขั้นตอน",
            "เคล็ดลับ: ตรวจสอบชนิดข้อมูลให้ตรงกับคอลัมน์ก่อนอัปโหลด",
        ]
        self._tip_index = 0
        
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
        self._start_ts = time.perf_counter()
        
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
        main_frame.pack(expand=True, fill="both", padx=20, pady=16)
        
        # หัวเรื่อง
        self.title_label = ctk.CTkLabel(main_frame, text=self.title(), font=("Arial", 16, "bold"))
        self.title_label.pack(pady=(0, 6))
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(main_frame, mode="indeterminate")
        self.progress.pack(pady=(6, 10), fill="x")
        self.progress.start()
        
        # เพิ่มการอัพเดท UI เป็นระยะ เพื่อให้ progress bar วิ่งได้
        self._schedule_ui_update()
        
        # ข้อความ
        self.message_label = ctk.CTkLabel(
            main_frame, 
            text=message, 
            font=("Arial", 12),
            wraplength=300
        )
        self.message_label.pack(pady=(2, 8))

        # กล่องขั้นตอนการทำงาน
        if self.steps:
            self.steps_frame = ctk.CTkFrame(main_frame)
            self.steps_frame.pack(fill="x", pady=(0, 6))
            for step_text in self.steps:
                row = ctk.CTkFrame(self.steps_frame, fg_color="transparent")
                row.pack(fill="x", pady=1)
                icon = ctk.CTkLabel(row, text="○", width=16)
                icon.pack(side="left", padx=(2, 6))
                lbl = ctk.CTkLabel(row, text=step_text, anchor="w")
                lbl.pack(side="left", fill="x", expand=True)
                self._step_labels.append((icon, lbl))

        # เวลาและเคล็ดลับ
        bottom_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(4, 0))
        self.elapsed_label = ctk.CTkLabel(bottom_frame, text="เวลา: 0.0 วินาที", text_color="#888888")
        self.elapsed_label.pack(side="left")
        if self._show_tips and self._tips:
            self.tip_label = ctk.CTkLabel(bottom_frame, text=self._tips[0], text_color="#888888")
            self.tip_label.pack(side="right")
            self._schedule_tip_rotation()
        
        # อัพเดทเวลา
        self._schedule_elapsed_update()
        
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
        try:
            if hasattr(self, 'message_label') and self.message_label and self.winfo_exists():
                self.message_label.configure(text=message)
                # เดาและอัพเดทสถานะขั้นตอนจากข้อความ
                self._infer_step_from_message(str(message))
        except Exception:
            pass

    def set_steps(self, steps: list[str]):
        """กำหนดรายการขั้นตอนใหม่"""
        self.steps = steps or []
        # ล้างของเดิมและสร้างใหม่หากต้องการ (ขอข้ามเพื่อความเรียบง่าย)
        
    def mark_step_running(self, index: int):
        if 0 <= index < len(self._step_labels):
            self._current_step_index = index
            icon, _ = self._step_labels[index]
            icon.configure(text="●")

    def mark_step_done(self, index: int):
        if 0 <= index < len(self._step_labels):
            icon, _ = self._step_labels[index]
            icon.configure(text="✓")

    def mark_step_error(self, index: int):
        if 0 <= index < len(self._step_labels):
            icon, _ = self._step_labels[index]
            icon.configure(text="✗")
            
    def run_task(self, task_func: Callable, *args, **kwargs):
        """รันงานใน background thread"""
        def worker():
            try:
                # ถ้า task_func รองรับ progress_callback ให้ส่งไป
                if 'progress_callback' in task_func.__code__.co_varnames:
                    self.result = task_func(*args, progress_callback=self.update_message, **kwargs)
                else:
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
        try:
            # รอให้แสดงผลขั้นต่ำเพื่อ UX ที่นุ่มนวล
            elapsed_ms = 0
            if self._start_ts is not None:
                elapsed_ms = int((time.perf_counter() - self._start_ts) * 1000)
            if elapsed_ms < self._min_display_ms:
                self.after(self._min_display_ms - elapsed_ms, self._finish_task)
                return
            if hasattr(self, 'progress') and self.progress:
                self.progress.stop()
            if self.winfo_exists():
                self.grab_release()
                self.destroy()
        except Exception:
            pass
        
    def _cancel_task(self):
        """ยกเลิกงาน (ถ้าต้องการ)"""
        self.error = "ยกเลิกโดยผู้ใช้"
        self._finish_task()
        
    def _schedule_ui_update(self):
        """กำหนดการอัพเดท UI เป็นระยะ เพื่อให้ progress bar วิ่งได้"""
        try:
            if self.winfo_exists():
                self.update_idletasks()
                self.after(50, self._schedule_ui_update)
        except Exception:
            pass

    def _schedule_elapsed_update(self):
        try:
            if self.winfo_exists() and self._start_ts is not None:
                elapsed = time.perf_counter() - self._start_ts
                if hasattr(self, 'elapsed_label') and self.elapsed_label:
                    self.elapsed_label.configure(text=f"เวลา: {elapsed:.1f} วินาที")
                self.after(200, self._schedule_elapsed_update)
        except Exception:
            pass

    def _schedule_tip_rotation(self):
        try:
            if self.winfo_exists() and hasattr(self, 'tip_label') and self.tip_label:
                self._tip_index = (self._tip_index + 1) % len(self._tips)
                self.tip_label.configure(text=self._tips[self._tip_index])
                self.after(2500, self._schedule_tip_rotation)
        except Exception:
            pass

    def _infer_step_from_message(self, message: str):
        """พยายามจับคู่ข้อความกับขั้นตอน และอัพเดทสถานะอัตโนมัติ"""
        text = message.strip()
        try:
            # ตัวอย่างขั้นตอนมาตรฐานตอนเตรียมระบบ
            keywords_map = [
                (0, ["เชื่อมต่อ", "การเชื่อมต่อ"]),
                (1, ["สิทธิ์", "สิทธิ์การใช้งาน"]),
                (2, ["โหลด", "เตรียม", "ตั้งค่า"]),
                (3, ["สร้าง UI", "สร้าง MainWindow", "สร้าง Tab"]),
            ]
            if self.steps:
                for idx, keys in keywords_map:
                    if idx < len(self.steps) and any(k in text for k in keys):
                        # กำลังทำ
                        self.mark_step_running(idx)
                        # ถ้ามีคำบ่งชี้เสร็จสิ้น
                        if any(done_kw in text for done_kw in ["เสร็จสิ้น", "สำเร็จ", "เรียบร้อย"]):
                            self.mark_step_done(idx)
                        break
        except Exception:
            pass
            
    def get_result(self):
        """คืนค่าผลลัพธ์ของงาน"""
        if self.error:
            raise self.error
        return self.result