# ENGINEERING CONTEXT - PIPELINE_SQLSERVER

> **คู่มือสำหรับ Engineers ที่จะอัปเดทหรือเขียนโค้ดต่อให้เป็น Pattern เดียวกัน**
>
> เอกสารนี้อธิบายรูปแบบการเขียนโค้ด (Code Patterns) ที่ใช้ในโปรเจกต์ PIPELINE_SQLSERVER
> เพื่อให้ทีมพัฒนาสามารถเขียนโค้ดที่สอดคล้องและมีคุณภาพเท่าเทียมกัน

---

## 📚 สารบัญ

1. [ภาพรวมโครงสร้างโปรเจกต์](#1-ภาพรวมโครงสร้างโปรเจกต์)
2. [Architecture Patterns](#2-architecture-patterns)
3. [Configuration Management](#3-configuration-management)
4. [UI Development Patterns](#4-ui-development-patterns)
5. [Data Flow & Processing](#5-data-flow--processing)
6. [Code Style Guidelines](#6-code-style-guidelines)
7. [Testing Patterns](#7-testing-patterns)
8. [Checklist สำหรับการ Code Review](#8-checklist-สำหรับการ-code-review)

---

## 1. ภาพรวมโครงสร้างโปรเจกต์

### 1.1 Layered Architecture

โปรเจกต์ใช้หลักการ **Separation of Concerns** แบ่งเป็น 3 ชั้นหลัก:

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │  <- UI, User Interaction
│  (ui/tabs, ui/components, ui/handlers)  │
├─────────────────────────────────────────┤
│        Business Logic Layer             │  <- Core Logic
│  (services/orchestrators, services/*)   │
├─────────────────────────────────────────┤
│           Data Layer                    │  <- Configuration, Database
│  (config/, constants.py)                │
└─────────────────────────────────────────┘
```

### 1.2 โครงสร้างไดเรกทอรี

```
PIPELINE_SQLSERVER/
├── config/                          # Configuration Layer
│   ├── json_manager.py             # ⭐ Centralized config management
│   ├── database.py                 # Database configuration
│   └── *.json                      # Configuration files
│
├── services/                        # Business Logic Layer
│   ├── orchestrators/              # ⭐ High-level coordinators
│   │   ├── file_orchestrator.py   # File operations coordinator
│   │   ├── database_orchestrator.py
│   │   └── ...
│   ├── database/                   # Database operations
│   │   ├── connection_service.py
│   │   ├── schema_service.py
│   │   ├── data_upload_service.py
│   │   └── validation/             # Validator services
│   ├── file/                       # File operations
│   │   ├── file_reader_service.py
│   │   ├── data_processor_service.py
│   │   └── file_management_service.py
│   └── utilities/                  # Utility services
│       └── preload_service.py
│
├── ui/                             # Presentation Layer
│   ├── tabs/                       # Tab components
│   │   ├── main_tab.py
│   │   ├── log_tab.py
│   │   └── settings_tab.py
│   ├── components/                 # Reusable UI components
│   │   ├── file_list.py
│   │   ├── progress_bar.py
│   │   └── status_bar.py
│   └── handlers/                   # UI event handlers
│       ├── file_handler.py
│       └── settings_handler.py
│
├── utils/                          # Shared Utilities
│   ├── logger.py                   # Logging utilities
│   ├── helpers.py
│   └── validators.py
│
├── constants.py                    # ⭐ Application constants
├── main.py                         # GUI entry point
└── auto_process_cli.py            # CLI entry point
```

**หมายเหตุ:**
- ⭐ = ไฟล์สำคัญที่ควรทำความเข้าใจก่อน
- ห้ามข้ามชั้น (เช่น UI ไม่เรียก database service โดยตรง)
- ใช้ Dependency Injection ผ่าน constructor

---

## 2. Architecture Patterns

### 2.1 Orchestrator Pattern ⭐

**คำถาม:** เมื่อไหร่ควรสร้าง Orchestrator?

**คำตอบ:** เมื่อมี services มากกว่า 2 ตัวที่ต้องทำงานร่วมกัน

**โครงสร้าง Orchestrator:**

```python
# services/orchestrators/your_orchestrator.py
class YourOrchestrator:
    """
    [ชื่อ Orchestrator] Orchestrator

    Description: [อธิบายหน้าที่หลัก]

    Responsibilities:
    - [รายการหน้าที่ 1]
    - [รายการหน้าที่ 2]
    - [รายการหน้าที่ 3]

    Example:
        >>> orchestrator = YourOrchestrator(log_callback=logging.info)
        >>> result = orchestrator.do_something()
    """

    def __init__(self, log_callback=None):
        """
        Initialize orchestrator with dependencies

        Args:
            log_callback: Function for logging (default: logging.info)
        """
        self.log = log_callback or logging.info

        # สร้าง service instances ที่ต้องใช้
        self.service_a = ServiceA(self.log)
        self.service_b = ServiceB(self.log)
        self.service_c = ServiceC(self.log)

        # โหลด configuration
        self._load_configuration()

    def _load_configuration(self):
        """โหลดการตั้งค่าที่จำเป็น (private method)"""
        from config.json_manager import load_app_settings
        self.settings = load_app_settings()

    # Public methods - ใช้สำหรับเรียกจาก client code
    def main_operation(self, param1, param2):
        """
        [อธิบายการทำงานหลัก]

        Args:
            param1: [อธิบาย parameter]
            param2: [อธิบาย parameter]

        Returns:
            Tuple[bool, Any]: (success, result_or_error)
        """
        try:
            # Step 1: ใช้ Service A
            result_a = self.service_a.do_something(param1)

            # Step 2: ใช้ Service B
            result_b = self.service_b.process(result_a)

            # Step 3: ใช้ Service C
            final_result = self.service_c.finalize(result_b, param2)

            self.log(f"✅ Operation completed successfully")
            return True, final_result

        except Exception as e:
            self.log(f"❌ Operation failed: {e}")
            return False, str(e)

    # Private methods - ใช้ภายในเท่านั้น
    def _helper_method(self, data):
        """[อธิบายการทำงานของ helper]"""
        # Implementation
        pass
```

**ตัวอย่างที่มีอยู่ในโปรเจกต์:**

1. **FileOrchestrator** - ประสานงาน file reading, processing, management
2. **DatabaseOrchestrator** - ประสานงาน connection, schema, upload, validation
3. **ValidationOrchestrator** - ประสานงาน validators หลายตัว

**❌ ไม่ควรทำ:**
```python
# ❌ Client ไม่ควรรู้จัก internal services
file_reader = FileReaderService()
data_processor = DataProcessorService()
file_manager = FileManagementService()

# ❌ Client ไม่ควรเรียก services แยกกัน
df = file_reader.read(file_path)
processed_df = data_processor.process(df)
file_manager.move_file(file_path)
```

**✅ ควรทำ:**
```python
# ✅ Client เรียกผ่าน Orchestrator
file_service = FileOrchestrator(log_callback=logging.info)
success, result = file_service.read_and_process_file(file_path, logic_type)
```

### 2.2 Service Layer Pattern

**หลักการ:** แต่ละ Service มีหน้าที่เฉพาะทาง (Single Responsibility Principle)

**โครงสร้าง Service:**

```python
# services/[category]/your_service.py
class YourService:
    """
    [ชื่อ Service] Service

    Responsibility: [อธิบายหน้าที่เฉพาะทาง]

    Example:
        >>> service = YourService(log_callback=logging.info)
        >>> result = service.process_data(data)
    """

    def __init__(self, log_callback=None):
        """
        Initialize service

        Args:
            log_callback: Function for logging
        """
        self.log = log_callback or logging.info
        self._settings_loaded = False

        # Lazy loading
        self._load_settings_if_needed()

    def _load_settings_if_needed(self):
        """โหลดการตั้งค่าครั้งเดียว (Lazy Loading Pattern)"""
        if not self._settings_loaded:
            self._load_settings()
            self._settings_loaded = True

    def _load_settings(self):
        """โหลดการตั้งค่าจริง"""
        from config.json_manager import load_app_settings
        self.settings = load_app_settings()

    def main_method(self, input_data) -> Tuple[bool, Any]:
        """
        [อธิบายการทำงานหลัก]

        Args:
            input_data: [อธิบาย input]

        Returns:
            Tuple[bool, Any]: (success, result_or_error)
        """
        try:
            self._load_settings_if_needed()

            # Processing logic
            result = self._process_internal(input_data)

            return True, result

        except Exception as e:
            self.log(f"❌ Error in {self.__class__.__name__}: {e}")
            return False, str(e)

    def _process_internal(self, data):
        """[อธิบาย internal processing]"""
        # Implementation
        pass
```

**แนวทางการแบ่ง Services:**

| หมวดหมู่ | ตัวอย่าง Service | หน้าที่ |
|----------|------------------|---------|
| **file/** | FileReaderService | อ่านไฟล์ Excel/CSV |
| | DataProcessorService | ประมวลผล/แปลงข้อมูล |
| | FileManagementService | ย้าย/จัดการไฟล์ |
| **database/** | ConnectionService | จัดการ database connection |
| | SchemaService | จัดการ table schema |
| | DataUploadService | อัปโหลดข้อมูล |
| | DataValidationService | ตรวจสอบข้อมูล |
| **utilities/** | PreloadService | โหลดข้อมูลล่วงหน้า |
| | PermissionCheckerService | ตรวจสอบสิทธิ์ |

### 2.3 Handler Pattern (UI Layer)

**หลักการ:** แยก UI logic ออกจาก UI components

**โครงสร้าง Handler:**

```python
# ui/handlers/your_handler.py
class YourHandler:
    """
    [ชื่อ Handler] Handler

    Handles UI operations for [อธิบายส่วนงาน]

    Example:
        >>> handler = YourHandler(service_a, service_b, log_callback=gui_log)
        >>> handler.handle_button_click()
    """

    def __init__(self, service_a, service_b, log_callback):
        """
        Initialize handler with injected dependencies

        Args:
            service_a: Instance of ServiceA
            service_b: Instance of ServiceB
            log_callback: Function to call for logging to UI
        """
        self.service_a = service_a
        self.service_b = service_b
        self.log = log_callback

    def handle_user_action(self, ui_callbacks):
        """
        Handle user action (e.g., button click)

        Args:
            ui_callbacks: Dictionary of UI callback functions
        """
        # Disable UI during processing
        ui_callbacks['disable_controls']()

        # Start background thread
        thread = threading.Thread(
            target=self._process_in_background,
            args=(ui_callbacks,)
        )
        thread.start()

    def _process_in_background(self, ui_callbacks):
        """Process data in background thread"""
        try:
            # Update progress
            ui_callbacks['update_progress'](0.3, "Processing...", "Step 1 of 3")

            # Use services
            success, result = self.service_a.do_something()

            if success:
                ui_callbacks['update_progress'](0.7, "Finalizing...", "Step 2 of 3")
                self.service_b.finalize(result)

                # Complete
                ui_callbacks['update_progress'](1.0, "Done", "Completed")
                self.log("✅ Operation completed")
            else:
                self.log(f"❌ Error: {result}")

        except Exception as e:
            self.log(f"❌ Unexpected error: {e}")
        finally:
            # Always re-enable UI
            ui_callbacks['enable_controls']()
```

**UI Callbacks Dictionary Pattern:**

```python
# In MainWindow or Tab component
def _get_ui_callbacks(self):
    """สร้าง dictionary ของ UI callbacks สำหรับส่งให้ handlers"""
    return {
        # Progress Bar
        'reset_progress': self.progress_bar.reset,
        'set_progress_status': self.progress_bar.set_status,
        'update_progress': self.progress_bar.update,

        # File List
        'clear_file_list': self.file_list.clear,
        'add_file_to_list': self.file_list.add_file,

        # Status Bar
        'update_status': self.status_bar.update_status,

        # Controls
        'disable_controls': self.main_tab_ui.disable_controls,
        'enable_controls': self.main_tab_ui.enable_controls,
    }
```

---

## 3. Configuration Management

### 3.1 ⭐ JSONManager - Centralized Configuration

**หลักการ:** ทุกการอ่าน/เขียน JSON ต้องผ่าน JSONManager เท่านั้น

**❌ ห้ามทำ:**
```python
# ❌ ห้ามอ่าน/เขียน JSON file โดยตรง
import json
with open("config/my_settings.json", 'r') as f:
    settings = json.load(f)

with open("config/my_settings.json", 'w') as f:
    json.dump(settings, f)
```

**✅ ต้องทำ:**
```python
# ✅ ใช้ JSONManager และ Convenience Functions
from config.json_manager import get_output_folder, set_output_folder

# Get
output_path = get_output_folder()

# Set
success = set_output_folder("/path/to/folder")
```

### 3.2 การเพิ่ม Configuration ใหม่

**ขั้นตอนที่ 1: เพิ่ม Config ใน JSONManager**

```python
# config/json_manager.py

# 1. เพิ่มใน _initialize_file_configs()
def _initialize_file_configs(self) -> Dict[str, JSONFileConfig]:
    return {
        # ... existing configs ...

        'your_new_config': JSONFileConfig(
            filename='your_config.json',
            default_content={
                "setting1": "default_value",
                "setting2": 100
            },
            required_keys=['setting1'],  # Optional
            backup_enabled=True,
            validation_func=self._validate_your_config
        ),
    }

# 2. เพิ่ม validation function
def _validate_your_config(self, content: Dict[str, Any]) -> bool:
    """Validate your configuration."""
    if not isinstance(content, dict):
        return False
    if 'setting1' not in content:
        return False
    # เพิ่ม validation rules ที่ต้องการ
    return True
```

**ขั้นตอนที่ 2: เพิ่ม Convenience Functions**

```python
# config/json_manager.py (ท้ายไฟล์)

def load_your_config() -> Dict[str, Any]:
    """Load your configuration."""
    return json_manager.load('your_new_config')

def save_your_config(config: Dict[str, Any]) -> bool:
    """Save your configuration."""
    return json_manager.save('your_new_config', config)

def get_your_setting1() -> str:
    """Get setting1 from your_config.json"""
    return json_manager.get('your_new_config', 'setting1', '')

def set_your_setting1(value: str) -> bool:
    """Set setting1 to your_config.json"""
    return json_manager.set('your_new_config', 'setting1', value)
```

**ขั้นตอนที่ 3: ใช้งาน**

```python
# ในไฟล์อื่นๆ
from config.json_manager import get_your_setting1, set_your_setting1

# Get
value = get_your_setting1()

# Set
success = set_your_setting1("new_value")
```

### 3.3 Configuration Best Practices

**1. ใช้ Type Hints:**
```python
def get_window_size() -> Tuple[int, int]:
    settings = load_app_settings()
    return tuple(settings.get('window_size', [900, 780]))
```

**2. ให้ Default Value:**
```python
def get_log_level() -> str:
    return json_manager.get('app_settings', 'log_level', 'INFO')
```

**3. Validate ก่อน Save:**
```python
def save_window_size(width: int, height: int) -> bool:
    # Validate
    if width < 800 or height < 600:
        logging.error("Window size too small")
        return False

    # Save
    settings = load_app_settings()
    settings['window_size'] = [width, height]
    return save_app_settings(settings)
```

**4. ใช้ Constants:**
```python
# constants.py
class ConfigKeys:
    WINDOW_SIZE = 'window_size'
    LOG_LEVEL = 'log_level'
    THEME = 'theme'

# Usage
from constants import ConfigKeys
settings = load_app_settings()
window_size = settings.get(ConfigKeys.WINDOW_SIZE)
```

---

## 4. UI Development Patterns

### 4.1 Tab Component Pattern

**หลักการ:** แต่ละ Tab เป็น component แยกที่รับ callbacks

**โครงสร้าง Tab:**

```python
# ui/tabs/your_tab.py
class YourTab:
    """
    [ชื่อ Tab] Tab Component

    Displays [อธิบายส่วนงาน]

    Args:
        parent: Parent widget
        callbacks: Dictionary of callback functions
    """

    def __init__(self, parent, callbacks):
        """
        Initialize tab component

        Args:
            parent: Parent widget (CTkFrame)
            callbacks: Dict of callback functions from MainWindow
        """
        self.parent = parent
        self.callbacks = callbacks

        # Load settings
        self._load_settings()

        # Create UI
        self._create_ui()

    def _load_settings(self):
        """โหลดการตั้งค่าที่เกี่ยวข้องกับ tab นี้"""
        from config.json_manager import get_your_setting
        self.setting_value = get_your_setting()

    def _create_ui(self):
        """Create all UI components in this tab"""
        # สร้าง UI ทีละส่วน
        self._create_toolbar()
        self._create_content_area()
        self._create_action_buttons()

    def _create_toolbar(self):
        """Create toolbar section"""
        toolbar = ctk.CTkFrame(self.parent)
        toolbar.pack(fill="x", padx=10, pady=(8, 0))

        # ปุ่มต่างๆ
        btn1 = ctk.CTkButton(
            toolbar,
            text="Action 1",
            command=self._handle_action1,
            width=120
        )
        btn1.pack(side="left", padx=5)

    def _create_content_area(self):
        """Create main content area"""
        # Scrollable frame สำหรับเนื้อหา
        self.content_frame = ctk.CTkScrollableFrame(
            self.parent,
            width=860,
            height=400
        )
        self.content_frame.pack(pady=8, padx=10, fill="both", expand=True)

    def _create_action_buttons(self):
        """Create action buttons at bottom"""
        button_frame = ctk.CTkFrame(self.parent)
        button_frame.pack(pady=4)

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._handle_save,
            width=120
        )
        save_btn.pack(side="left", padx=5)

    # Event handlers
    def _handle_action1(self):
        """Handle action 1 button click"""
        # เรียก callback ที่ได้รับจาก MainWindow
        if 'on_action1' in self.callbacks:
            self.callbacks['on_action1']()

    def _handle_save(self):
        """Handle save button click"""
        # Save logic
        from config.json_manager import set_your_setting
        success = set_your_setting(self.setting_value)

        if success:
            messagebox.showinfo("Success", "Settings saved")
        else:
            messagebox.showerror("Error", "Failed to save settings")

    # Public methods
    def enable_controls(self):
        """เปิดการใช้งานปุ่มทั้งหมด"""
        # Implementation
        pass

    def disable_controls(self):
        """ปิดการใช้งานปุ่มทั้งหมด"""
        # Implementation
        pass
```

**การใช้งานใน MainWindow:**

```python
# ui/main_window.py
class MainWindow(ctk.CTkToplevel):
    def _create_your_tab(self, parent):
        """Create components in Your Tab"""
        # Define callbacks
        callbacks = {
            'on_action1': self._handle_tab_action1,
            'on_action2': self._handle_tab_action2,
        }

        # Create tab component
        self.your_tab_ui = YourTab(parent, callbacks)

    def _handle_tab_action1(self):
        """Handle action 1 from your tab"""
        # Implementation
        pass
```

### 4.2 Reusable Component Pattern

**หลักการ:** สร้าง component ที่ใช้ซ้ำได้หลายที่

**ตัวอย่าง Component:**

```python
# ui/components/your_component.py
import customtkinter as ctk

class YourComponent(ctk.CTkFrame):
    """
    [ชื่อ Component] Component

    A reusable component for [อธิบายการใช้งาน]

    Example:
        >>> component = YourComponent(parent, width=400, height=300)
        >>> component.pack(pady=10)
        >>> component.set_data(data)
    """

    def __init__(self, master, width=None, height=None, **kwargs):
        """
        Initialize component

        Args:
            master: Parent widget
            width: Component width (optional)
            height: Component height (optional)
            **kwargs: Additional CTkFrame parameters
        """
        super().__init__(master, width=width, height=height, **kwargs)

        # State variables
        self.data = []

        # Create internal UI
        self._create_ui()

    def _create_ui(self):
        """Create internal UI elements"""
        # สร้าง UI ภายใน component
        self.label = ctk.CTkLabel(self, text="Component Title")
        self.label.pack(pady=5)

        self.listbox = ctk.CTkScrollableFrame(self)
        self.listbox.pack(fill="both", expand=True, padx=5, pady=5)

    # Public API
    def set_data(self, data: list):
        """
        Set data to display in component

        Args:
            data: List of items to display
        """
        self.data = data
        self._refresh_display()

    def clear(self):
        """Clear all data from component"""
        self.data = []
        self._refresh_display()

    def get_selected(self):
        """
        Get currently selected items

        Returns:
            List of selected items
        """
        # Implementation
        pass

    # Private methods
    def _refresh_display(self):
        """Refresh the display with current data"""
        # Clear existing widgets
        for widget in self.listbox.winfo_children():
            widget.destroy()

        # Add new widgets
        for item in self.data:
            label = ctk.CTkLabel(self.listbox, text=str(item))
            label.pack(pady=2)
```

**Components ที่มีอยู่:**

| Component | หน้าที่ | ตำแหน่ง |
|-----------|---------|---------|
| **FileList** | แสดงรายการไฟล์พร้อม checkbox | ui/components/file_list.py |
| **ProgressBar** | แสดง progress bar พร้อม status | ui/components/progress_bar.py |
| **StatusBar** | แสดง status message | ui/components/status_bar.py |

### 4.3 Callback Pattern

**หลักการ:** ใช้ callbacks เพื่อ decouple components

**Pattern 1: Simple Callback**

```python
# Tab component
class MyTab:
    def __init__(self, parent, callbacks):
        self.callbacks = callbacks

    def _handle_button_click(self):
        # เรียก callback
        if 'on_button_click' in self.callbacks:
            self.callbacks['on_button_click'](some_data)

# MainWindow
class MainWindow:
    def _create_tab(self, parent):
        callbacks = {
            'on_button_click': self._handle_button_data
        }
        self.tab = MyTab(parent, callbacks)

    def _handle_button_data(self, data):
        # Process data
        pass
```

**Pattern 2: UI Callbacks Dictionary**

```python
# Handler
class FileHandler:
    def process_files(self, ui_callbacks):
        # Update UI
        ui_callbacks['update_progress'](0.5, "Processing...", "50%")

        # Process data
        result = self._process()

        # Update UI again
        ui_callbacks['update_status']("Completed", False)

# MainWindow
class MainWindow:
    def _start_processing(self):
        ui_callbacks = {
            'update_progress': self.progress_bar.update,
            'update_status': self.status_bar.update_status,
            'disable_controls': self.main_tab.disable_controls,
            'enable_controls': self.main_tab.enable_controls,
        }

        self.file_handler.process_files(ui_callbacks)
```

### 4.4 Async UI Building Pattern

**หลักการ:** สร้าง UI แบบ progressive เพื่อไม่ให้ค้าง

```python
class SettingsTab:
    def __init__(self, parent, settings, callbacks, progress_callback=None):
        self.parent = parent
        self.settings = settings
        self.callbacks = callbacks
        self.progress_callback = progress_callback

        # Start async building
        self._start_async_build()

    def _start_async_build(self):
        """เริ่มสร้าง UI แบบ async"""
        if self.progress_callback:
            self.progress_callback("Building Settings Tab...")

        # สร้างส่วนแรก
        self._create_toolbar()

        # สร้างส่วนถัดไปใน next frame
        self.parent.after(10, self._create_content_step1)

    def _create_content_step1(self):
        """สร้างเนื้อหาส่วนที่ 1"""
        if self.progress_callback:
            self.progress_callback("Building content (step 1)...")

        # Create UI elements
        self._create_section1()

        # Continue with next step
        self.parent.after(10, self._create_content_step2)

    def _create_content_step2(self):
        """สร้างเนื้อหาส่วนที่ 2"""
        if self.progress_callback:
            self.progress_callback("Building content (step 2)...")

        # Create UI elements
        self._create_section2()

        # Done
        if self.progress_callback:
            self.progress_callback("Settings Tab completed")
```

**เมื่อไหร่ควรใช้ Async Building:**
- เมื่อมี UI elements มากกว่า 50 ชิ้น
- เมื่อต้องโหลดข้อมูลจาก file/database
- เมื่อต้องสร้าง UI แบบ dynamic จาก configuration

---

## 5. Data Flow & Processing

### 5.1 Pipeline Pattern

**Data Flow:**

```
┌──────────────┐
│ File Reading │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Processing  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Validation  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Upload    │
└──────────────┘
```

**ตัวอย่าง Implementation:**

```python
def process_file_pipeline(file_path, logic_type):
    """
    Process file through pipeline

    Pipeline stages:
    1. File Reading
    2. Data Processing
    3. Data Validation
    4. Database Upload
    """

    # Stage 1: File Reading
    log("📖 Stage 1: Reading file...")
    success, df = file_service.read_excel_file(file_path, logic_type)
    if not success:
        return False, f"Reading failed: {df}"

    # Stage 2: Data Processing
    log("🔄 Stage 2: Processing data...")
    success, processed_df = data_processor.process_dataframe(df, logic_type)
    if not success:
        return False, f"Processing failed: {processed_df}"

    # Stage 3: Data Validation (in SQL)
    log("✅ Stage 3: Validation will be done in SQL...")
    required_cols = file_service.get_required_dtypes(logic_type)

    # Stage 4: Database Upload
    log("📤 Stage 4: Uploading to database...")
    success, message = db_service.upload_data(
        processed_df,
        logic_type,
        required_cols,
        log_func=log,
        clear_existing=True
    )

    if success:
        log(f"🎉 Pipeline completed successfully")
        return True, message
    else:
        log(f"❌ Upload failed: {message}")
        return False, message
```

### 5.2 Error Handling Pattern

**Return Tuple Pattern:**

```python
def your_method(param) -> Tuple[bool, Any]:
    """
    [อธิบายการทำงาน]

    Args:
        param: [อธิบาย parameter]

    Returns:
        Tuple[bool, Any]: (success, result_or_error_message)
            - If success: (True, result_data)
            - If failed: (False, error_message)

    Example:
        >>> success, result = your_method(data)
        >>> if success:
        >>>     print(f"Success: {result}")
        >>> else:
        >>>     print(f"Error: {result}")
    """
    try:
        # Validation
        if not param:
            return False, "Parameter cannot be empty"

        # Processing
        result = self._process(param)

        # Success
        self.log(f"✅ Processing completed")
        return True, result

    except FileNotFoundError as e:
        error_msg = f"File not found: {e}"
        self.log(f"❌ {error_msg}")
        return False, error_msg

    except ValueError as e:
        error_msg = f"Invalid value: {e}"
        self.log(f"❌ {error_msg}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        self.log(f"❌ {error_msg}")
        return False, error_msg
```

**Usage:**

```python
# Caller
success, result = service.your_method(data)
if success:
    # Handle success case
    print(f"Result: {result}")
    next_operation(result)
else:
    # Handle error case
    logging.error(f"Error: {result}")
    show_error_dialog(result)
```

**Exception Hierarchy:**

```python
# Best Practice: จับ exception แบบ specific ก่อน
try:
    # Your code
    pass
except FileNotFoundError:
    # Handle file not found
    pass
except PermissionError:
    # Handle permission denied
    pass
except json.JSONDecodeError:
    # Handle invalid JSON
    pass
except ValueError:
    # Handle invalid value
    pass
except Exception as e:
    # Handle unexpected errors
    logging.exception("Unexpected error occurred")
    pass
```

### 5.3 Logging Pattern

**Emoji-based Logging:**

```python
# Success
self.log("✅ Operation completed successfully")

# Error
self.log("❌ Failed to process file")

# Warning
self.log("⚠️ No files found in folder")

# Info
self.log("📊 Processing 1000 rows")
self.log("📁 Folder updated: /path/to/folder")
self.log("📁 Found 5 files")

# File operations
self.log("📦 File moved to: /new/path")
self.log("📤 Uploading data...")

# Progress
self.log("🔄 Loading configuration...")
self.log("🔍 Scanning files...")

# Completion
self.log("🎉 All tasks completed!")

# Time
self.log("⏱️ Processing time: 5m 30s")

# Phase markers
self.log("📋 Phase 1: Validation")
```

**Structured Logging (Optional):**

```python
# Enable structured logging via environment variable
# STRUCTURED_LOGGING=true

# JSON format for log aggregation
{
    "timestamp": 1234567890.123,
    "level": "INFO",
    "message": "File uploaded successfully",
    "module": "file_handler",
    "function": "upload_file",
    "line": 123,
    "extra_data": {
        "file_path": "/path/to/file.xlsx",
        "rows": 1000
    }
}
```

### 5.4 Performance Patterns

**Pattern 1: Parallel Processing**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_files_parallel(files, max_workers=4):
    """ประมวลผลไฟล์แบบ parallel"""

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_file, file): file
            for file in files
        }

        # Collect results as they complete
        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
                log(f"✅ Processed: {file}")
            except Exception as e:
                log(f"❌ Error processing {file}: {e}")

    return results

def process_single_file(file):
    """ประมวลผลไฟล์เดียว (worker function)"""
    # Processing logic
    return result
```

**Pattern 2: Chunked Processing**

```python
def process_large_file(file_path, chunk_size=50000):
    """อ่านและประมวลผลไฟล์ขนาดใหญ่แบบ chunk"""

    chunks = []

    # Read in chunks
    if file_path.endswith('.csv'):
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            processed_chunk = process_chunk(chunk)
            chunks.append(processed_chunk)
    else:
        for chunk in pd.read_excel(file_path, chunksize=chunk_size):
            processed_chunk = process_chunk(chunk)
            chunks.append(processed_chunk)

    # Combine all chunks
    return pd.concat(chunks, ignore_index=True)

def process_chunk(chunk):
    """ประมวลผล chunk เดียว"""
    # Processing logic
    return chunk
```

**Pattern 3: Memory Optimization**

```python
def optimize_dataframe_memory(df):
    """ลด memory usage ของ DataFrame"""

    for col in df.columns:
        col_type = df[col].dtype

        if col_type == 'int64':
            # ลด int64 เป็น int32 ถ้าได้
            if df[col].min() > np.iinfo(np.int32).min and \
               df[col].max() < np.iinfo(np.int32).max:
                df[col] = df[col].astype(np.int32)

        elif col_type == 'float64':
            # ลด float64 เป็น float32
            df[col] = df[col].astype(np.float32)

        elif col_type == 'object':
            # แปลง object เป็น category ถ้ามีค่าซ้ำมาก
            num_unique_values = len(df[col].unique())
            num_total_values = len(df[col])
            if num_unique_values / num_total_values < 0.5:
                df[col] = df[col].astype('category')

    return df
```

**Pattern 4: Caching**

```python
class CachedService:
    def __init__(self):
        self._cache = {}
        self._cache_timestamps = {}

    def get_data(self, key, cache_duration=300):
        """
        Get data with caching

        Args:
            key: Cache key
            cache_duration: Cache duration in seconds (default: 5 minutes)
        """
        import time

        # Check if cached and not expired
        if key in self._cache:
            timestamp = self._cache_timestamps.get(key, 0)
            if time.time() - timestamp < cache_duration:
                return self._cache[key]

        # Load data
        data = self._load_data(key)

        # Update cache
        self._cache[key] = data
        self._cache_timestamps[key] = time.time()

        return data

    def clear_cache(self):
        """Clear all cache"""
        self._cache.clear()
        self._cache_timestamps.clear()
```

---

## 6. Code Style Guidelines

### 6.1 Naming Conventions

| ประเภท | Convention | ตัวอย่าง |
|--------|------------|---------|
| **Class** | PascalCase | `FileOrchestrator`, `DatabaseService` |
| **Function/Method** | snake_case | `load_settings()`, `process_data()` |
| **Private Method** | _snake_case | `_load_config()`, `_process_internal()` |
| **Variable** | snake_case | `file_path`, `column_settings` |
| **Constant** | UPPER_CASE | `MAX_WORKERS`, `DEFAULT_TIMEOUT` |
| **Module** | snake_case | `file_handler.py`, `json_manager.py` |

**ตัวอย่าง:**

```python
# ✅ Good
class FileOrchestrator:
    MAX_RETRIES = 3  # Constant

    def __init__(self):
        self.file_path = ""  # Variable

    def read_excel_file(self, file_path):  # Public method
        return self._load_file(file_path)

    def _load_file(self, path):  # Private method
        pass

# ❌ Bad
class fileOrchestrator:  # ❌ Should be PascalCase
    maxRetries = 3  # ❌ Constant should be UPPER_CASE

    def ReadExcelFile(self, FilePath):  # ❌ Should be snake_case
        return self.LoadFile(FilePath)  # ❌ Private should have _

    def LoadFile(self, Path):
        pass
```

### 6.2 Docstrings

**Module Docstring:**

```python
"""
[ชื่อโมดูล] - [คำอธิบายสั้นๆ]

[คำอธิบายยาว 2-3 บรรทัด]

Example:
    >>> from module import Class
    >>> instance = Class()
    >>> result = instance.method()
"""
```

**Class Docstring:**

```python
class YourClass:
    """
    [ชื่อ Class] - [คำอธิบายสั้นๆ]

    [คำอธิบายยาว]

    Attributes:
        attribute1 (type): [คำอธิบาย attribute]
        attribute2 (type): [คำอธิบาย attribute]

    Example:
        >>> obj = YourClass(param1, param2)
        >>> result = obj.method()
    """
```

**Method Docstring:**

```python
def your_method(self, param1: str, param2: int = 0) -> Tuple[bool, Any]:
    """
    [คำอธิบายสั้นๆ]

    [คำอธิบายยาว - อธิบายวิธีการทำงาน]

    Args:
        param1 (str): [คำอธิบาย parameter]
        param2 (int, optional): [คำอธิบาย parameter]. Defaults to 0.

    Returns:
        Tuple[bool, Any]: (success, result_or_error)
            - If success: (True, result_data)
            - If failed: (False, error_message)

    Raises:
        ValueError: If param1 is empty
        FileNotFoundError: If file not found

    Example:
        >>> success, result = obj.your_method("test", 10)
        >>> if success:
        >>>     print(result)
    """
```

### 6.3 Type Hints

**Always use type hints:**

```python
from typing import Any, Dict, List, Optional, Tuple, Callable, Union

# Function parameters and return types
def load_config(file_path: str) -> Dict[str, Any]:
    pass

# Optional parameters
def process_data(data: list, options: Optional[Dict] = None) -> bool:
    pass

# Multiple return types
def get_result() -> Union[str, int]:
    pass

# Tuple return
def parse_file(path: str) -> Tuple[bool, Optional[pd.DataFrame]]:
    pass

# Callable
def register_callback(callback: Callable[[str], None]) -> None:
    pass

# Complex types
def process_settings(
    column_settings: Dict[str, List[str]],
    dtype_settings: Dict[str, Dict[str, str]]
) -> Tuple[bool, str]:
    pass
```

### 6.4 Import Organization

**Always organize imports in this order:**

```python
# 1. Standard library imports (alphabetical)
import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 2. Third-party imports (alphabetical)
import customtkinter as ctk
import pandas as pd
from tkinter import messagebox, filedialog

# 3. Local imports (grouped by category)
# Config imports
from config.json_manager import load_column_settings, get_input_folder
from config.database import DatabaseConfig

# Service imports
from services.orchestrators.file_orchestrator import FileOrchestrator
from services.orchestrators.database_orchestrator import DatabaseOrchestrator

# UI imports
from ui.components.file_list import FileList
from ui.components.progress_bar import ProgressBar

# Utility imports
from utils.logger import setup_logging
from constants import AppConstants, DatabaseConstants
```

### 6.5 Code Comments

**Section Comments:**

```python
class YourClass:
    def __init__(self):
        # ===== Configuration =====
        self.config = self._load_config()

        # ===== Services =====
        self.service_a = ServiceA()
        self.service_b = ServiceB()

        # ===== UI State =====
        self.is_processing = False
        self.selected_files = []
```

**Inline Comments:**

```python
# ดีใช้เมื่อ:
# 1. อธิบาย logic ที่ซับซ้อน
# 2. อธิบายเหตุผลของการตัดสินใจ
# 3. ทำ TODO/FIXME/NOTE

# Calculate adjusted score (using weighted average)
adjusted_score = (score * 0.7) + (bonus * 0.3)

# ปิด Settings tab ระหว่างอัปโหลด เพื่อป้องกันการเปลี่ยนแปลงการตั้งค่า
if hasattr(self, 'parent_tabview'):
    self.parent_tabview.configure(state="disabled")

# TODO: Add validation for edge cases
# FIXME: This might fail with large files
# NOTE: This is a temporary workaround
```

**ไม่ควรใช้ comments เมื่อ:**

```python
# ❌ Bad: อธิบายสิ่งที่โค้ดทำอยู่แล้ว
# Set x to 10
x = 10

# ❌ Bad: ใช้ comment แทนการตั้งชื่อที่ดี
# Calculate total
t = a + b + c

# ✅ Good: ใช้ชื่อที่อธิบายตัวเอง
total_price = base_price + tax + shipping
```

### 6.6 Code Formatting

**Line Length:**
- Maximum 100 characters per line
- Break long lines logically

```python
# ❌ Too long
result = very_long_function_name(parameter1, parameter2, parameter3, parameter4, parameter5, parameter6)

# ✅ Break into multiple lines
result = very_long_function_name(
    parameter1,
    parameter2,
    parameter3,
    parameter4,
    parameter5,
    parameter6
)

# ✅ Alternative: Break after operator
result = (
    very_long_expression_part1 +
    very_long_expression_part2 +
    very_long_expression_part3
)
```

**Whitespace:**

```python
# ✅ Good spacing
def function(param1, param2):
    result = param1 + param2
    return result

x = 1 + 2
y = [1, 2, 3]
z = {'key': 'value'}

# ❌ Bad spacing
def function(param1,param2):
    result=param1+param2
    return result

x=1+2
y=[1,2,3]
z={'key':'value'}
```

**Blank Lines:**

```python
class MyClass:
    # 2 blank lines after imports

    def method1(self):
        pass

    # 1 blank line between methods
    def method2(self):
        pass

    # 2 blank lines before new section


    def method3(self):
        pass
```

---

## 7. Testing Patterns

### 7.1 Unit Testing

**Test File Structure:**

```
tests/
├── __init__.py
├── test_config/
│   └── test_json_manager.py
├── test_services/
│   ├── test_file_orchestrator.py
│   └── test_database_orchestrator.py
└── test_ui/
    └── test_handlers.py
```

**Test Template:**

```python
# tests/test_services/test_your_service.py
import unittest
from unittest.mock import Mock, patch, MagicMock
from services.your_service import YourService

class TestYourService(unittest.TestCase):
    """Test cases for YourService"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        self.mock_log = Mock()
        self.service = YourService(log_callback=self.mock_log)

    def tearDown(self):
        """Clean up after each test method"""
        pass

    def test_method_success(self):
        """Test method with valid input"""
        # Arrange
        input_data = "test_data"
        expected_result = "processed_data"

        # Act
        success, result = self.service.your_method(input_data)

        # Assert
        self.assertTrue(success)
        self.assertEqual(result, expected_result)
        self.mock_log.assert_called()

    def test_method_failure(self):
        """Test method with invalid input"""
        # Arrange
        input_data = None

        # Act
        success, result = self.service.your_method(input_data)

        # Assert
        self.assertFalse(success)
        self.assertIn("error", result.lower())

    @patch('services.your_service.external_dependency')
    def test_method_with_mock(self, mock_dependency):
        """Test method with mocked dependency"""
        # Arrange
        mock_dependency.return_value = "mocked_value"

        # Act
        success, result = self.service.method_using_dependency()

        # Assert
        self.assertTrue(success)
        mock_dependency.assert_called_once()

if __name__ == '__main__':
    unittest.main()
```

**Running Tests:**

```bash
# Run all tests
python -m unittest discover tests

# Run specific test file
python -m unittest tests.test_services.test_your_service

# Run with coverage
pip install coverage
coverage run -m unittest discover tests
coverage report
coverage html  # Generate HTML report
```

### 7.2 Integration Testing

```python
# tests/integration/test_file_to_database.py
import unittest
from services.orchestrators.file_orchestrator import FileOrchestrator
from services.orchestrators.database_orchestrator import DatabaseOrchestrator

class TestFileToDatabase(unittest.TestCase):
    """Integration tests for file to database pipeline"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        cls.file_service = FileOrchestrator()
        cls.db_service = DatabaseOrchestrator()

    def test_full_pipeline(self):
        """Test complete pipeline from file to database"""
        # Arrange
        test_file = "tests/data/test_file.xlsx"
        logic_type = "test_data"

        # Act - Read file
        success, df = self.file_service.read_excel_file(test_file, logic_type)
        self.assertTrue(success)

        # Act - Upload to database
        required_cols = self.file_service.get_required_dtypes(logic_type)
        success, message = self.db_service.upload_data(
            df, logic_type, required_cols
        )

        # Assert
        self.assertTrue(success)
```

### 7.3 Manual Testing Checklist

**สำหรับ Features ใหม่:**

- [ ] ทดสอบ happy path (กรณีที่ทำงานสำเร็จ)
- [ ] ทดสอบ error cases (กรณีที่มี error)
- [ ] ทดสอบ edge cases (กรณีขอบเขต)
- [ ] ทดสอบกับข้อมูลจริง
- [ ] ทดสอบ performance (ถ้าเกี่ยวข้อง)
- [ ] ทดสอบ UI responsiveness (ถ้าเกี่ยวข้อง)
- [ ] ตรวจสอบ log messages
- [ ] ตรวจสอบ error messages ที่แสดงผู้ใช้

**สำหรับ Bug Fixes:**

- [ ] Reproduce bug ได้
- [ ] เข้าใจสาเหตุของ bug
- [ ] Fix แล้วทดสอบว่า bug หายไป
- [ ] ทดสอบว่าไม่ทำให้เกิด regression
- [ ] เพิ่ม test case เพื่อป้องกัน bug นี้เกิดซ้ำ

---

## 8. Checklist สำหรับการ Code Review

### 8.1 Architecture & Design

**Orchestrator & Services:**
- [ ] ใช้ Orchestrator เมื่อมี services มากกว่า 2 ตัว?
- [ ] แต่ละ Service มีหน้าที่เฉพาะทาง (Single Responsibility)?
- [ ] ใช้ Dependency Injection แทน global variables?
- [ ] มี proper abstraction และ encapsulation?

**UI:**
- [ ] Tab components มี proper callbacks?
- [ ] Reusable components ถูกสร้างเป็น separate class?
- [ ] UI logic แยกออกจาก business logic?
- [ ] ใช้ threading สำหรับ long-running operations?

### 8.2 Configuration Management

**JSONManager:**
- [ ] ✅ ใช้ JSONManager แทน manual JSON handling?
- [ ] ✅ มี validation function สำหรับ config ใหม่?
- [ ] ✅ มี convenience functions ที่เหมาะสม?
- [ ] ✅ มี default values ที่เหมาะสม?

**ตัวอย่างการตรวจสอบ:**

```python
# ❌ Bad: Manual JSON handling
import json
with open("config/my_config.json", 'r') as f:
    config = json.load(f)

# ✅ Good: Use JSONManager
from config.json_manager import get_my_config
config = get_my_config()
```

### 8.3 Error Handling

**Return Values:**
- [ ] ใช้ Tuple[bool, Any] return pattern?
- [ ] มี proper error messages?
- [ ] จับ specific exceptions ก่อน general Exception?
- [ ] มี logging ที่เหมาะสม?

**ตัวอย่าง:**

```python
# ✅ Good
def process_data(data) -> Tuple[bool, Any]:
    try:
        result = process(data)
        return True, result
    except ValueError as e:
        return False, f"Invalid data: {e}"
    except Exception as e:
        logging.exception("Unexpected error")
        return False, f"Error: {e}"
```

### 8.4 Code Style

**Naming:**
- [ ] Classes ใช้ PascalCase?
- [ ] Functions/methods ใช้ snake_case?
- [ ] Constants ใช้ UPPER_CASE?
- [ ] Private methods มี underscore prefix?

**Documentation:**
- [ ] มี module docstring?
- [ ] มี class docstring?
- [ ] มี method docstrings พร้อม type hints?
- [ ] Comments อธิบาย "why" ไม่ใช่ "what"?

**Imports:**
- [ ] Imports จัดเรียงตาม standard > third-party > local?
- [ ] ไม่มี unused imports?
- [ ] ไม่มี wildcard imports (`from x import *`)?

### 8.5 Performance

**ประสิทธิภาพ:**
- [ ] ใช้ parallel processing เมื่อเหมาะสม?
- [ ] ใช้ chunked processing สำหรับไฟล์ใหญ่?
- [ ] มี caching เมื่อเหมาะสม?
- [ ] ไม่มี unnecessary computations ใน loops?

**ตัวอย่าง:**

```python
# ❌ Bad: Load config in loop
for item in items:
    config = load_config()  # ❌ Load every iteration
    process(item, config)

# ✅ Good: Load config once
config = load_config()
for item in items:
    process(item, config)
```

### 8.6 Testing

**Test Coverage:**
- [ ] มี unit tests สำหรับ core logic?
- [ ] มี integration tests สำหรับ critical paths?
- [ ] Tests ครอบคลุม error cases?
- [ ] Tests มีชื่อที่อธิบายตัวเอง?

### 8.7 Logging

**Log Quality:**
- [ ] ใช้ emoji-based logging?
- [ ] Log messages มีความหมายชัดเจน?
- [ ] Log level เหมาะสม (INFO/WARNING/ERROR)?
- [ ] ไม่ log sensitive data (passwords, keys)?

**ตัวอย่าง:**

```python
# ✅ Good logging
self.log("✅ File processed successfully")
self.log("❌ Failed to connect to database")
self.log("⚠️ File size exceeds recommended limit")
self.log("📊 Processing 1000 rows")
```

### 8.8 Security

**Security Checklist:**
- [ ] ไม่มี hardcoded passwords/keys?
- [ ] ใช้ environment variables สำหรับ sensitive data?
- [ ] Validate user input?
- [ ] ใช้ parameterized queries (ป้องกัน SQL injection)?

---

## 9. Quick Reference

### 9.1 สร้าง Orchestrator ใหม่

```python
# services/orchestrators/your_orchestrator.py
class YourOrchestrator:
    def __init__(self, log_callback=None):
        self.log = log_callback or logging.info
        self.service_a = ServiceA(self.log)
        self.service_b = ServiceB(self.log)

    def main_operation(self, param):
        try:
            result_a = self.service_a.do_something(param)
            result_b = self.service_b.process(result_a)
            return True, result_b
        except Exception as e:
            return False, str(e)
```

### 9.2 สร้าง Service ใหม่

```python
# services/category/your_service.py
class YourService:
    def __init__(self, log_callback=None):
        self.log = log_callback or logging.info

    def process(self, data) -> Tuple[bool, Any]:
        try:
            result = self._internal_process(data)
            return True, result
        except Exception as e:
            return False, str(e)
```

### 9.3 เพิ่ม Configuration

```python
# 1. In json_manager.py - _initialize_file_configs()
'your_config': JSONFileConfig(
    filename='your_config.json',
    default_content={"key": "value"},
    validation_func=self._validate_your_config
),

# 2. Add validation
def _validate_your_config(self, content):
    return isinstance(content, dict) and 'key' in content

# 3. Add convenience functions
def get_your_setting() -> str:
    return json_manager.get('your_config', 'key', '')

def set_your_setting(value: str) -> bool:
    return json_manager.set('your_config', 'key', value)
```

### 9.4 สร้าง UI Tab

```python
# ui/tabs/your_tab.py
class YourTab:
    def __init__(self, parent, callbacks):
        self.parent = parent
        self.callbacks = callbacks
        self._create_ui()

    def _create_ui(self):
        # Create UI elements
        pass

    def _handle_button_click(self):
        if 'on_button_click' in self.callbacks:
            self.callbacks['on_button_click']()
```

### 9.5 สร้าง UI Component

```python
# ui/components/your_component.py
class YourComponent(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._create_ui()

    def _create_ui(self):
        # Create internal UI
        pass

    def set_data(self, data):
        # Public API
        pass
```

---

## 10. ทรัพยากรเพิ่มเติม

### 10.1 เอกสารที่เกี่ยวข้อง

- **README.md** - Overview และ setup instructions
- **constants.py** - Application constants
- **config/json_manager.py** - Configuration management
- **services/orchestrators/** - Orchestrator patterns
- **ui/components/** - Reusable UI components

### 10.2 Design Patterns References

- **Orchestrator Pattern** - Coordinates multiple services
- **Service Layer Pattern** - Encapsulates business logic
- **Handler Pattern** - Separates UI logic from components
- **Facade Pattern** - Simplifies complex subsystems (JSONManager)
- **Observer Pattern** - Callback system for UI updates
- **Pipeline Pattern** - Sequential data processing

### 10.3 Python Best Practices

- [PEP 8](https://peps.python.org/pep-0008/) - Style Guide
- [PEP 257](https://peps.python.org/pep-0257/) - Docstring Conventions
- [PEP 484](https://peps.python.org/pep-0484/) - Type Hints

### 10.4 ติดต่อทีม

เมื่อมีคำถามหรือต้องการความช่วยเหลือ:
1. ตรวจสอบเอกสารนี้ก่อน
2. อ่าน code ที่มีอยู่ในโปรเจกต์
3. สอบถามทีมผ่าน communication channels

---

## สรุป

เอกสารนี้รวบรวม patterns และ best practices ที่ใช้ในโปรเจกต์ PIPELINE_SQLSERVER:

✅ **Architecture:** Layered, Orchestrator, Service Layer, Handler
✅ **Configuration:** JSONManager centralized management
✅ **UI:** Tab components, Reusable components, Callbacks
✅ **Data Flow:** Pipeline, Error handling, Logging
✅ **Code Style:** Naming, Docstrings, Type hints, Imports
✅ **Testing:** Unit tests, Integration tests, Manual testing

**หลักการสำคัญ:**
- **Consistency** - ทุกส่วนใช้ pattern เดียวกัน
- **Separation of Concerns** - แยกหน้าที่ชัดเจน
- **DRY** - Don't Repeat Yourself
- **SOLID** - หลักการออกแบบที่ดี
- **Testability** - เขียนโค้ดที่ test ได้

เมื่อเขียนโค้ดใหม่หรืออัปเดท **ให้ทำตาม patterns ในเอกสารนี้** เพื่อความสอดคล้องและคุณภาพของโค้ด

---

**เอกสารนี้จะถูกอัปเดตเมื่อมี patterns ใหม่เพิ่มเข้ามา**

_Last Updated: 2025-01-XX_
