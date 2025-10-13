# 📚 Documentation Guide

> คู่มือสำหรับเอกสารของโปรเจกต์ PIPELINE_SQLSERVER

---

## เอกสารทั้งหมด

โปรเจกต์นี้มีเอกสาร 3 ชุดหลัก:

### 1. **ENGINEERING_CONTEXT.md** 📖
**คู่มือหลักฉบับเต็ม - อ่านครั้งแรก**

เอกสารนี้อธิบายรายละเอียดครบถ้วนเกี่ยวกับ:
- ✅ Architecture Patterns ทั้งหมด
- ✅ การใช้งาน Orchestrator, Service, Handler patterns
- ✅ Configuration Management แบบ centralized
- ✅ UI Development patterns
- ✅ Data Flow & Processing
- ✅ Code Style Guidelines
- ✅ Testing Patterns
- ✅ Code Review Checklist

**เมื่อไหร่ควรอ่าน:**
- เมื่อเริ่มทำงานในโปรเจกต์ครั้งแรก
- เมื่อต้องการเข้าใจ architecture ของระบบ
- เมื่อต้องการทำความเข้าใจ design patterns ที่ใช้
- เมื่อต้องการแนวทางในการเขียนโค้ดให้ถูกต้อง

**ขนาด:** ~300+ บรรทัด (อ่านประมาณ 20-30 นาที)

---

### 2. **PATTERNS_QUICK_GUIDE.md** 🚀
**คู่มือสรุปแบบย่อ - อ้างอิงเร็ว**

เอกสารนี้เป็น quick reference ที่มี:
- ✅ เมื่อไหร่ใช้ pattern ไหน (decision tree)
- ✅ Code templates สำหรับ copy-paste
- ✅ Configuration quick reference
- ✅ Common mistakes และวิธีแก้
- ✅ Checklists สำหรับแต่ละ task
- ✅ Emoji reference
- ✅ Import templates

**เมื่อไหร่ควรใช้:**
- เมื่อกำลังเขียนโค้ดและต้องการ template
- เมื่อต้องการ check ว่าทำถูกหรือไม่
- เมื่อลืม syntax หรือรูปแบบ
- เมื่อต้องการ quick lookup

**ขนาด:** ~150+ บรรทัด (scan ได้ภายใน 5 นาที)

---

### 3. **README.md** 📝
**คู่มือการติดตั้งและใช้งาน**

เอกสารนี้อธิบาย:
- ✅ ภาพรวมโปรเจกต์
- ✅ การติดตั้งและ setup
- ✅ วิธีใช้งาน GUI และ CLI
- ✅ Configuration setup
- ✅ Troubleshooting

**เมื่อไหร่ควนอ่าน:**
- เมื่อติดตั้งโปรเจกต์ครั้งแรก
- เมื่อต้องการรู้วิธีใช้งาน
- เมื่อเจอปัญหาในการใช้งาน

---

## Workflow สำหรับ Engineers

### เมื่อเริ่มทำงานในโปรเจกต์ครั้งแรก

```
1. อ่าน README.md
   └─> ติดตั้งและ setup environment

2. อ่าน ENGINEERING_CONTEXT.md (ทั้งหมด)
   └─> เข้าใจ architecture และ patterns

3. Bookmark PATTERNS_QUICK_GUIDE.md
   └─> ใช้อ้างอิงขณะเขียนโค้ด
```

### เมื่อต้องการเขียน Feature ใหม่

```
1. เปิด PATTERNS_QUICK_GUIDE.md
   └─> ดูว่าควรใช้ pattern ไหน

2. Copy template ที่เหมาะสม
   └─> แก้ไขตามความต้องการ

3. ตรวจสอบ checklist
   └─> ก่อน commit code
```

### เมื่อต้องการ Review Code

```
1. เปิด ENGINEERING_CONTEXT.md
   └─> ดู "8. Checklist สำหรับการ Code Review"

2. ตรวจสอบ code ตาม checklist
   └─> ทีละข้อ

3. อ้างอิง PATTERNS_QUICK_GUIDE.md
   └─> ดู "4. Common Mistakes" เพื่อหา anti-patterns
```

### เมื่อลืม Syntax หรือ Convention

```
1. เปิด PATTERNS_QUICK_GUIDE.md
   └─> ค้นหาหัวข้อที่ต้องการ

2. ถ้าต้องการรายละเอียดเพิ่ม
   └─> ดูใน ENGINEERING_CONTEXT.md
```

---

## โครงสร้างของเอกสาร

### ENGINEERING_CONTEXT.md

