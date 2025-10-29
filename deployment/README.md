# 📦 Deployment Files

โฟลเดอร์นี้เก็บไฟล์ที่ใช้สำหรับสร้าง Windows Installer แบบมืออาชีพ

---

## 📁 ไฟล์ในโฟลเดอร์นี้

### 1. `pipeline_gui_app.spec`
- **PyInstaller specification file**
- กำหนดวิธีการ build .exe
- รวม dependencies, data files, และ configuration
- ใช้คำสั่ง: `pyinstaller pipeline_gui_app.spec`

### 2. `installer.iss`
- **Inno Setup script**
- กำหนด installer wizard, shortcuts, และ registry
- สร้าง professional Windows installer
- ใช้คำสั่ง: `iscc installer.iss`

### 3. `build_installer.bat`
- **Automated build script**
- รัน PyInstaller และ Inno Setup อัตโนมัติ
- ตรวจสอบ dependencies
- สร้าง installer ครบวงจรในคำสั่งเดียว

### 4. `README_BUILD.md`
- **เอกสารแบบละเอียด**
- คู่มือสร้าง installer ทีละขั้นตอน
- แก้ปัญหาที่พบบ่อย
- Customization guide

### 5. `QUICK_START.md`
- **เริ่มต้นอย่างรวดเร็ว**
- สร้าง installer ใน 3 ขั้นตอน
- เหมาะสำหรับคนที่รีบ

---

## 🚀 วิธีใช้งานอย่างรวดเร็ว

### แบบอัตโนมัติ (แนะนำ)
```bash
cd deployment
build_installer.bat
```

### แบบทีละขั้นตอน
```bash
# 1. Build executable
pyinstaller pipeline_gui_app.spec

# 2. Build installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

---

## 📦 Output

หลังจากรัน build สำเร็จ คุณจะได้:

```
dist/
├── SQLServerPipeline/                          # Portable version
│   ├── SQLServerPipeline.exe
│   └── ... (dependencies)
│
└── installer/
    └── SQLServerPipeline_v2.2.0_Setup.exe      # Windows Installer ✅
```

---

## 📋 สิ่งที่ต้องมี

- ✅ Python 3.8+
- ✅ PyInstaller (`pip install pyinstaller`)
- ✅ Inno Setup (https://jrsoftware.org/isdl.php)
- ✅ Dependencies (`pip install -r requirements-lock.txt`)

---

## 📚 เอกสารเพิ่มเติม

- **Quick Start**: อ่าน `QUICK_START.md`
- **Full Guide**: อ่าน `README_BUILD.md`
- **Inno Setup Docs**: https://jrsoftware.org/ishelp/

---

## ⚙️ Customization

### เปลี่ยน Version
แก้ไขใน `installer.iss`:
```ini
#define MyAppVersion "2.2.0"
```

### เปลี่ยน Icon
วาง icon ไว้ที่ `assets/icon.ico` แล้ว build ใหม่

### เพิ่ม Files
แก้ไขใน `pipeline_gui_app.spec` หรือ `installer.iss`

---

**พร้อมสร้าง installer แบบมืออาชีพ!** 🎉
