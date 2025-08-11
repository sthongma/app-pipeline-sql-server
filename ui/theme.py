"""
ธีมและตัวแปรฟอนต์ส่วนกลางสำหรับ UI

การใช้งาน:
    from ui import theme
    theme.init_fonts()
    label = ctk.CTkLabel(parent, text="...", font=theme.FONT_BODY)

หมายเหตุ: ใช้ฟอนต์ "Kanit" เป็นหลัก จะ fallback ไปยัง "Segoe UI" -> "Arial" ถ้าไม่มี
"""

from __future__ import annotations

import os
import glob
import sys
import customtkinter as ctk
import tkinter as tk
from tkinter import font as tkfont
from typing import List


# ฟอนต์ส่วนกลาง
FONT_FAMILY: str | None = None
FONT_TITLE: ctk.CTkFont | None = None
FONT_SUBTITLE: ctk.CTkFont | None = None
FONT_BODY: ctk.CTkFont | None = None
FONT_SMALL: ctk.CTkFont | None = None
FONT_BUTTON: ctk.CTkFont | None = None
FONT_UNIFORM: ctk.CTkFont | None = None


def _register_kanit_fonts_if_available() -> None:
    """ลงทะเบียนไฟล์ฟอนต์ Kanit ใน Windows"""
    if sys.platform != "win32":
        return
    try:
        ttf_paths: List[str] = glob.glob(os.path.join("Kanit", "*.ttf"))
        if not ttf_paths:
            return
        
        import ctypes
        FR_PRIVATE = 0x10
        AddFontResourceExW = ctypes.windll.gdi32.AddFontResourceExW
        SendMessageW = ctypes.windll.user32.SendMessageW
        HWND_BROADCAST = 0xFFFF
        WM_FONTCHANGE = 0x001D
        
        for p in ttf_paths:
            try:
                AddFontResourceExW(os.path.abspath(p), FR_PRIVATE, 0)
            except Exception:
                pass
        
        try:
            SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
        except Exception:
            pass
    except Exception:
        pass


def _pick_font_family() -> str:
    """เลือกฟอนต์ที่มีอยู่จริงในระบบ โดยให้ความสำคัญกับ Kanit"""
    try:
        root = tk.Tk()
        root.withdraw()
        families = set(tkfont.families(root))
        root.destroy()
    except Exception:
        families = set()

    preferred = ["Kanit", "Segoe UI", "Arial", "Tahoma"]
    for fam in preferred:
        if fam in families:
            return fam
    return preferred[2]


def _patch_customtkinter_defaults():
    """แทนที่ default behavior ของ CustomTkinter เพื่อใช้ฟอนต์ Kanit อัตโนมัติ"""
    try:
        # Patch CTkLabel
        original_label_init = ctk.CTkLabel.__init__
        def patched_label_init(self, *args, **kwargs):
            if 'font' not in kwargs and FONT_BODY is not None:
                kwargs['font'] = FONT_BODY
            return original_label_init(self, *args, **kwargs)
        ctk.CTkLabel.__init__ = patched_label_init
        
        # Patch CTkButton
        original_button_init = ctk.CTkButton.__init__
        def patched_button_init(self, *args, **kwargs):
            if 'font' not in kwargs and FONT_BUTTON is not None:
                kwargs['font'] = FONT_BUTTON
            return original_button_init(self, *args, **kwargs)
        ctk.CTkButton.__init__ = patched_button_init
        
        # Patch CTkEntry
        original_entry_init = ctk.CTkEntry.__init__
        def patched_entry_init(self, *args, **kwargs):
            if 'font' not in kwargs and FONT_BODY is not None:
                kwargs['font'] = FONT_BODY
            return original_entry_init(self, *args, **kwargs)
        ctk.CTkEntry.__init__ = patched_entry_init
        
        # Patch CTkTextbox
        original_textbox_init = ctk.CTkTextbox.__init__
        def patched_textbox_init(self, *args, **kwargs):
            if 'font' not in kwargs and FONT_BODY is not None:
                kwargs['font'] = FONT_BODY
            return original_textbox_init(self, *args, **kwargs)
        ctk.CTkTextbox.__init__ = patched_textbox_init
        
        # Patch CTkOptionMenu
        original_optionmenu_init = ctk.CTkOptionMenu.__init__
        def patched_optionmenu_init(self, *args, **kwargs):
            if 'font' not in kwargs and FONT_BODY is not None:
                kwargs['font'] = FONT_BODY
            return original_optionmenu_init(self, *args, **kwargs)
        ctk.CTkOptionMenu.__init__ = patched_optionmenu_init
        
    except Exception:
        pass

