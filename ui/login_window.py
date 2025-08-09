import customtkinter as ctk
from tkinter import messagebox
import json
import os
from services.database_service import DatabaseService
from ui.main_window import MainWindow
from ui.loading_dialog import LoadingDialog
from services.preload_service import PreloadService
from constants import PathConstants, AppConstants
import logging

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # ตั้งค่าหน้าต่าง
        self.title("เข้าสู่ระบบ SQL Server")
        self.geometry(f"{AppConstants.LOGIN_WINDOW_SIZE[0]}x{AppConstants.LOGIN_WINDOW_SIZE[1]}")
        self.resizable(False, False)
        
        # สร้างบริการ
        self.db_service = DatabaseService()
        self.preload_service = PreloadService()
        
        # สร้าง UI
        self._create_ui()
        
        # โหลดการตั้งค่าที่บันทึกไว้
        self._load_saved_settings()
        
    def _create_ui(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both")

        # กำหนด column/row ให้ขยายได้ เพื่อจัดกึ่งกลาง
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        for i in range(10):
            main_frame.grid_rowconfigure(i, weight=1)

        label_width = 140

        # หัวข้อ
        title_label = ctk.CTkLabel(main_frame, text="เข้าสู่ระบบ SQL Server", font=("Arial", 22, "bold"))
        title_label.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="n")

        # Server
        server_label = ctk.CTkLabel(main_frame, text="เซิร์ฟเวอร์:", width=label_width, anchor="w")
        server_label.grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.server_entry = ctk.CTkEntry(main_frame, width=220, placeholder_text="ชื่อเซิร์ฟเวอร์")
        self.server_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Database
        db_label = ctk.CTkLabel(main_frame, text="ฐานข้อมูล:", width=label_width, anchor="w")
        db_label.grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.db_entry = ctk.CTkEntry(main_frame, width=220, placeholder_text="ชื่อฐานข้อมูล")
        self.db_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        # Authentication
        auth_label = ctk.CTkLabel(main_frame, text="วิธีการยืนยันตัวตน:", width=label_width, anchor="w")
        auth_label.grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.auth_menu = ctk.CTkOptionMenu(main_frame, values=["Windows", "SQL Server"], command=self._on_auth_change, width=220)
        self.auth_menu.grid(row=4, column=1, sticky="w", padx=5, pady=5)

        # Username (row 5)
        self.username_label = ctk.CTkLabel(main_frame, text="ชื่อผู้ใช้:", width=label_width, anchor="w")
        self.username_entry = ctk.CTkEntry(main_frame, width=220, placeholder_text="ชื่อผู้ใช้")
        # Password (row 6)
        self.password_label = ctk.CTkLabel(main_frame, text="รหัสผ่าน:", width=label_width, anchor="w")
        self.password_entry = ctk.CTkEntry(main_frame, width=220, show="*", placeholder_text="รหัสผ่าน")

        # Remember me
        self.remember_var = ctk.BooleanVar(value=True)
        remember_check = ctk.CTkCheckBox(main_frame, text="จดจำการตั้งค่า", variable=self.remember_var)
        remember_check.grid(row=7, column=0, columnspan=2, pady=5, sticky="")

        # Connect button
        connect_button = ctk.CTkButton(main_frame, text="เชื่อมต่อ", command=self._connect, width=220)
        connect_button.grid(row=8, column=0, columnspan=2, pady=10, sticky="", ipadx=30)

        self._on_auth_change("Windows")

    def _on_auth_change(self, choice):
        if choice == "Windows":
            self.username_label.grid_remove()
            self.username_entry.grid_remove()
            self.password_label.grid_remove()
            self.password_entry.grid_remove()
        else:
            self.username_label.grid(row=5, column=0, sticky="e", padx=5, pady=5)
            self.username_entry.grid(row=5, column=1, sticky="w", padx=5, pady=5)
            self.password_label.grid(row=6, column=0, sticky="e", padx=5, pady=5)
            self.password_entry.grid(row=6, column=1, sticky="w", padx=5, pady=5)

    def _load_saved_settings(self):
        """โหลดการตั้งค่าที่บันทึกไว้"""
        try:
            if os.path.exists(PathConstants.SQL_CONFIG_FILE):
                with open(PathConstants.SQL_CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    
                self.server_entry.insert(0, config.get("server", ""))
                self.db_entry.insert(0, config.get("database", ""))
                self.auth_menu.set(config.get("auth_type", "Windows"))
                self.username_entry.insert(0, config.get("username", ""))
                self.password_entry.insert(0, config.get("password", ""))
                
                # เรียกใช้ _on_auth_change เพื่อซ่อน/แสดง username/password
                self._on_auth_change(config.get("auth_type", "Windows"))
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            
    def _save_settings(self):
        """บันทึกการตั้งค่า"""
        if self.remember_var.get():
            config = {
                "server": self.server_entry.get(),
                "database": self.db_entry.get(),
                "auth_type": self.auth_menu.get(),
                "username": self.username_entry.get(),
                "password": self.password_entry.get()
            }
            
            try:
                with open(PathConstants.SQL_CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=4)
            except Exception as e:
                logging.error(f"Error saving settings: {e}")
                
    def _connect(self):
        """เชื่อมต่อกับ SQL Server"""
        config = {
            "server": self.server_entry.get(),
            "database": self.db_entry.get(),
            "auth_type": self.auth_menu.get(),
            "username": self.username_entry.get(),
            "password": self.password_entry.get()
        }
        
        # ตรวจสอบข้อมูลที่จำเป็น
        if not config["server"] or not config["database"]:
            messagebox.showerror("Error", "กรุณากรอก Server และ Database")
            return
            
        if config["auth_type"] == "SQL Server" and (not config["username"] or not config["password"]):
            messagebox.showerror("Error", "กรุณากรอก Username และ Password")
            return
            
        # บันทึกการตั้งค่า
        self._save_settings()
        
        # ทดสอบการเชื่อมต่อ ตรวจสิทธิ์ และ preload ใน dialog เดียว (background)
        try:
            loading_dialog = LoadingDialog(
                self,
                "กำลังเตรียมระบบ",
                "กำลังทดสอบการเชื่อมต่อกับฐานข้อมูล...",
                min_display_ms=1200,
                min_step_duration_ms=900,
                min_total_duration_ms=3800,
                auto_close_on_task_done=False,
                steps=[
                    "เชื่อมต่อฐานข้อมูล",
                    "ตรวจสอบสิทธิ์การใช้งาน",
                    "โหลดการตั้งค่าระบบและประเภทไฟล์",
                    "สร้างส่วนประกอบของหน้าหลัก"
                ]
            )

            # รันงานแบบรวมใน background และคุมเวลาปิด dialog เองหลังงาน UI พร้อมจริง
            final_result = {}
            self._prepare_done_var = ctk.BooleanVar(value=False)
            def on_prepare_done(res, err):
                final_result["res"] = res
                final_result["err"] = err
                # แจ้งว่าเสร็จแล้วให้ wait_variable เดินต่อ
                try:
                    self._prepare_done_var.set(True)
                except Exception:
                    pass

            loading_dialog.run_task(self._connect_and_prepare, config, on_done=on_prepare_done)

            # รอให้เตรียมระบบเสร็จ (แต่ยังไม่ปิด dialog)
            self.wait_variable(self._prepare_done_var)

            # ตรวจสอบผลลัพธ์
            result = final_result.get("res") or {}
            error = final_result.get("err")
            if error:
                loading_dialog.release_and_close()
                self.wait_window(loading_dialog)
                messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {str(error)}")
                return

            if loading_dialog.error:
                messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {str(loading_dialog.error)}")
                return

            if not result.get('connection_ok', False):
                loading_dialog.release_and_close()
                self.wait_window(loading_dialog)
                messagebox.showerror("Error", "ไม่สามารถเชื่อมต่อกับ SQL Server ได้")
                return

            if not result.get('permissions_ok', False):
                missing_permissions = result.get('missing_permissions', [])
                recommendations = result.get('recommendations', [])
                detail_msg = f"ขาดสิทธิ์ที่จำเป็น: {', '.join(missing_permissions)}\n\n"
                if recommendations:
                    detail_msg += "คำแนะนำการแก้ไข:\n" + "\n".join(recommendations[:3])
                loading_dialog.release_and_close()
                self.wait_window(loading_dialog)
                messagebox.showerror("สิทธิ์ไม่เพียงพอ", f"เชื่อมต่อสำเร็จ แต่สิทธิ์ไม่เพียงพอ\n\n{detail_msg}")
                return

            # ส่งข้อมูลที่โหลดไว้ให้ MainWindow
            preloaded_data = result.get('preloaded_data')

            # แสดง loading dialog และสร้าง MainWindow ใน main thread
            self.ui_loading_dialog = LoadingDialog(
                self,
                "กำลังสร้าง UI",
                "กำลังเตรียม MainWindow และสร้าง UI ทุกประเภทไฟล์...",
                min_display_ms=900,
                min_step_duration_ms=700,
                min_total_duration_ms=2200,
                auto_close_on_task_done=False,
                steps=[
                    "สร้าง Tab View",
                    "สร้าง Main Tab",
                    "สร้าง Log Tab",
                    "สร้าง Settings Tab"
                ]
            )

            # เริ่มสร้าง MainWindow ใน main thread โดยใช้ after()
            self.preloaded_data = preloaded_data
            self.after(100, self._start_ui_creation)
        except Exception as e:
            messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {str(e)}")
            
    def _start_ui_creation(self):
        """เริ่มการสร้าง UI ใน main thread"""
        try:
            # อัพเดท progress
            self.ui_loading_dialog.update_message("กำลังเริ่มสร้าง MainWindow...")
            self.after(50, self._create_main_window_step1)
        except Exception as e:
            self.ui_loading_dialog.destroy()
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการสร้าง UI: {str(e)}")
    
    def _create_main_window_step1(self):
        """สร้าง MainWindow ขั้นตอนที่ 1"""
        try:
            self.ui_loading_dialog.update_message("กำลังสร้าง MainWindow...")
            # สร้าง MainWindow พร้อม progress callback
            def progress_callback(message):
                self.ui_loading_dialog.update_message(message)
                
            # ใช้ callback เพื่อเปิด main window เมื่อสร้าง UI ทั้งหมดเสร็จ (รอทุกอย่างพร้อมก่อนแสดง)
            def on_main_ready():
                # ปิด dialog สร้าง UI และค่อยแสดงหน้าหลัก
                # ค่อยปล่อยให้ dialog ปิดเองตามเวลาขั้นต่ำ
                try:
                    if self.ui_loading_dialog:
                        self.ui_loading_dialog.release_and_close()
                except Exception:
                    pass
                # ซ่อน Login และโชว์ Main หลังจากพร้อมเต็มที่
                self.withdraw()
                self.main_window.deiconify()

            self.main_window = MainWindow(
                master=self,
                preloaded_data=self.preloaded_data,
                ui_progress_callback=progress_callback,
                on_ready_callback=on_main_ready
            )
            # ซ่อน MainWindow ไว้ก่อนจนกว่าจะพร้อม
            self.main_window.withdraw()
            
            # รอเสร็จแล้ว ปล่อย dialog ปิดตามเวลาและตั้ง handler ปิดหน้าต่างหลัก
            self.after(150, self._finish_ui_creation)
            
        except Exception as e:
            self.ui_loading_dialog.destroy()
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการสร้าง UI: {str(e)}")
    
    def _finish_ui_creation(self):
        """เสร็จสิ้นการสร้าง UI"""
        try:
            self.ui_loading_dialog.update_message("สร้าง MainWindow และ UI เสร็จสิ้น!")
            
            # ปล่อยให้ dialog ปิดตัวเองเมื่อครบเวลาขั้นต่ำแล้ว
            try:
                if self.ui_loading_dialog:
                    self.ui_loading_dialog.release_and_close()
            except Exception:
                pass
            
            # ตั้ง handler ปิดหน้าต่างหลัก (MainWindow จะถูกแสดงโดย on_main_ready เมื่อพร้อมทั้งหมด)
            self.main_window.protocol("WM_DELETE_WINDOW", lambda: self._on_main_window_close(self.main_window))
            
        except Exception as e:
            self.ui_loading_dialog.destroy()
            messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการสร้าง UI: {str(e)}")
            
    def _on_main_window_close(self, main_window):
        """จัดการเมื่อปิดหน้าต่างหลัก"""
        main_window.destroy()
        self.destroy()  # ปิดแอปพลิเคชัน 

    # ===== Combined background task =====
    def _connect_and_prepare(self, config, progress_callback=None):
        """รวมขั้นตอน: เชื่อมต่อ -> ตรวจสิทธิ์ -> preload ข้อมูล"""
        # 1) ทดสอบการเชื่อมต่อ
        if progress_callback:
            progress_callback("กำลังทดสอบการเชื่อมต่อกับฐานข้อมูล...")
        connection_ok = self.db_service.test_connection(config)
        if not connection_ok:
            return {"connection_ok": False}

        # 2) ตรวจสิทธิ์
        if progress_callback:
            progress_callback("กำลังตรวจสอบสิทธิ์การใช้งานฐานข้อมูล...")
        permission_results = self.db_service.check_permissions('bronze', log_callback=progress_callback)
        permissions_ok = permission_results.get('success', False)
        if not permissions_ok:
            return {
                "connection_ok": True,
                "permissions_ok": False,
                "missing_permissions": permission_results.get('missing_critical', []),
                "recommendations": permission_results.get('recommendations', [])
            }

        # 3) Preload ข้อมูล
        if progress_callback:
            progress_callback("กำลังโหลดประเภทไฟล์และการตั้งค่าทั้งหมด...")
        preload_success, _msg, data = self.preload_service.preload_file_settings(progress_callback=progress_callback)

        return {
            "connection_ok": True,
            "permissions_ok": True,
            "preloaded_data": data if preload_success else None
        }