import customtkinter as ctk
from tkinter import messagebox
import os
from services.orchestrators.database_orchestrator import DatabaseOrchestrator
from ui.main_window import MainWindow
from ui.loading_dialog import LoadingDialog
from services.utilities.preload_service import PreloadService
from constants import AppConstants
from config.database import DatabaseConfig
from config.json_manager import json_manager
import logging

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # ตั้งค่าหน้าต่าง
        self.title("Login SQL Server")
        self.geometry(f"{AppConstants.LOGIN_WINDOW_SIZE[0]}x{AppConstants.LOGIN_WINDOW_SIZE[1]}")
        self.resizable(False, False)
        # มินิมอลโทน: เพิ่มระยะห่างทั่วๆ ไป
        self._base_padx = 12
        self._base_pady = 10
        
        # สร้างบริการ
        self.db_service = DatabaseOrchestrator()
        self.preload_service = PreloadService()
        self.db_config = DatabaseConfig()
        
        # สร้าง UI
        self._create_ui()
        
        # โหลดการตั้งค่าที่บันทึกไว้
        self._load_saved_settings()
        

        
    def _create_ui(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(expand=True, fill="both", padx=self._base_padx, pady=self._base_pady)

        # กำหนด column/row ให้ขยายได้ เพื่อจัดกึ่งกลาง
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        for i in range(10):
            main_frame.grid_rowconfigure(i, weight=1)

        label_width = 100

        # กรอบหัวข้อ (Frame) แยกส่วนหัวกับฟอร์มหลัก พื้นหลังสีต่างแต่โทนเดียวกัน
        title_frame = ctk.CTkFrame(main_frame, fg_color="#363636")  # สีเข้มขึ้นในโทนเดียวกับธีม
        title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10), padx=0)
        title_label = ctk.CTkLabel(
            title_frame,
            text="SIGN IN TO SQL SERVER",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f0f4fa"  # สีอ่อนตัดกับพื้นหลัง
        )
        title_label.pack(padx=18, pady=12)

        # Server
        server_label = ctk.CTkLabel(main_frame, text="Server", width=label_width, anchor="w")
        server_label.grid(row=2, column=0, sticky="e", padx=6, pady=4)
        self.server_entry = ctk.CTkEntry(main_frame, width=240, placeholder_text="Server name")
        self.server_entry.grid(row=2, column=1, sticky="w", padx=6, pady=4)

        # Database
        db_label = ctk.CTkLabel(main_frame, text="Database", width=label_width, anchor="w")
        db_label.grid(row=3, column=0, sticky="e", padx=6, pady=4)
        self.db_entry = ctk.CTkEntry(main_frame, width=240, placeholder_text="Database name")
        self.db_entry.grid(row=3, column=1, sticky="w", padx=6, pady=4)

        # Schema
        schema_label = ctk.CTkLabel(main_frame, text="Schema", width=label_width, anchor="w")
        schema_label.grid(row=4, column=0, sticky="e", padx=6, pady=4)
        self.schema_entry = ctk.CTkEntry(main_frame, width=240, placeholder_text="Schema name (default: bronze)")
        self.schema_entry.grid(row=4, column=1, sticky="w", padx=6, pady=4)

        # Authentication
        auth_label = ctk.CTkLabel(main_frame, text="Authentication", width=label_width, anchor="w")
        auth_label.grid(row=5, column=0, sticky="e", padx=6, pady=4)
        self.auth_menu = ctk.CTkOptionMenu(main_frame, values=["Windows", "SQL Server"], command=self._on_auth_change, width=240)
        self.auth_menu.grid(row=5, column=1, sticky="w", padx=6, pady=4)

        # Username (row 6)
        self.username_label = ctk.CTkLabel(main_frame, text="Username", width=label_width, anchor="w")
        self.username_entry = ctk.CTkEntry(main_frame, width=240, placeholder_text="Username")
        # Password (row 7)
        self.password_label = ctk.CTkLabel(main_frame, text="Password", width=label_width, anchor="w")
        self.password_entry = ctk.CTkEntry(main_frame, width=240, show="*", placeholder_text="Password")

        # Remember me (ย้ายมาอยู่ใต้ช่อง password และให้ขนาดเล็กลง และเพิ่มระยะห่างจากด้านบน)
        self.remember_var = ctk.BooleanVar(value=True)
        remember_check = ctk.CTkCheckBox(
            main_frame, 
            text="Remember settings", 
            variable=self.remember_var,
            width=100,  # ขนาดปุ่มติ๊กถูก
            font=ctk.CTkFont(size=12),
            checkbox_width=18,  # ขนาดปุ่มติ๊กถูก
            checkbox_height=18   # ขนาดปุ่มติ๊กถูก
        )
        # เพิ่มระยะห่างด้านบนโดยจะไปกำหนดใน grid ด้วย pady
        # จะวางไว้ที่ row 8, column 1 (ใต้ password entry, ชิดซ้าย)
        remember_check.grid(row=8, column=1, sticky="w", padx=(0, 0), pady=(0, 2))

        # Connect button
        connect_button = ctk.CTkButton(main_frame, text="Connect", command=self._connect, width=300)
        connect_button.grid(row=9, column=0, columnspan=2, pady=12, sticky="", ipadx=30)

        self._on_auth_change("Windows")

    def _on_auth_change(self, choice):
        if choice == "Windows":
            self.username_label.grid_remove()
            self.username_entry.grid_remove()
            self.password_label.grid_remove()
            self.password_entry.grid_remove()
        else:
            self.username_label.grid(row=6, column=0, sticky="e", padx=5, pady=5)
            self.username_entry.grid(row=6, column=1, sticky="w", padx=5, pady=5)
            self.password_label.grid(row=7, column=0, sticky="e", padx=5, pady=5)
            self.password_entry.grid(row=7, column=1, sticky="w", padx=5, pady=5)

    def _load_saved_settings(self):
        """Load settings from environment variables only"""
        try:
            # Load from environment variables only
            server = os.getenv('DB_SERVER', '')
            database = os.getenv('DB_NAME', '')
            schema = os.getenv('DB_SCHEMA', 'bronze')
            username = os.getenv('DB_USERNAME', '')
            password = os.getenv('DB_PASSWORD', '')


            # Determine auth type based on username presence
            auth_type = "SQL Server" if username else "Windows"

            self.server_entry.insert(0, server)
            self.db_entry.insert(0, database)
            self.schema_entry.insert(0, schema)
            self.auth_menu.set(auth_type)
            self.username_entry.insert(0, username)
            self.password_entry.insert(0, password)

            # เรียกใช้ _on_auth_change เพื่อซ่อน/แสดง username/password
            self._on_auth_change(auth_type)
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            
    def _save_settings(self):
        """Save settings to .env file"""
        if self.remember_var.get():
            try:
                # Get schema value, default to 'bronze' if empty
                schema_value = self.schema_entry.get().strip() or 'bronze'

                success = self.db_config.save_to_env_file(
                    server=self.server_entry.get(),
                    database=self.db_entry.get(),
                    schema=schema_value,
                    auth_type=self.auth_menu.get(),
                    username=self.username_entry.get(),
                    password=self.password_entry.get()
                )
                if success:
                    logging.info("Database configuration saved to .env file")
                else:
                    logging.error("Failed to save configuration to .env file")
            except Exception as e:
                logging.error(f"Error saving settings: {e}")
                
    def _connect(self):
        """Connect to SQL Server"""
        # Get schema value, default to 'bronze' if empty
        schema_value = self.schema_entry.get().strip() or 'bronze'

        config = {
            "server": self.server_entry.get(),
            "database": self.db_entry.get(),
            "schema": schema_value,
            "auth_type": self.auth_menu.get(),
            "username": self.username_entry.get(),
            "password": self.password_entry.get()
        }

        # ตรวจสอบข้อมูลที่จำเป็น
        if not config["server"] or not config["database"]:
            messagebox.showerror("Error", "Please fill in Server and Database")
            return

        if config["auth_type"] == "SQL Server" and (not config["username"] or not config["password"]):
            messagebox.showerror("Error", "Please fill in Username and Password")
            return
            
        # บันทึกการตั้งค่า
        self._save_settings()
        
        # Reload config to get updated environment variables
        self.db_config.load_config()
        
        # Update DatabaseConfig engine
        try:
            self.db_config.update_engine()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update database configuration: {str(e)}")
            return
        
        # ทดสอบการเชื่อมต่อ ตรวจสิทธิ์ และ preload ใน dialog เดียว (background)
        try:
            loading_dialog = LoadingDialog(
                self,
                "Preparing system",
                "Testing database connection...",
                min_display_ms=1200,
                min_step_duration_ms=900,
                min_total_duration_ms=3800,
                auto_close_on_task_done=False,
                steps=[
                    "Connect to database",
                    "Check permissions",
                    "Load app/file settings",
                    "Build main UI components"
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
            
            # ถ้า user ยกเลิก ให้ปิดเงียบๆ ไม่แสดง error
            if loading_dialog.user_cancelled:
                loading_dialog.release_and_close()
                self.wait_window(loading_dialog)
                return
                
            if error:
                loading_dialog.release_and_close()
                self.wait_window(loading_dialog)
                messagebox.showerror("Error", f"Error occurred: {str(error)}")
                return

            if loading_dialog.error and not loading_dialog.user_cancelled:
                messagebox.showerror("Error", f"Error occurred: {str(loading_dialog.error)}")
                return

            if not result.get('connection_ok', False):
                loading_dialog.release_and_close()
                self.wait_window(loading_dialog)
                if not loading_dialog.user_cancelled:
                    messagebox.showerror("Error", "Unable to connect to SQL Server")
                return

            if not result.get('permissions_ok', False):
                missing_permissions = result.get('missing_permissions', [])
                recommendations = result.get('recommendations', [])
                detail_msg = f"Missing required permissions: {', '.join(missing_permissions)}\n\n"
                if recommendations:
                    detail_msg += "Recommendations:\n" + "\n".join(recommendations[:3])
                loading_dialog.release_and_close()
                self.wait_window(loading_dialog)
                if not loading_dialog.user_cancelled:
                    messagebox.showerror("Insufficient permissions", f"Connected, but permissions are insufficient\n\n{detail_msg}")
                return

            # ส่งข้อมูลที่โหลดไว้ให้ MainWindow
            preloaded_data = result.get('preloaded_data')

            # แสดง loading dialog และสร้าง MainWindow ใน main thread
            self.ui_loading_dialog = LoadingDialog(
                self,
                "Building UI",
                "Preparing MainWindow and building UI for file types...",
                min_display_ms=900,
                min_step_duration_ms=700,
                min_total_duration_ms=2800,
                auto_close_on_task_done=False,
                steps=[
                    "Build Tab View",
                    "Build Main Tab",
                    "Build Log Tab",
                    "Build Settings Tab",
                    "Initialize log file",
                    "Initialize input/output folders",
                    "Verify SQL Server connection"
                ]
            )

            # เริ่มสร้าง MainWindow ใน main thread โดยใช้ after()
            self.preloaded_data = preloaded_data
            self.after(100, self._start_ui_creation)
        except Exception as e:
            # ตรวจสอบว่า error เกิดจาก user cancel หรือไม่
            try:
                if hasattr(self, 'ui_loading_dialog') and self.ui_loading_dialog and self.ui_loading_dialog.user_cancelled:
                    return  # ไม่แสดง error ถ้า user ยกเลิก
            except:
                pass
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            
    def _start_ui_creation(self):
        """Start UI creation in main thread"""
        try:
            # อัพเดท progress
            self.ui_loading_dialog.update_message("Starting MainWindow creation...")
            self.after(50, self._create_main_window_step1)
        except Exception as e:
            try:
                if hasattr(self, 'ui_loading_dialog') and self.ui_loading_dialog and self.ui_loading_dialog.user_cancelled:
                    return  # ไม่แสดง error ถ้า user ยกเลิก
            except:
                pass
            if hasattr(self, 'ui_loading_dialog'):
                self.ui_loading_dialog.destroy()
            messagebox.showerror("Error", f"Error creating UI: {str(e)}")
    
    def _create_main_window_step1(self):
        """Create MainWindow step 1"""
        try:
            self.ui_loading_dialog.update_message("Creating MainWindow...")

            # Track completed steps
            self._completed_ui_steps = set()

            # สร้าง MainWindow พร้อม progress callback ที่มี step index
            def progress_callback(message):
                """UI building progress callback"""
                self.ui_loading_dialog.update_message(message)

                # Map messages to step indices and mark done when moving to next
                if "Tab View" in message:
                    self.ui_loading_dialog.mark_step_running(0)
                    self._completed_ui_steps.add(0)
                elif "Main Tab" in message:
                    if 0 in self._completed_ui_steps:
                        self.ui_loading_dialog.mark_step_done(0)
                    self.ui_loading_dialog.mark_step_running(1)
                    self._completed_ui_steps.add(1)
                elif "Log Tab" in message:
                    if 1 in self._completed_ui_steps:
                        self.ui_loading_dialog.mark_step_done(1)
                    self.ui_loading_dialog.mark_step_running(2)
                    self._completed_ui_steps.add(2)
                elif "Settings Tab" in message:
                    if 2 in self._completed_ui_steps:
                        self.ui_loading_dialog.mark_step_done(2)
                    self.ui_loading_dialog.mark_step_running(3)
                    self._completed_ui_steps.add(3)

            # ใช้ callback เพื่อเปิด main window เมื่อสร้าง UI ทั้งหมดเสร็จ
            def on_ui_ready():
                # Mark Settings Tab as done
                if 3 in self._completed_ui_steps:
                    self.ui_loading_dialog.mark_step_done(3)
                # UI สร้างเสร็จแล้ว ต่อด้วย initialization tasks
                self.after(50, self._run_initialization_tasks)

            self.main_window = MainWindow(
                master=self,
                preloaded_data=self.preloaded_data,
                ui_progress_callback=progress_callback,
                on_ready_callback=on_ui_ready
            )
            # ซ่อน MainWindow ไว้ก่อนจนกว่าจะพร้อมทั้งหมด
            self.main_window.withdraw()
            
        except Exception as e:
            try:
                if hasattr(self, 'ui_loading_dialog') and self.ui_loading_dialog and self.ui_loading_dialog.user_cancelled:
                    return  # ไม่แสดง error ถ้า user ยกเลิก
            except:
                pass
            if hasattr(self, 'ui_loading_dialog'):
                self.ui_loading_dialog.destroy()
            messagebox.showerror("Error", f"Error creating UI: {str(e)}")
    
    def _run_initialization_tasks(self):
        """รัน initialization tasks ทั้งหมดใน loading dialog"""
        try:
            def progress_callback(message, step_index=None, mark_done=False):
                """Callback ที่รับทั้งข้อความ, step index และ mark_done flag"""
                if self.ui_loading_dialog:
                    self.ui_loading_dialog.update_message(message)
                    # ถ้ามี step_index
                    if step_index is not None:
                        if mark_done:
                            # Mark step เป็น done (✓)
                            self.ui_loading_dialog.mark_step_done(step_index)
                        else:
                            # Mark step เป็น running (●)
                            self.ui_loading_dialog.mark_step_running(step_index)

            # รัน initialization tasks
            success = self.main_window.run_initialization_tasks(progress_callback)

            if not success:
                # ถ้า initialization ล้มเหลว
                if self.ui_loading_dialog:
                    self.ui_loading_dialog.release_and_close()
                    self.wait_window(self.ui_loading_dialog)
                messagebox.showerror(
                    "Initialization Error",
                    "Failed to initialize system. Please check SQL Server connection."
                )
                if hasattr(self, 'main_window'):
                    self.main_window.destroy()
                return

            # ทุกอย่างพร้อมแล้ว - แสดง MainWindow
            self.after(50, self._show_main_window)

        except Exception as e:
            if self.ui_loading_dialog:
                self.ui_loading_dialog.release_and_close()
                self.wait_window(self.ui_loading_dialog)
            messagebox.showerror("Error", f"Error during initialization: {str(e)}")
            if hasattr(self, 'main_window'):
                self.main_window.destroy()

    def _show_main_window(self):
        """แสดง MainWindow หลังจากทุกอย่างพร้อม"""
        try:
            self.ui_loading_dialog.update_message("System ready! Opening main window...")

            # ปล่อยให้ dialog ปิดตัวเองเมื่อครบเวลาขั้นต่ำแล้ว
            if self.ui_loading_dialog:
                self.ui_loading_dialog.release_and_close()
                self.wait_window(self.ui_loading_dialog)

            # ตั้ง handler ปิดหน้าต่างหลัก
            self.main_window.protocol("WM_DELETE_WINDOW", lambda: self._on_main_window_close(self.main_window))

            # ซ่อน Login และโชว์ Main
            self.withdraw()
            self.main_window.deiconify()

        except Exception as e:
            messagebox.showerror("Error", f"Error showing main window: {str(e)}")
            
    def _on_main_window_close(self, main_window):
        """Handle main window close event"""
        main_window.destroy()
        self.destroy()  # ปิดแอปพลิเคชัน 

    # ===== Combined background task =====
    def _connect_and_prepare(self, config, progress_callback=None):
        """Combined steps: connect -> check permissions -> preload data"""
        # 1) ทดสอบการเชื่อมต่อ
        if progress_callback:
            progress_callback("Testing database connection...")
        connection_ok = self.db_service.test_connection(config)
        if not connection_ok:
            return {"connection_ok": False}

        # 2) ตรวจสิทธิ์ - ใช้ config ที่ user พิมพ์ใหม่
        if progress_callback:
            progress_callback("Checking database permissions...")

        # อัปเดต connection service ให้ใช้ config ใหม่ก่อนตรวจสิทธิ์
        self.db_service.update_config(
            server=config["server"],
            database=config["database"],
            auth_type=config["auth_type"],
            username=config.get("username"),
            password=config.get("password")
        )

        permission_results = self.db_service.check_permissions(config.get('schema', 'bronze'), log_callback=progress_callback)
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
            progress_callback("Loading file types and settings...")
        preload_success, _msg, data = self.preload_service.preload_file_settings(progress_callback=progress_callback)

        return {
            "connection_ok": True,
            "permissions_ok": True,
            "preloaded_data": data if preload_success else None
        }