def init_fonts() -> None:
    """กำหนดฟอนต์ส่วนกลาง (เรียกครั้งเดียวพอ)"""
    global FONT_FAMILY, FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_SMALL, FONT_BUTTON, FONT_UNIFORM
    if FONT_FAMILY is not None:
        return

    # พยายามลงทะเบียน Kanit จากโฟลเดอร์ในโปรเจกต์ก่อน แล้วค่อยเลือก
    _register_kanit_fonts_if_available()
    FONT_FAMILY = _pick_font_family()
    
    # สร้าง CTkFont objects (จะทำงานได้เฉพาะเมื่อมี root window แล้ว)
    try:
        FONT_TITLE = ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold")
        FONT_SUBTITLE = ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")
        FONT_BODY = ctk.CTkFont(family=FONT_FAMILY, size=12)
        FONT_SMALL = ctk.CTkFont(family=FONT_FAMILY, size=10)
        FONT_BUTTON = ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")
        FONT_UNIFORM = ctk.CTkFont(family=FONT_FAMILY, size=12)
    except Exception:
        # สร้าง placeholder objects ที่จะถูกสร้างใหม่ภายหลัง
        FONT_TITLE = None
        FONT_SUBTITLE = None  
        FONT_BODY = None
        FONT_SMALL = None
        FONT_BUTTON = None
        FONT_UNIFORM = None
    
    # ตั้งค่า CustomTkinter default font
    try:
        # แก้ไข theme manager ของ CustomTkinter
        from customtkinter import ThemeManager
        if hasattr(ThemeManager, 'theme'):
            # อัพเดท theme สำหรับ widgets ต่างๆ
            theme_dict = ThemeManager.theme
            if "CTkFont" in theme_dict:
                theme_dict["CTkFont"]["family"] = FONT_FAMILY
            if "CTkLabel" in theme_dict:
                theme_dict["CTkLabel"]["font"] = (FONT_FAMILY, 12)
            if "CTkButton" in theme_dict:  
                theme_dict["CTkButton"]["font"] = (FONT_FAMILY, 12, "bold")
            if "CTkEntry" in theme_dict:
                theme_dict["CTkEntry"]["font"] = (FONT_FAMILY, 12)
            if "CTkTextbox" in theme_dict:
                theme_dict["CTkTextbox"]["font"] = (FONT_FAMILY, 12)
            if "CTkOptionMenu" in theme_dict:
                theme_dict["CTkOptionMenu"]["font"] = (FONT_FAMILY, 12)
    except Exception:
        pass

    # ปรับฟอนต์มาตรฐานของ Tk เพื่อครอบคลุมวิดเจ็ตที่ไม่ได้กำหนด font โดยตรง
    try:
        root = tk._get_default_root()
        if root is None:
            root = tk.Tk()
            root.withdraw()
            
        # ตั้งค่า default fonts ทั้งหมด
        font_names = [
            "TkDefaultFont",
            "TkTextFont", 
            "TkHeadingFont",
            "TkMenuFont",
            "TkCaptionFont",
            "TkSmallCaptionFont",
            "TkIconFont",
            "TkTooltipFont",
            "TkFixedFont"
        ]
        
        for name in font_names:
            try:
                f = tkfont.nametofont(name, root)
                original_size = f.cget("size")
                f.configure(family=FONT_FAMILY, size=abs(original_size) if original_size else 12)
            except Exception:
                pass
                
        # ตั้งค่า option database เพื่อให้ widgets ใหม่ใช้ฟอนต์ที่ต้องการ
        root.option_add("*Font", f"{FONT_FAMILY} 12")
        root.option_add("*font", f"{FONT_FAMILY} 12")
        
    except Exception:
        pass
    
    # Patch CustomTkinter widgets เพื่อใช้ฟอนต์ Kanit โดย default
    if FONT_BODY is not None:
        _patch_customtkinter_defaults()


def ensure_font_objects():
    """สร้าง CTkFont objects ถ้ายังไม่ได้สร้าง (เรียกหลังมี root window)"""
    global FONT_TITLE, FONT_SUBTITLE, FONT_BODY, FONT_SMALL, FONT_BUTTON, FONT_UNIFORM
    
    if FONT_BODY is None and FONT_FAMILY is not None:
        try:
            FONT_TITLE = ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold")
            FONT_SUBTITLE = ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold")
            FONT_BODY = ctk.CTkFont(family=FONT_FAMILY, size=12)
            FONT_SMALL = ctk.CTkFont(family=FONT_FAMILY, size=10)
            FONT_BUTTON = ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")
            FONT_UNIFORM = ctk.CTkFont(family=FONT_FAMILY, size=12)
            
            # Patch CustomTkinter defaults ตอนนี้
            _patch_customtkinter_defaults()
            
        except Exception:
            pass

def get_family() -> str:
    """คืนชื่อฟอนต์ที่ถูกเลือก (สำหรับ debug หรือใช้งานอื่นๆ)"""
    return FONT_FAMILY or ""


def apply_fonts(root_widget) -> None:
    """ใช้ฟอนต์ Kanit กับ widgets ทั้งหมด"""
    ensure_font_objects()
    
    if FONT_UNIFORM is None:
        return

    try:
        stack = [root_widget]
        
        while stack:
            w = stack.pop()
            try:
                # ใช้ฟอนต์กับ CTk widgets
                if isinstance(w, (ctk.CTkLabel, ctk.CTkCheckBox, ctk.CTkEntry, ctk.CTkTextbox)):
                    w.configure(font=FONT_UNIFORM)
                elif isinstance(w, ctk.CTkButton):
                    w.configure(font=FONT_BUTTON)
                elif isinstance(w, ctk.CTkOptionMenu):
                    w.configure(font=FONT_UNIFORM)
                elif isinstance(w, ctk.CTkTabview):
                    # ใช้ฟอนต์กับ tab labels
                    try:
                        seg = getattr(w, "_segmented_button", None)
                        if seg is not None:
                            seg.configure(font=FONT_UNIFORM)
                    except Exception:
                        pass
                
                # เพิ่ม child widgets
                try:
                    for child in w.winfo_children():
                        stack.append(child)
                except Exception:
                    pass
                    
            except Exception:
                pass
                
    except Exception:
        pass


