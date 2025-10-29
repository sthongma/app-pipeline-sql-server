# 🏗️ การสร้าง Installer สำหรับ SQL Server Pipeline

คู่มือนี้อธิบายวิธีสร้าง Windows Installer แบบมืออาชีพสำหรับโปรแกรม SQL Server Pipeline

---

## 📋 สิ่งที่ต้องเตรียม

### 1. Python และ Dependencies
```bash
python --version    # ต้องเป็น 3.8 ขึ้นไป
pip install -r requirements-lock.txt
pip install pyinstaller
```

### 2. Inno Setup (สำหรับสร้าง Installer)
- ดาวน์โหลดจาก: https://jrsoftware.org/isdl.php
- เวอร์ชันแนะนำ: Inno Setup 6.2.1 หรือใหม่กว่า
- ติดตั้งแบบ Default (ไม่ต้องเปลี่ยนอะไร)

### 3. Icon File (ถ้ามี)
```
assets/
└── icon.ico    # ไฟล์ icon ขนาด 256x256 หรือ 512x512
```

---

## 🚀 วิธีสร้าง Installer (แบบอัตโนมัติ)

### วิธีที่ 1: ใช้ Build Script (ง่ายที่สุด)

```bash
# 1. เปิด Command Prompt หรือ PowerShell
cd build

# 2. รัน build script
build_installer.bat

# 3. รอให้เสร็จ (ประมาณ 3-5 นาที)
```

**ผลลัพธ์ที่ได้:**
```
dist/
├── SQLServerPipeline/                          # เวอร์ชัน Portable
│   ├── SQLServerPipeline.exe                   # ไฟล์หลัก
│   ├── _internal/                              # Libraries
│   ├── .env.example                            # ตัวอย่าง config
│   └── ... (ไฟล์อื่นๆ)
│
└── installer/
    └── SQLServerPipeline_v2.2.0_Setup.exe      # Windows Installer ✅
```

---

## 🔧 วิธีสร้างแบบทีละขั้นตอน (Manual)

### ขั้นตอนที่ 1: สร้าง Executable ด้วย PyInstaller

```bash
# จากโฟลเดอร์หลักของโปรเจกต์
cd /path/to/app-pipeline-sql-server

# Build ด้วย spec file
pyinstaller --clean build/pipeline_gui_app.spec
```

**ผลลัพธ์:**
- ไฟล์ .exe จะอยู่ใน `dist/SQLServerPipeline/`
- ขนาดประมาณ 150-200 MB (รวม dependencies)

### ขั้นตอนที่ 2: คัดลอกไฟล์เพิ่มเติม

```bash
# คัดลอก documentation
copy README.md dist\SQLServerPipeline\
copy SECURITY.md dist\SQLServerPipeline\
copy PERFORMANCE.md dist\SQLServerPipeline\
copy .env.example dist\SQLServerPipeline\

# คัดลอก monitoring tools (optional)
xcopy /e /i monitoring dist\SQLServerPipeline\monitoring\

# สร้างโฟลเดอร์ที่จำเป็น
mkdir dist\SQLServerPipeline\logs
mkdir dist\SQLServerPipeline\Uploaded_Files
mkdir dist\SQLServerPipeline\config
```

### ขั้นตอนที่ 3: สร้าง Installer ด้วย Inno Setup

```bash
# รัน Inno Setup compiler
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\installer.iss
```

**ผลลัพธ์:**
- Installer จะอยู่ใน `dist/installer/`
- ชื่อไฟล์: `SQLServerPipeline_v2.2.0_Setup.exe`
- ขนาดประมาณ 60-80 MB (บีบอัดแล้ว)

---

## 📦 ผลลัพธ์ที่ได้ (2 แบบ)

### แบบที่ 1: Portable Version
```
dist/SQLServerPipeline/
├── SQLServerPipeline.exe      # รันได้เลย ไม่ต้องติดตั้ง
├── _internal/                 # Dependencies
├── .env.example
├── README.md
├── logs/
├── Uploaded_Files/
└── monitoring/
```

