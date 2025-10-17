# Add-ons / เครื่องมือเสริม

โฟลเดอร์นี้เก็บเครื่องมือเสริม (add-on tools) สำหรับ PIPELINE_SQLSERVER

## โครงสร้าง

```
addons/
├── column_mapper/          # ML-enhanced column mapping tool
│   ├── column_mapper_cli.py
│   ├── services/
│   │   ├── ml_column_mapper.py
│   │   └── auto_column_rename_service.py
│   ├── run_column_mapper.bat       # Interactive mode
│   ├── run_column_auto_mapper.bat  # Auto mode
│   └── README.md
└── (future_tools)/         # เครื่องมืออื่นๆ ในอนาคต
```

## เครื่องมือที่มี

### 1. Column Mapper
เครื่องมือช่วยแมพคอลัมน์อัตโนมัติโดยใช้ ML เมื่อพบคอลัมน์ที่ไม่ตรงกับการตั้งค่า

**คุณสมบัติ:**
- ตรวจจับคอลัมน์ที่หายไป (missing columns)
- แนะนำการแมพใหม่โดยใช้ ML
- รองรับทั้งโหมด interactive และ auto
- อัพเดท column_settings.json อัตโนมัติ

**การใช้งาน:**
```bash
# Interactive mode - เลือกการแมพเอง
python addons/column_mapper/column_mapper_cli.py [folder_path]

# Auto mode - ใช้ ML แมพอัตโนมัติ
python addons/column_mapper/column_mapper_cli.py [folder_path] --auto

# หรือใช้ batch files
run_column_mapper.bat
run_column_auto_mapper.bat
```

ดู [column_mapper/README.md](column_mapper/README.md) สำหรับรายละเอียดเพิ่มเติม

## หมายเหตุสำหรับนักพัฒนา

### การเพิ่มเครื่องมือใหม่
1. สร้างโฟลเดอร์ใหม่ใน `addons/`
2. เพิ่ม `__init__.py` และ `README.md`
3. เครื่องมือสามารถเข้าถึง config ของ app หลักได้ผ่าน:
   ```python
   import sys
   from pathlib import Path
   sys.path.append(str(Path(__file__).parent.parent))
   from constants import PathConstants
   ```

### โครงสร้างที่แนะนำ
```
addons/
└── your_tool/
    ├── __init__.py
    ├── README.md
    ├── your_tool_cli.py      # Main script
    ├── services/             # Business logic
    ├── run_your_tool.bat     # Windows launcher
    └── requirements.txt      # Tool-specific deps (optional)
```