```
1. ภาพรวมโครงสร้างโปรเจกต์
   ├─ 1.1 Layered Architecture
   └─ 1.2 โครงสร้างไดเรกทอรี

2. Architecture Patterns
   ├─ 2.1 Orchestrator Pattern ⭐
   ├─ 2.2 Service Layer Pattern
   ├─ 2.3 Handler Pattern
   └─ 2.4 Other Patterns

3. Configuration Management
   ├─ 3.1 JSONManager ⭐
   ├─ 3.2 การเพิ่ม Configuration ใหม่
   └─ 3.3 Best Practices

4. UI Development Patterns
   ├─ 4.1 Tab Component Pattern
   ├─ 4.2 Reusable Component Pattern
   ├─ 4.3 Callback Pattern
   └─ 4.4 Async UI Building

5. Data Flow & Processing
   ├─ 5.1 Pipeline Pattern
   ├─ 5.2 Error Handling Pattern
   ├─ 5.3 Logging Pattern
   └─ 5.4 Performance Patterns

6. Code Style Guidelines
   ├─ 6.1 Naming Conventions
   ├─ 6.2 Docstrings
   ├─ 6.3 Type Hints
   ├─ 6.4 Import Organization
   ├─ 6.5 Code Comments
   └─ 6.6 Code Formatting

7. Testing Patterns
   ├─ 7.1 Unit Testing
   ├─ 7.2 Integration Testing
   └─ 7.3 Manual Testing Checklist

8. Checklist สำหรับการ Code Review
   └─ แยกตาม category

9. Quick Reference
   └─ Code snippets สำหรับงานทั่วไป

10. ทรัพยากรเพิ่มเติม
```

### PATTERNS_QUICK_GUIDE.md

```
1. เมื่อไหร่ใช้ Pattern ไหน
   └─ Decision guide

2. Code Templates
   ├─ Orchestrator Template
   ├─ Service Template
   ├─ Handler Template
   ├─ Tab Component Template
   └─ UI Component Template

3. Configuration Quick Ref
   ├─ การเพิ่ม Config ใหม่ (step by step)
   └─ Configs ที่มีอยู่ (table)

4. Common Mistakes
   └─ ❌ Bad vs ✅ Good examples

5. Checklists
   ├─ สร้าง Orchestrator
   ├─ สร้าง Service
   ├─ สร้าง Handler
   ├─ สร้าง Tab
   ├─ สร้าง Component
   ├─ เพิ่ม Configuration
   └─ Code Review

6. Emoji Reference
   └─ Table with usage examples

7. File Structure Quick Ref

8. Import Templates

9. Naming Quick Ref

10. Contact & Help
```

---

## Tips สำหรับการใช้เอกสาร

### 🔍 การค้นหาข้อมูล

**ใน VSCode:**
- กด `Ctrl+F` (Windows) หรือ `Cmd+F` (Mac) เพื่อค้นหาในไฟล์
- ใช้ outline/breadcrumbs เพื่อดูโครงสร้างเอกสาร

**สิ่งที่ควรค้นหา:**
- `⭐` - หัวข้อสำคัญที่ต้องรู้
- `✅ Good` - ตัวอย่างที่ถูกต้อง
- `❌ Bad` - สิ่งที่ไม่ควรทำ
- `TODO` - สิ่งที่ต้องทำต่อ
- Class/Function names - เพื่อดูวิธีใช้งาน

### 📑 Bookmarks ที่แนะนำ

ใน VSCode, bookmark หัวข้อเหล่านี้:

**ENGINEERING_CONTEXT.md:**
- "2.1 Orchestrator Pattern" - เมื่อต้องสร้าง orchestrator
- "3.1 JSONManager" - เมื่อต้องการใช้ config
- "5.2 Error Handling Pattern" - เมื่อต้องการ error handling
- "8. Checklist สำหรับการ Code Review" - เมื่อ review code

**PATTERNS_QUICK_GUIDE.md:**
- "1. เมื่อไหร่ใช้ Pattern ไหน" - decision guide
- "2. Code Templates" - copy templates
- "4. Common Mistakes" - เช็คว่าทำผิดไหม
- "5. Checklists" - ตรวจสอบงาน

### 💡 Best Practices

**อ่านเอกสารอย่างมีประสิทธิภาพ:**

1. **First Time:**
   - อ่าน ENGINEERING_CONTEXT.md ทั้งหมดแบบคร่าว ๆ
   - จด notes สิ่งสำคัญ
   - ลอง run ตัวอย่าง code

2. **Daily Usage:**
   - เปิด PATTERNS_QUICK_GUIDE.md ขณะเขียนโค้ด
   - ใช้ templates แทนเขียนใหม่
   - ตรวจสอบ checklist ก่อน commit

3. **Code Review:**
   - ใช้ checklist จาก ENGINEERING_CONTEXT.md
   - อ้างอิง "Common Mistakes" เพื่อหา anti-patterns