**วิธีใช้:**
1. Zip โฟลเดอร์ทั้งหมด
2. แจกจ่ายให้ผู้ใช้
3. ผู้ใช้แตก zip และดับเบิลคลิก `.exe`

**ข้อดี:**
- ✅ ไม่ต้องติดตั้ง
- ✅ พกพาได้ (USB drive)
- ✅ ไม่มีผลต่อระบบ

**ข้อเสีย:**
- ❌ ไม่มีใน Programs and Features
- ❌ ไม่มี Start Menu shortcut
- ❌ ต้องแตก zip เอง

---

### แบบที่ 2: Installer Version (แนะนำ) ⭐

```
dist/installer/
└── SQLServerPipeline_v2.2.0_Setup.exe    # Windows Installer
```

**วิธีใช้:**
1. แจกจ่ายไฟล์ `.exe` เดียว
2. ผู้ใช้ดับเบิลคลิก
3. ติดตั้งแบบมาตรฐาน Windows

**ข้อดี:**
- ✅ ติดตั้งอัตโนมัติ
- ✅ มี Start Menu shortcuts
- ✅ มีใน Programs and Features
- ✅ ถอนการติดตั้งได้ง่าย
- ✅ สร้าง Desktop icon
- ✅ ตั้งค่า permissions อัตโนมัติ

**ข้อเสีย:**
- ❌ ต้องมีสิทธิ์ Admin ในการติดตั้ง

---

## 🎯 ฟีเจอร์ของ Installer

### การติดตั้ง
- ✅ ติดตั้งไปที่ `C:\Program Files\SQL Server Pipeline\`
- ✅ สร้างโฟลเดอร์ logs, Uploaded_Files อัตโนมัติ
- ✅ คัดลอก `.env.example` → `.env`
- ✅ ตั้งค่า file permissions

### Shortcuts ที่สร้าง
**Start Menu:**
- SQL Server Pipeline (โปรแกรมหลัก)
- คู่มือการใช้งาน (README.md)
- ตั้งค่าฐานข้อมูล (เปิด .env ใน Notepad)
- โฟลเดอร์โปรแกรม
- Uninstall

**Desktop:**
- SQL Server Pipeline (ถ้าเลือก)

### หลังติดตั้งเสร็จ
- เปิด README.md อัตโนมัติ
- เสนอให้ตั้งค่า .env
- เสนอให้เปิดโปรแกรม

### การถอนการติดตั้ง
- ลบไฟล์โปรแกรม
- **เก็บ** config และ logs ไว้ (ปลอดภัย)
- ลบ shortcuts
- ลบ registry entries

---

## 🔍 การทดสอบ

### ทดสอบ Portable Version
```bash
# 1. ไปที่โฟลเดอร์
cd dist\SQLServerPipeline

# 2. รันโปรแกรม
SQLServerPipeline.exe

# 3. ทดสอบฟีเจอร์หลัก
- เชื่อมต่อฐานข้อมูล
- Upload ไฟล์ทดสอบ
- ดู logs
- ตรวจสอบ error handling
```

### ทดสอบ Installer Version
```bash
# 1. รัน installer
dist\installer\SQLServerPipeline_v2.2.0_Setup.exe

# 2. ติดตั้งแบบ Default

# 3. ตรวจสอบ
- Start Menu มี shortcuts ครบ
- Desktop มี icon (ถ้าเลือก)
- โปรแกรมรันได้
- Config ครบถ้วน

# 4. ทดสอบ Uninstall
- Control Panel → Programs and Features
- Uninstall SQL Server Pipeline
- ตรวจสอบว่าลบสะอาด
```

---

## 🐛 แก้ปัญหาที่พบบ่อย

### 1. PyInstaller build ล้มเหลว

**อาการ:**
```
ModuleNotFoundError: No module named 'xxx'
```

**แก้ไข:**
```bash
# ติดตั้ง dependencies ใหม่
pip install -r requirements-lock.txt

