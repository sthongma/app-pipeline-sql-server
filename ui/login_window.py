import customtkinter as ctk
from tkinter import messagebox
import json
import os
from services.database_service import DatabaseService
from ui.main_window import MainWindow

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # ตั้งค่าหน้าต่าง
        self.title("SQL Server Login")
        self.geometry("500x400")
        self.resizable(False, False)
        
        # สร้างบริการ
        self.db_service = DatabaseService()
        
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
        title_label = ctk.CTkLabel(main_frame, text="SQL Server Login", font=("Arial", 22, "bold"))
        title_label.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="n")

        # Server
        server_label = ctk.CTkLabel(main_frame, text="Server:", width=label_width, anchor="w")
        server_label.grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.server_entry = ctk.CTkEntry(main_frame, width=220, placeholder_text="YourServerName")
        self.server_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Database
        db_label = ctk.CTkLabel(main_frame, text="Database:", width=label_width, anchor="w")
        db_label.grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.db_entry = ctk.CTkEntry(main_frame, width=220, placeholder_text="YourDatabaseName")
        self.db_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)

        # Authentication
        auth_label = ctk.CTkLabel(main_frame, text="Authentication:", width=label_width, anchor="w")
        auth_label.grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.auth_menu = ctk.CTkOptionMenu(main_frame, values=["Windows", "SQL Server"], command=self._on_auth_change, width=220)
        self.auth_menu.grid(row=4, column=1, sticky="w", padx=5, pady=5)

        # Username (row 5)
        self.username_label = ctk.CTkLabel(main_frame, text="Username:", width=label_width, anchor="w")
        self.username_entry = ctk.CTkEntry(main_frame, width=220, placeholder_text="Username")
        # Password (row 6)
        self.password_label = ctk.CTkLabel(main_frame, text="Password:", width=label_width, anchor="w")
        self.password_entry = ctk.CTkEntry(main_frame, width=220, show="*", placeholder_text="Password")

        # Remember me
        self.remember_var = ctk.BooleanVar(value=True)
        remember_check = ctk.CTkCheckBox(main_frame, text="Remember settings", variable=self.remember_var)
        remember_check.grid(row=7, column=0, columnspan=2, pady=5, sticky="")

        # Connect button
        connect_button = ctk.CTkButton(main_frame, text="Connect", command=self._connect, width=220)
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
            if os.path.exists("sql_config.json"):
                with open("sql_config.json", "r") as f:
                    config = json.load(f)
                    
                self.server_entry.insert(0, config.get("server", ""))
                self.db_entry.insert(0, config.get("database", ""))
                self.auth_menu.set(config.get("auth_type", "Windows"))
                self.username_entry.insert(0, config.get("username", ""))
                self.password_entry.insert(0, config.get("password", ""))
                
                # เรียกใช้ _on_auth_change เพื่อซ่อน/แสดง username/password
                self._on_auth_change(config.get("auth_type", "Windows"))
        except Exception as e:
            print(f"Error loading settings: {e}")
            
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
                with open("sql_config.json", "w") as f:
                    json.dump(config, f, indent=4)
            except Exception as e:
                print(f"Error saving settings: {e}")
                
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
        
        # ทดสอบการเชื่อมต่อและสิทธิ์
        try:
            if self.db_service.test_connection(config):
                # ตรวจสอบสิทธิ์ที่จำเป็น
                permission_results = self.db_service.check_permissions('bronze')
                if not permission_results.get('success', False):
                    missing_permissions = permission_results.get('missing_critical', [])
                    recommendations = permission_results.get('recommendations', [])
                    
                    # สร้างข้อความแสดงรายละเอียด
                    detail_msg = f"ขาดสิทธิ์ที่จำเป็น: {', '.join(missing_permissions)}\n\n"
                    if recommendations:
                        detail_msg += "คำแนะนำการแก้ไข:\n" + "\n".join(recommendations[:3])  # แสดง 3 บรรทัดแรก
                    
                    messagebox.showerror(
                        "สิทธิ์ไม่เพียงพอ", 
                        f"เชื่อมต่อสำเร็จ แต่ไม่สามารถใช้งานได้เนื่องจากสิทธิ์ฐานข้อมูลไม่เพียงพอ\n\n{detail_msg}"
                    )
                    return
                
                # เชื่อมต่อและสิทธิ์ผ่าน
                self.withdraw()
                main_window = MainWindow()
                main_window.protocol("WM_DELETE_WINDOW", lambda: self._on_main_window_close(main_window))
                main_window.mainloop()
            else:
                messagebox.showerror("Error", "ไม่สามารถเชื่อมต่อกับ SQL Server ได้")
        except Exception as e:
            messagebox.showerror("Error", f"เกิดข้อผิดพลาด: {str(e)}")
            
    def _on_main_window_close(self, main_window):
        """จัดการเมื่อปิดหน้าต่างหลัก"""
        main_window.destroy()
        self.destroy()  # ปิดแอปพลิเคชัน 