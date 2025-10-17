import customtkinter as ctk
import threading
import time
from typing import Callable, Any

class LoadingDialog(ctk.CTkToplevel):
    """Loading dialog for displaying loading status with step list, tips and timing"""
    
    def __init__(
        self,
        parent,
        title: str = "Loading...",
        message: str = "Please wait...",
        min_display_ms: int = 600,
        min_step_duration_ms: int = 800,
        min_total_duration_ms: int | None = None,
        steps: list | None = None,
        show_tips: bool = True,
        tips: list | None = None,
        auto_close_on_task_done: bool = True,
    ):
        super().__init__(parent)
        
        self.parent = parent
        self.result = None
        self.error = None
        self.task_thread = None
        self.user_cancelled = False
        self._min_display_ms = int(min_display_ms)
        self._min_step_duration_ms = int(min_step_duration_ms)
        self._start_ts = None
        self.steps = steps or []
        self._step_labels = []
        self._current_step_index = None
        self._step_done_flags = [False] * len(self.steps)
        self._show_tips = bool(show_tips)
        self._tips = tips or [
            "Tip: You can adjust UI theme in Settings",
            "Tip: Set Date Format to match your files in Settings",
            "Tip: Use 'Auto Processing' to reduce steps",
            "Tip: Check data types match columns before upload",
        ]
        self._tip_index = 0
        self._closing_started = False
        self._last_message_update = 0  # Track last message update time for debouncing
        self._pending_message = None  # Store pending message for debounced update
        self._ui_update_interval = 150  # UI update interval in ms (increased to reduce flickering)
        self._elapsed_update_interval = 500  # Elapsed time update interval in ms
        self._min_total_duration_ms = (
            int(min_total_duration_ms)
            if min_total_duration_ms is not None
            else (len(self.steps) * self._min_step_duration_ms if self.steps else self._min_display_ms)
        )
        self._auto_close_on_task_done = bool(auto_close_on_task_done)
        
        # ตั้งค่าหน้าต่าง
        self.title(title)
        # ใช้ขนาดเท่าเดิม ไม่ยืดตาม steps
        self.geometry("380x160")
        self.resizable(False, False)
        self.transient(parent)  # ทำให้เป็น dialog ของ parent
        self.grab_set()  # ทำให้ dialog เป็น modal
        
        # จัดกึ่งกลางหน้าจอ
        self._center_window()
        
        # ตั้งค่าการจัดการเมื่อ user กด X
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
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

        # ได้ขนาดของ dialog
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        # คำนวณตำแหน่งกึ่งกลาง
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)

        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
    def _create_ui(self, message):
        """สร้าง UI ของ dialog"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=20, pady=16)
        
        # หัวเรื่อง
        self.title_label = ctk.CTkLabel(main_frame, text=self.title())
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
            wraplength=300
        )
        self.message_label.pack(pady=(2, 8))

        # แสดงสถานะ step ปัจจุบัน (แทนที่จะแสดง list ทั้งหมด)
        if self.steps:
            # สร้าง frame สำหรับ icon + text
            self.step_status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            self.step_status_frame.pack(pady=(0, 6), fill="x")

            # Icon
            self.step_icon_label = ctk.CTkLabel(
                self.step_status_frame,
                text="○",
                text_color="#888888",
                width=20
            )
            self.step_icon_label.pack(side="left", padx=(0, 6))

            # Text
            self.step_text_label = ctk.CTkLabel(
                self.step_status_frame,
                text="Preparing...",
                anchor="w"
            )
            self.step_text_label.pack(side="left", fill="x", expand=True)

        # เวลาและเคล็ดลับ
        bottom_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(4, 0))
        self.elapsed_label = ctk.CTkLabel(bottom_frame, text="Time: 0.0 seconds", text_color="#7a7a7a")
        self.elapsed_label.pack(side="left")
        if self._show_tips and self._tips:
            self.tip_label = ctk.CTkLabel(bottom_frame, text=self._tips[0], text_color="#7a7a7a")
            self.tip_label.pack(side="right")
            self._schedule_tip_rotation()
        
        # อัพเดทเวลา
        self._schedule_elapsed_update()
        
        # ปุ่ม Cancel (ซ่อนไว้ก่อน)
        self.cancel_button = ctk.CTkButton(
            main_frame, 
            text="Cancel", 
            command=self._cancel_task,
            width=100
        )
        # ไม่แสดงปุ่ม cancel เพื่อความง่าย
        
    def update_message(self, message):
        """อัพเดทข้อความด้วย debouncing เพื่อลด UI updates"""
        try:
            current_time = time.perf_counter()
            # Debounce: อัพเดท UI ไม่เกินทุก 150ms (เพิ่มจาก 100ms)
            if current_time - self._last_message_update < 0.15:
                # เก็บข้อความไว้สำหรับอัพเดทภายหลัง
                self._pending_message = message
                return

            if hasattr(self, 'message_label') and self.message_label and self.winfo_exists():
                self.message_label.configure(text=message)
                # เดาและอัพเดทสถานะขั้นตอนจากข้อความ
                self._infer_step_from_message(str(message))
                self._last_message_update = current_time
                self._pending_message = None
        except Exception:
            pass

    def set_steps(self, steps: list[str]):
        """กำหนดรายการขั้นตอนใหม่"""
        self.steps = steps or []
        # ล้างของเดิมและสร้างใหม่หากต้องการ (ขอข้ามเพื่อความเรียบง่าย)
        
    def mark_step_running(self, index: int):
        """อัพเดทสถานะขั้นตอนเป็น running"""
        if 0 <= index < len(self.steps):
            self._current_step_index = index
            step_text = self.steps[index]
            # อัพเดท icon (ใส่สี)
            if hasattr(self, 'step_icon_label') and self.step_icon_label:
                self.step_icon_label.configure(
                    text="●",
                    text_color="#4A9EFF"  # สีฟ้า - กำลังทำ
                )
            # อัพเดท text (ไม่ใส่สี)
            if hasattr(self, 'step_text_label') and self.step_text_label:
                self.step_text_label.configure(text=step_text)

    def mark_step_done(self, index: int):
        """อัพเดทสถานะขั้นตอนเป็น done"""
        if 0 <= index < len(self.steps):
            step_text = self.steps[index]
            # อัพเดท icon (ใส่สี)
            if hasattr(self, 'step_icon_label') and self.step_icon_label:
                self.step_icon_label.configure(
                    text="✓",
                    text_color="#41AA41"  # สีเขียว - เสร็จแล้ว
                )
            # อัพเดท text (ไม่ใส่สี)
            if hasattr(self, 'step_text_label') and self.step_text_label:
                self.step_text_label.configure(text=step_text)
            if 0 <= index < len(self._step_done_flags):
                self._step_done_flags[index] = True

    def mark_step_error(self, index: int):
        """อัพเดทสถานะขั้นตอนเป็น error"""
        if 0 <= index < len(self.steps):
            step_text = self.steps[index]
            # อัพเดท icon (ใส่สี)
            if hasattr(self, 'step_icon_label') and self.step_icon_label:
                self.step_icon_label.configure(
                    text="✗",
                    text_color="#FF4444"  # สีแดง - error
                )
            # อัพเดท text (ไม่ใส่สี)
            if hasattr(self, 'step_text_label') and self.step_text_label:
                self.step_text_label.configure(text=step_text)
            
    def run_task(self, task_func: Callable, *args, on_done: Callable[[Any, Any], None] | None = None, **kwargs):
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
                # แจ้ง callback เสร็จงานบน main thread และปิดถ้าตั้งค่า auto_close
                def _done():
                    try:
                        if callable(on_done):
                            on_done(self.result, self.error)
                    finally:
                        if self._auto_close_on_task_done:
                            self._finish_task()
                self.after(100, _done)
                
        self.task_thread = threading.Thread(target=worker)
        self.task_thread.daemon = True
        self.task_thread.start()
        
    def _finish_task(self):
        """เสร็จสิ้นงานและปิด dialog"""
        try:
            if self._closing_started:
                return
            # คำนวณเวลาแสดงผลขั้นต่ำรวม (ช้ากว่าการทำงานจริงได้)
            elapsed_ms = int((time.perf_counter() - self._start_ts) * 1000) if self._start_ts else 0
            required_min_ms = max(self._min_display_ms, self._min_total_duration_ms or 0)

            # ถ้ามี steps และยังไม่ทำครบ ให้แอนิเมตขั้นตอนที่เหลือแบบคั่นเวลา แล้วค่อยปิด
            total_steps = len(self.steps)
            done_count = sum(1 for f in self._step_done_flags if f)
            if total_steps > 0 and done_count < total_steps:
                self._closing_started = True
                # เริ่มรัน step ปัจจุบันถ้ายังไม่ได้รัน
                if self._current_step_index is None:
                    self.mark_step_running(0)
                self._animate_remaining_steps_and_close(required_min_ms)
                return

            # หากไม่มี steps หรือทำครบแล้ว แต่เวลาไม่ถึงขั้นต่ำ ให้รอเพิ่ม
            if elapsed_ms < required_min_ms:
                self.after(required_min_ms - elapsed_ms, self._finish_task)
                return

            # ปิดจริง
            self._final_close()
        except Exception:
            pass

    def _animate_remaining_steps_and_close(self, required_min_ms: int):
        """แอนิเมตให้ขั้นตอนที่เหลือเสร็จตามช่วงเวลา แล้วปิดเมื่อถึงเวลา"""
        try:
            total_steps = len(self.steps)
            # หาดัชนีขั้นตอนถัดไปที่ยังไม่ done (รวมปัจจุบัน)
            next_idx = None
            for i in range(self._current_step_index or 0, total_steps):
                if not self._step_done_flags[i]:
                    next_idx = i
                    break
            if next_idx is None:
                # ทุกขั้นตอนทำครบแล้ว → ตรวจเวลาแล้วปิด
                elapsed_ms = int((time.perf_counter() - self._start_ts) * 1000) if self._start_ts else 0
                if elapsed_ms < required_min_ms:
                    self.after(required_min_ms - elapsed_ms, self._final_close)
                else:
                    self._final_close()
                return
            # ทำให้แน่ใจว่า step นี้กำลังทำงานอยู่
            if self._current_step_index != next_idx:
                self.mark_step_running(next_idx)
            # คำนวณเวลาต่อขั้นตอนให้พอดีกับ required_min_ms ที่เหลือ
            elapsed_ms = int((time.perf_counter() - self._start_ts) * 1000) if self._start_ts else 0
            remaining_ms = max(required_min_ms - elapsed_ms, 0)
            remaining_steps = sum(1 for f in self._step_done_flags if not f)
            per_step_ms = max(self._min_step_duration_ms, int(remaining_ms / remaining_steps) if remaining_steps > 0 else self._min_step_duration_ms)

            def _advance():
                self.mark_step_done(next_idx)
                # ไปขั้นตอนถัดไป
                following_idx = None
                for j in range(next_idx + 1, total_steps):
                    if not self._step_done_flags[j]:
                        following_idx = j
                        break
                if following_idx is not None:
                    self.mark_step_running(following_idx)
                    self.after(per_step_ms, lambda: self._animate_remaining_steps_and_close(required_min_ms))
                else:
                    # ไม่มีขั้นตอนเหลือ → ตรวจเวลาแล้วปิด
                    elapsed = int((time.perf_counter() - self._start_ts) * 1000) if self._start_ts else 0
                    if elapsed < required_min_ms:
                        self.after(required_min_ms - elapsed, self._final_close)
                    else:
                        self._final_close()

            self.after(per_step_ms, _advance)
        except Exception:
            self._final_close()

    def _final_close(self):
        try:
            if hasattr(self, 'progress') and self.progress:
                self.progress.stop()
            if self.winfo_exists():
                self.grab_release()
                self.destroy()
        except Exception:
            pass

    def release_and_close(self):
        """ให้ปิด dialog ได้เมื่อถึงเวลาแสดงขั้นต่ำแล้ว (ใช้คู่กับ auto_close_on_task_done=False)"""
        try:
            if not self._auto_close_on_task_done:
                self._finish_task()
        except Exception:
            try:
                if self.winfo_exists():
                    self.destroy()
            except Exception:
                pass
        
    def _on_close(self):
        """จัดการเมื่อ user กด X"""
        self.user_cancelled = True
        self._cancel_task()
        
    def _cancel_task(self):
        """ยกเลิกงาน (ถ้าต้องการ)"""
        self.user_cancelled = True
        self.error = "Cancelled by user"
        self._finish_task()
        
    def _schedule_ui_update(self):
        """กำหนดการอัพเดท UI เป็นระยะ เพื่อให้ progress bar วิ่งได้"""
        try:
            if self.winfo_exists():
                # ใช้ update_idletasks() แทน update() เพื่อลดการ redraw
                self.update_idletasks()
                # ถ้ามี pending message ให้อัพเดทตอนนี้
                if self._pending_message is not None:
                    try:
                        if hasattr(self, 'message_label') and self.message_label:
                            self.message_label.configure(text=self._pending_message)
                            self._infer_step_from_message(str(self._pending_message))
                            self._pending_message = None
                            self._last_message_update = time.perf_counter()
                    except Exception:
                        pass
                # เพิ่ม interval เป็น 150ms เพื่อลดการกระตุก
                self.after(self._ui_update_interval, self._schedule_ui_update)
        except Exception:
            pass

    def _schedule_elapsed_update(self):
        try:
            if self.winfo_exists() and self._start_ts is not None:
                elapsed = time.perf_counter() - self._start_ts
                if hasattr(self, 'elapsed_label') and self.elapsed_label:
                    self.elapsed_label.configure(text=f"Time: {elapsed:.1f} seconds")
                # เพิ่ม interval เป็น 500ms เพื่อลดการกระตุก
                self.after(self._elapsed_update_interval, self._schedule_elapsed_update)
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
                (0, ["Connect", "Connection"]),
                (1, ["Permission", "Access rights"]),
                (2, ["Load", "Prepare", "Setup"]),
                (3, ["Create UI", "Create MainWindow", "Create Tab"]),
            ]
            if self.steps:
                for idx, keys in keywords_map:
                    if idx < len(self.steps) and any(k in text for k in keys):
                        # กำลังทำ
                        self.mark_step_running(idx)
                        # ถ้ามีคำบ่งชี้เสร็จสิ้น
                        if any(done_kw in text for done_kw in ["completed", "successful", "done"]):
                            self.mark_step_done(idx)
                        break
        except Exception:
            pass
            
    def get_result(self):
        """คืนค่าผลลัพธ์ของงาน"""
        if self.error:
            raise self.error
        return self.result