# หรือเพิ่ม hidden import ใน spec file
hiddenimports = ['module_name']
```

### 2. .exe ไม่ทำงาน (ดับเบิลคลิกแล้วไม่เกิดอะไร)

**แก้ไข:**
```bash
# รันผ่าน command line เพื่อดู error
cd dist\SQLServerPipeline
SQLServerPipeline.exe
```

### 3. ไม่พบ customtkinter theme

**แก้ไข:**
ตรวจสอบว่า `collect_data_files('customtkinter')` อยู่ใน spec file

### 4. Inno Setup ไม่พบ

**แก้ไข:**
```bash
# ติดตั้ง Inno Setup จาก
https://jrsoftware.org/isdl.php

# หรือแก้ไข path ใน build_installer.bat
set INNO_PATH=C:\Path\To\ISCC.exe
```

### 5. Antivirus block .exe

**อาการ:**
Windows Defender หรือ Antivirus อื่นๆ block ไฟล์

**แก้ไข:**
```bash
# 1. Add exclusion ใน Windows Defender
# 2. Sign code ด้วย code signing certificate
# 3. ส่ง .exe ให้ Microsoft ตรวจสอบ
```

---

## 📝 Customization

### แก้ไข Icon
```bash
# วาง icon ไว้ที่
assets/icon.ico

# Icon ต้องเป็น .ico format
# ขนาดแนะนำ: 256x256 หรือ 512x512
# มีหลาย resolution: 16x16, 32x32, 48x48, 256x256
```

### แก้ไขข้อมูล App
แก้ไขใน `build/installer.iss`:
```ini
#define MyAppName "SQL Server Pipeline"
#define MyAppVersion "2.2.0"
#define MyAppPublisher "Your Organization"
#define MyAppURL "https://github.com/..."
```

### เพิ่มไฟล์เข้า Installer
แก้ไขใน `build/installer.iss`:
```ini
[Files]
Source: "path\to\your\file"; DestDir: "{app}"; Flags: ignoreversion
```

---

## 📊 ขนาดไฟล์โดยประมาณ

| Item | Size |
|------|------|
| PyInstaller Output (uncompressed) | ~150 MB |
| Portable Version (zipped) | ~80 MB |
| Installer .exe | ~70 MB |
| Installed Size | ~150 MB |

---

## 🚀 Automation และ CI/CD

### GitHub Actions (อนาคต)
```yaml
# .github/workflows/build-release.yml
name: Build Release
on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Installer
        run: build\build_installer.bat
      - name: Upload Release
        uses: actions/upload-artifact@v3
        with:
          name: installer
          path: dist/installer/*.exe
```

---

## 📚 เอกสารเพิ่มเติม

- **PyInstaller Manual**: https://pyinstaller.org/en/stable/
- **Inno Setup Documentation**: https://jrsoftware.org/ishelp/
- **Code Signing Guide**: https://docs.microsoft.com/en-us/windows/win32/seccrypto/using-signtool

---

## ✅ Checklist ก่อนแจกจ่าย

- [ ] ทดสอบบน Windows 10
- [ ] ทดสอบบน Windows 11
- [ ] ทดสอบบนเครื่องที่ไม่มี Python
- [ ] ทดสอบ Install/Uninstall
- [ ] ทดสอบการเชื่อมต่อฐานข้อมูล
- [ ] ทดสอบ Upload ไฟล์
- [ ] ตรวจสอบ logs
- [ ] อ่าน README.md ให้ครบ
- [ ] แก้ไข .env ให้ถูกต้อง
- [ ] ตรวจสอบ Security (SECURITY.md)
- [ ] เตรียมเอกสารสำหรับผู้ใช้

---

**สร้างโดย:** SQL Server Pipeline Team
**เวอร์ชัน:** 2.2.0
**อัพเดทล่าสุด:** 2025-10-29