4. **Learning:**
   - อ่านเอกสารทีละส่วน
   - ลองเขียน code ตามตัวอย่าง
   - สอบถามทีมเมื่อสงสัย

---

## การอัปเดตเอกสาร

### เมื่อมี Pattern ใหม่

1. อัปเดต **ENGINEERING_CONTEXT.md**:
   - เพิ่ม section ใหม่พร้อมคำอธิบายละเอียด
   - ใส่ตัวอย่างโค้ดที่ชัดเจน
   - อัปเดต checklist ที่เกี่ยวข้อง

2. อัปเดต **PATTERNS_QUICK_GUIDE.md**:
   - เพิ่มใน "เมื่อไหร่ใช้ Pattern ไหน"
   - เพิ่ม template ใหม่
   - เพิ่มใน checklist

3. อัปเดต **DOCS_README.md** (ไฟล์นี้):
   - อัปเดต "สารบัญ" ถ้าจำเป็น

### Version Control

เมื่ออัปเดตเอกสาร:
- แก้ไข "Last Updated" date ท้ายไฟล์
- Commit พร้อม message ที่ชัดเจน: `docs: add pattern for [feature]`
- Review จากทีมก่อน merge

---

## FAQs

### Q: เอกสารไหนควรอ่านก่อน?
**A:** อ่าน README.md → ENGINEERING_CONTEXT.md → bookmark PATTERNS_QUICK_GUIDE.md

### Q: ลืม pattern ที่ต้องใช้ จะทำยังไง?
**A:** เปิด PATTERNS_QUICK_GUIDE.md → ดู "1. เมื่อไหร่ใช้ Pattern ไหน"

### Q: ต้องการ template สำหรับเขียนโค้ด
**A:** ดูใน PATTERNS_QUICK_GUIDE.md → "2. Code Templates"

### Q: ต้องการเช็คว่าโค้ดที่เขียนถูกต้องไหม?
**A:** ดู checklist ใน PATTERNS_QUICK_GUIDE.md → "5. Checklists"

### Q: ต้องการทำความเข้าใจ pattern แบบละเอียด
**A:** อ่านใน ENGINEERING_CONTEXT.md → หาหัวข้อที่ต้องการ

### Q: กำลัง review code ของคนอื่น
**A:** ใช้ ENGINEERING_CONTEXT.md → "8. Checklist สำหรับการ Code Review"

### Q: เจอโค้ดที่ดูแปลก ๆ ไม่แน่ใจว่าถูกหรือผิด
**A:** ดู PATTERNS_QUICK_GUIDE.md → "4. Common Mistakes"

### Q: ต้องการเพิ่ม configuration ใหม่
**A:** ดู PATTERNS_QUICK_GUIDE.md → "3. Configuration Quick Ref"

---

## Feedback & Contributions

### รายงานปัญหา

ถ้าเจอปัญหาในเอกสาร:
1. ตรวจสอบว่าอ่านถูกหัวข้อหรือไม่
2. ค้นหาข้อมูลเพิ่มเติมในเอกสารอื่น
3. สอบถามทีม
4. แจ้งปัญหาผ่าน communication channels

### แนะนำการปรับปรุง

ถ้ามีข้อเสนอแนะ:
- Pattern ใหม่ที่ควรเพิ่ม
- ตัวอย่างที่ควรมี
- ส่วนที่อธิบายไม่ชัดเจน
- การจัดเรียงที่ควรปรับปรุง

กรุณาแจ้งทีมเพื่อพิจารณาอัปเดต

---

## Summary

### เอกสารทั้ง 3 ชุด มีจุดประสงค์ต่างกัน:

| เอกสาร | จุดประสงค์ | เมื่อไหร่ใช้ | ขนาด |
|--------|-----------|-------------|------|
| **README.md** | Setup & การใช้งาน | ติดตั้งครั้งแรก | ~100 บรรทัด |
| **ENGINEERING_CONTEXT.md** | ความเข้าใจเชิงลึก | เรียนรู้ครั้งแรก, อ้างอิงละเอียด | ~300+ บรรทัด |
| **PATTERNS_QUICK_GUIDE.md** | อ้างอิงเร็ว | ขณะเขียนโค้ด, quick lookup | ~150 บรรทัด |

### หลักการใช้งาน:

1. **อ่าน** ENGINEERING_CONTEXT.md ทั้งหมดก่อนเริ่มทำงาน
2. **Bookmark** PATTERNS_QUICK_GUIDE.md สำหรับอ้างอิงขณะเขียนโค้ด
3. **ตรวจสอบ** checklists ก่อน commit code
4. **อัปเดต** เอกสารเมื่อมี patterns ใหม่

---

**Happy Coding! 🚀**

ถ้ามีคำถามหรือข้อสงสัย อย่าลังเลที่จะถามทีม

_Last Updated: 2025-01-XX_
