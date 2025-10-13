# PATTERNS QUICK GUIDE

> คู่มือสรุปแบบย่อสำหรับ Engineers - อ้างอิงเร็ว ๆ เมื่อเขียนโค้ด

---

## 📋 Table of Contents

1. [เมื่อไหร่ใช้ Pattern ไหน](#1-เมื่อไหร่ใช้-pattern-ไหน)
2. [Code Templates](#2-code-templates)
3. [Configuration Quick Ref](#3-configuration-quick-ref)
4. [Common Mistakes](#4-common-mistakes)
5. [Checklists](#5-checklists)

---

## 1. เมื่อไหร่ใช้ Pattern ไหน

### ต้องการจัดการหลาย Services
→ **ใช้ Orchestrator Pattern**
```python
# services/orchestrators/your_orchestrator.py
class YourOrchestrator:
    def __init__(self, log_callback=None):
        self.service_a = ServiceA()
        self.service_b = ServiceB()
```

### ต้องการสร้าง Service ใหม่
→ **ใช้ Service Layer Pattern**
```python
# services/category/your_service.py
class YourService:
    def process(self, data) -> Tuple[bool, Any]:
        try:
            return True, result
        except Exception as e:
            return False, str(e)
```

### ต้องการจัดการ UI Events
→ **ใช้ Handler Pattern**
```python
# ui/handlers/your_handler.py
class YourHandler:
    def __init__(self, services, log_callback):
        self.services = services
        self.log = log_callback
```

### ต้องการสร้าง Tab ใหม่
→ **ใช้ Tab Component Pattern**
```python
# ui/tabs/your_tab.py
class YourTab:
    def __init__(self, parent, callbacks):
        self.callbacks = callbacks
        self._create_ui()
```

### ต้องการสร้าง UI Component ที่ใช้ซ้ำได้
→ **ใช้ Reusable Component Pattern**
```python
# ui/components/your_component.py
class YourComponent(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
```

### ต้องการอ่าน/เขียน Configuration
→ **ใช้ JSONManager เสมอ**
```python
from config.json_manager import get_your_setting, set_your_setting
value = get_your_setting()
set_your_setting("new_value")
```

---

## 2. Code Templates

### 2.1 Orchestrator Template

```python
# services/orchestrators/your_orchestrator.py
"""
[Name] Orchestrator

Coordinates: [list services]
"""
from typing import Tuple, Any
import logging

class YourOrchestrator:
    """
    [Description]

    Responsibilities:
    - [Task 1]
    - [Task 2]
    """

    def __init__(self, log_callback=None):
        self.log = log_callback or logging.info

        # Initialize services
        self.service_a = ServiceA(self.log)
        self.service_b = ServiceB(self.log)

        # Load configuration
        self._load_configuration()

    def _load_configuration(self):
        """Load required configuration"""
        from config.json_manager import load_app_settings
        self.settings = load_app_settings()

    def main_operation(self, param) -> Tuple[bool, Any]:
        """
        [Description]

        Args:
            param: [description]

        Returns:
            Tuple[bool, Any]: (success, result_or_error)
        """
        try:
            # Step 1
            result_a = self.service_a.do_something(param)

            # Step 2
            result_b = self.service_b.process(result_a)

            self.log("✅ Operation completed")
            return True, result_b

        except Exception as e:
            self.log(f"❌ Error: {e}")
            return False, str(e)
```

### 2.2 Service Template

```python
# services/category/your_service.py
"""
[Name] Service

Handles: [description]
"""
from typing import Tuple, Any
import logging

class YourService:
    """
    [Description]

    Responsibility: [single responsibility]
    """

    def __init__(self, log_callback=None):
        self.log = log_callback or logging.info
        self._settings_loaded = False

    def _load_settings_if_needed(self):
        """Lazy load settings"""
        if not self._settings_loaded:
            self._load_settings()
            self._settings_loaded = True

    def _load_settings(self):
        """Load configuration"""
        from config.json_manager import load_app_settings
        self.settings = load_app_settings()

    def process(self, data) -> Tuple[bool, Any]:
        """
        [Description]

        Args:
            data: [description]

        Returns:
            Tuple[bool, Any]: (success, result_or_error)
        """
        try:
            self._load_settings_if_needed()

            # Processing logic
            result = self._internal_process(data)

            self.log("✅ Processing completed")
            return True, result

        except ValueError as e:
            self.log(f"❌ Invalid data: {e}")
            return False, str(e)
        except Exception as e:
            self.log(f"❌ Error: {e}")
            return False, str(e)

    def _internal_process(self, data):
        """Internal processing logic"""
        # Implementation
        pass
```

### 2.3 Handler Template

```python
# ui/handlers/your_handler.py
"""
[Name] Handler

Handles UI operations for: [description]
"""
import threading

class YourHandler:
    """
    [Description]
    """

    def __init__(self, service_a, service_b, log_callback):
        self.service_a = service_a
        self.service_b = service_b
        self.log = log_callback

    def handle_user_action(self, ui_callbacks):
        """
        Handle user action

        Args:
            ui_callbacks: Dict of UI callback functions
        """
        # Disable UI
        ui_callbacks['disable_controls']()

        # Start background thread
        thread = threading.Thread(
            target=self._process_in_background,
            args=(ui_callbacks,)
        )
        thread.start()

    def _process_in_background(self, ui_callbacks):
        """Process in background thread"""
        try:
            # Update progress
            ui_callbacks['update_progress'](0.3, "Processing...", "Step 1")

            # Use services
            success, result = self.service_a.do_something()

            if success:
                ui_callbacks['update_progress'](0.7, "Finalizing...", "Step 2")
                self.service_b.finalize(result)
                ui_callbacks['update_progress'](1.0, "Done", "Complete")
                self.log("✅ Operation completed")
            else:
                self.log(f"❌ Error: {result}")

        except Exception as e:
            self.log(f"❌ Unexpected error: {e}")
        finally:
            # Always re-enable UI
            ui_callbacks['enable_controls']()
```

### 2.4 Tab Component Template

```python
# ui/tabs/your_tab.py
"""
[Name] Tab Component
"""
import customtkinter as ctk
from tkinter import messagebox

class YourTab:
    """
    [Description]
    """

    def __init__(self, parent, callbacks):
        self.parent = parent
        self.callbacks = callbacks

        # Load settings
        self._load_settings()

        # Create UI
        self._create_ui()

    def _load_settings(self):
        """Load settings for this tab"""
        from config.json_manager import get_your_setting
        self.setting_value = get_your_setting()

    def _create_ui(self):
        """Create UI components"""
        self._create_toolbar()
        self._create_content_area()
        self._create_action_buttons()

    def _create_toolbar(self):
        """Create toolbar"""
        toolbar = ctk.CTkFrame(self.parent)
        toolbar.pack(fill="x", padx=10, pady=(8, 0))

        btn = ctk.CTkButton(toolbar, text="Action", command=self._handle_action)
        btn.pack(side="left", padx=5)

    def _create_content_area(self):
        """Create main content"""
        self.content = ctk.CTkScrollableFrame(self.parent, width=860, height=400)
        self.content.pack(pady=8, padx=10, fill="both", expand=True)

    def _create_action_buttons(self):
        """Create bottom buttons"""
        button_frame = ctk.CTkFrame(self.parent)
        button_frame.pack(pady=4)

        save_btn = ctk.CTkButton(button_frame, text="Save", command=self._handle_save)
        save_btn.pack(side="left", padx=5)

    def _handle_action(self):
        """Handle action button"""
        if 'on_action' in self.callbacks:
            self.callbacks['on_action']()

    def _handle_save(self):
        """Handle save button"""
        from config.json_manager import set_your_setting
        success = set_your_setting(self.setting_value)

        if success:
            messagebox.showinfo("Success", "Saved")
        else:
            messagebox.showerror("Error", "Failed to save")

    def enable_controls(self):
        """Enable all controls"""
        pass

    def disable_controls(self):
        """Disable all controls"""
        pass
```

### 2.5 UI Component Template

```python
# ui/components/your_component.py
"""
[Name] Component
"""
import customtkinter as ctk

class YourComponent(ctk.CTkFrame):
    """
    Reusable component for [description]

    Example:
        >>> component = YourComponent(parent, width=400)
        >>> component.pack(pady=10)
        >>> component.set_data(data)
    """

    def __init__(self, master, width=None, height=None, **kwargs):
        super().__init__(master, width=width, height=height, **kwargs)

        # State
        self.data = []

        # Create UI
        self._create_ui()

    def _create_ui(self):
        """Create internal UI"""
        self.label = ctk.CTkLabel(self, text="Component")
        self.label.pack(pady=5)

        self.content = ctk.CTkScrollableFrame(self)
        self.content.pack(fill="both", expand=True, padx=5, pady=5)

    # Public API
    def set_data(self, data: list):
        """Set data to display"""
        self.data = data
        self._refresh()

    def clear(self):
        """Clear all data"""
        self.data = []
        self._refresh()

    def get_selected(self):
        """Get selected items"""
        pass

    # Private methods
    def _refresh(self):
        """Refresh display"""
        for widget in self.content.winfo_children():
            widget.destroy()

        for item in self.data:
            label = ctk.CTkLabel(self.content, text=str(item))
            label.pack(pady=2)
```

---

## 3. Configuration Quick Ref

### 3.1 เพิ่ม Configuration ใหม่

**Step 1: เพิ่มใน JSONManager**
```python
# config/json_manager.py - ใน _initialize_file_configs()
'your_config': JSONFileConfig(
    filename='your_config.json',
    default_content={"setting1": "value"},
    required_keys=['setting1'],
    validation_func=self._validate_your_config
),

# เพิ่ม validation function
def _validate_your_config(self, content: Dict[str, Any]) -> bool:
    if not isinstance(content, dict):
        return False
    if 'setting1' not in content:
        return False
    return True
```

**Step 2: เพิ่ม Convenience Functions**
```python
# config/json_manager.py - ท้ายไฟล์

def load_your_config() -> Dict[str, Any]:
    return json_manager.load('your_config')

def save_your_config(config: Dict[str, Any]) -> bool:
    return json_manager.save('your_config', config)

def get_your_setting1() -> str:
    return json_manager.get('your_config', 'setting1', '')

def set_your_setting1(value: str) -> bool:
    return json_manager.set('your_config', 'setting1', value)
```

**Step 3: ใช้งาน**
```python
from config.json_manager import get_your_setting1, set_your_setting1

# Get
value = get_your_setting1()

# Set
success = set_your_setting1("new_value")
```

### 3.2 Configurations ที่มีอยู่

| Config Name | File | Get Function | Set Function |
|-------------|------|--------------|--------------|
| **app_settings** | app_settings.json | `load_app_settings()` | `save_app_settings()` |
| **input_folder** | input_folder_config.json | `get_input_folder()` | `set_input_folder()` |
| **output_folder** | output_folder_config.json | `get_output_folder()` | `set_output_folder()` |
| **log_folder** | log_folder_config.json | `get_log_folder()` | `set_log_folder()` |
| **column_settings** | column_settings.json | `load_column_settings()` | `save_column_settings()` |
| **dtype_settings** | dtype_settings.json | `load_dtype_settings()` | `save_dtype_settings()` |

---

## 4. Common Mistakes

### ❌ Mistake 1: Manual JSON Handling
```python
# ❌ Don't do this
import json
with open("config/my_config.json", 'r') as f:
    config = json.load(f)
```

### ✅ Fix: Use JSONManager
```python
# ✅ Do this
from config.json_manager import get_my_setting
value = get_my_setting()
```

---

### ❌ Mistake 2: UI Calling Services Directly
```python
# ❌ Don't do this
class MainTab:
    def __init__(self):
        self.db_service = DatabaseService()  # ❌
        self.file_service = FileService()    # ❌
```

### ✅ Fix: Use Handlers
```python
# ✅ Do this
class MainWindow:
    def __init__(self):
        # Create services
        self.db_service = DatabaseOrchestrator()
        self.file_service = FileOrchestrator()

        # Create handler with injected services
        self.file_handler = FileHandler(
            self.file_service,
            self.db_service,
            self.log
        )
```

---

### ❌ Mistake 3: Not Using Return Tuple Pattern
```python
# ❌ Don't do this
def process_data(data):
    if not data:
        raise ValueError("No data")
    return result
```

### ✅ Fix: Use Tuple Pattern
```python
# ✅ Do this
def process_data(data) -> Tuple[bool, Any]:
    if not data:
        return False, "No data"
    return True, result

# Usage
success, result = process_data(data)
if success:
    print(result)
else:
    print(f"Error: {result}")
```

---

### ❌ Mistake 4: No Logging
```python
# ❌ Don't do this
def process():
    result = do_something()
    return result
```

### ✅ Fix: Add Logging
```python
# ✅ Do this
def process():
    self.log("🔄 Starting process...")
    result = do_something()
    self.log("✅ Process completed")
    return result
```

---

### ❌ Mistake 5: Blocking UI Thread
```python
# ❌ Don't do this
def handle_button_click(self):
    # Long running operation in UI thread ❌
    result = long_running_operation()
```

### ✅ Fix: Use Threading
```python
# ✅ Do this
def handle_button_click(self):
    thread = threading.Thread(target=self._process_in_background)
    thread.start()

def _process_in_background(self):
    result = long_running_operation()
```

---

## 5. Checklists

### 5.1 เมื่อสร้าง Orchestrator ใหม่

- [ ] สร้างไฟล์ใน `services/orchestrators/`
- [ ] ใช้ชื่อตามรูปแบบ `*_orchestrator.py`
- [ ] มี docstring อธิบาย responsibilities
- [ ] ใช้ Dependency Injection
- [ ] มี `__init__` รับ `log_callback`
- [ ] Methods return `Tuple[bool, Any]`
- [ ] มี proper error handling
- [ ] มี logging ที่เหมาะสม

### 5.2 เมื่อสร้าง Service ใหม่

- [ ] สร้างไฟล์ใน `services/[category]/`
- [ ] ใช้ชื่อตามรูปแบบ `*_service.py`
- [ ] มี Single Responsibility
- [ ] มี lazy loading สำหรับ settings
- [ ] Methods return `Tuple[bool, Any]`
- [ ] มี type hints
- [ ] มี docstrings
- [ ] มี error handling

### 5.3 เมื่อสร้าง Handler ใหม่

- [ ] สร้างไฟล์ใน `ui/handlers/`
- [ ] ใช้ชื่อตามรูปแบบ `*_handler.py`
- [ ] รับ services ผ่าน constructor
- [ ] รับ `log_callback` สำหรับ logging
- [ ] ใช้ threading สำหรับ long operations
- [ ] รับ `ui_callbacks` dictionary
- [ ] Always disable/enable controls

### 5.4 เมื่อสร้าง Tab ใหม่

- [ ] สร้างไฟล์ใน `ui/tabs/`
- [ ] ใช้ชื่อตามรูปแบบ `*_tab.py`
- [ ] รับ `parent` และ `callbacks`
- [ ] มี `_create_ui()` method
- [ ] มี `enable_controls()` method
- [ ] มี `disable_controls()` method
- [ ] Load/save settings ผ่าน JSONManager

### 5.5 เมื่อสร้าง Component ใหม่

- [ ] สร้างไฟล์ใน `ui/components/`
- [ ] Inherit จาก `ctk.CTkFrame` หรือ widget ที่เหมาะสม
- [ ] มี clear public API
- [ ] มี docstring พร้อมตัวอย่าง
- [ ] Reusable และ self-contained
- [ ] มี proper state management

### 5.6 เมื่อเพิ่ม Configuration

- [ ] เพิ่มใน `json_manager.py` - `_initialize_file_configs()`
- [ ] เพิ่ม validation function
- [ ] เพิ่ม convenience functions
- [ ] มี default values
- [ ] มี type hints
- [ ] Test การโหลด/บันทึก

### 5.7 Code Review Checklist

**Architecture:**
- [ ] ใช้ pattern ที่เหมาะสม
- [ ] แยกชั้นอย่างถูกต้อง
- [ ] Dependency Injection

**Configuration:**
- [ ] ใช้ JSONManager
- [ ] ไม่มี manual JSON handling
- [ ] มี validation

**Error Handling:**
- [ ] Return `Tuple[bool, Any]`
- [ ] จับ specific exceptions
- [ ] มี proper error messages

**Logging:**
- [ ] ใช้ emoji-based logging
- [ ] Log level เหมาะสม
- [ ] ไม่ log sensitive data

**Code Style:**
- [ ] Naming conventions ถูกต้อง
- [ ] มี docstrings
- [ ] มี type hints
- [ ] Imports organized

**Testing:**
- [ ] มี unit tests
- [ ] Test ครอบคลุม error cases
- [ ] Manual test แล้ว

---

## 6. Emoji Reference

| Emoji | ใช้เมื่อ | ตัวอย่าง |
|-------|---------|----------|
| ✅ | Success | `"✅ Operation completed"` |
| ❌ | Error | `"❌ Failed to process"` |
| ⚠️ | Warning | `"⚠️ File size large"` |
| 📊 | Data/Stats | `"📊 Processing 1000 rows"` |
| 📂 | Folder | `"📂 Folder updated"` |
| 📁 | File | `"📁 Found 5 files"` |
| 📦 | Package/Move | `"📦 File moved"` |
| 📤 | Upload | `"📤 Uploading data"` |
| 🔄 | Processing | `"🔄 Loading config"` |
| 🔍 | Search | `"🔍 Scanning files"` |
| 🎉 | Completion | `"🎉 All done!"` |
| ⏱️ | Time | `"⏱️ Time: 5m 30s"` |
| 📋 | Phase | `"📋 Phase 1: Validation"` |

---

## 7. File Structure Quick Ref

```
PIPELINE_SQLSERVER/
├── config/
│   ├── json_manager.py        ⭐ Centralized config
│   └── database.py
├── services/
│   ├── orchestrators/         ⭐ High-level coordinators
│   │   ├── file_orchestrator.py
│   │   └── database_orchestrator.py
│   ├── database/              Service implementations
│   ├── file/
│   └── utilities/
├── ui/
│   ├── tabs/                  ⭐ Tab components
│   ├── components/            ⭐ Reusable UI
│   └── handlers/              ⭐ UI event handlers
├── utils/
├── constants.py               ⭐ All constants
└── main.py
```

---

## 8. Import Templates

### Standard Import Order

```python
# 1. Standard library
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 2. Third-party
import customtkinter as ctk
import pandas as pd
from tkinter import messagebox

# 3. Local - Config
from config.json_manager import load_app_settings, get_input_folder
from config.database import DatabaseConfig

# 4. Local - Services
from services.orchestrators.file_orchestrator import FileOrchestrator
from services.orchestrators.database_orchestrator import DatabaseOrchestrator

# 5. Local - UI
from ui.components.file_list import FileList
from ui.components.progress_bar import ProgressBar

# 6. Local - Utils
from utils.logger import setup_logging
from constants import AppConstants
```

---

## 9. Naming Quick Ref

| ประเภท | Convention | ตัวอย่าง |
|--------|------------|---------|
| Class | PascalCase | `FileOrchestrator` |
| Function | snake_case | `load_settings()` |
| Private Method | _snake_case | `_load_config()` |
| Variable | snake_case | `file_path` |
| Constant | UPPER_CASE | `MAX_WORKERS` |
| Module | snake_case | `file_handler.py` |

---

## 10. Contact & Help

**เมื่อมีคำถาม:**
1. ✅ ตรวจสอบ ENGINEERING_CONTEXT.md (รายละเอียดเต็ม)
2. ✅ ตรวจสอบ PATTERNS_QUICK_GUIDE.md (คู่มือนี้)
3. ✅ อ่าน code ที่มีอยู่ในโปรเจกต์
4. ✅ สอบถามทีม

**เอกสารที่เกี่ยวข้อง:**
- `README.md` - Setup & overview
- `ENGINEERING_CONTEXT.md` - Full guide
- `constants.py` - Constants reference
- `config/json_manager.py` - Config system

---

**Quick tip:** Copy templates จากเอกสารนี้และแก้ไขตามที่ต้องการ แทนการเขียนใหม่ทั้งหมด

_Last Updated: 2025-01-XX_
