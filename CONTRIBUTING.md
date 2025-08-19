# Contributing to PIPELINE_SQLSERVER

ยินดีต้อนรับผู้ร่วมพัฒนา! 🎉 

เอกสารนี้อธิบายวิธีการมีส่วนร่วมในโครงการ PIPELINE_SQLSERVER

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)  
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Architecture Guidelines](#architecture-guidelines)

## Code of Conduct

เราตั้งใจที่จะสร้างสิ่งแวดล้อมที่เป็นมิตรและเปิดกว้างสำหรับทุกคน:

- ใช้ภาษาที่เป็นมิตรและรวมทุกคน
- เคารพมุมมองและประสบการณ์ที่แตกต่าง
- ยอมรับคำติชมที่สร้างสรรค์อย่างสุภาพ
- มุ่งเน้นสิ่งที่ดีที่สุดสำหรับชุมชน
- แสดงความเห็นอกเห็นใจต่อสมาชิกชุมชนอื่น ๆ

## Getting Started

### Prerequisites

- Python 3.8+ 
- Git
- SQL Server หรือ SQL Server Express
- ความรู้พื้นฐานเกี่ยวกับ Python และ SQL

### Fork และ Clone

```bash
# 1. Fork repository บน GitHub
# 2. Clone repository ที่ fork มา
git clone https://github.com/YOUR_USERNAME/PIPELINE_SQLSERVER.git
cd PIPELINE_SQLSERVER

# 3. เพิ่ม upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/PIPELINE_SQLSERVER.git
```

## Development Setup

### 1. สร้าง Development Environment

```bash
# สร้าง virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# ติดตั้ง dependencies
pip install -r requirements.txt

# ติดตั้ง development dependencies  
pip install -e ".[dev]"
```

### 2. ตั้งค่า Environment Variables

```bash
# รันสคริปต์ setup
python install_requirements.py

# แก้ไข .env สำหรับ development
# ใช้ test database แยกจาก production
```

### 3. ตรวจสอบ Setup

```bash
# รัน tests เพื่อตรวจสอบ
python -m pytest

# รันโปรแกรมเพื่อทดสอบ
python pipeline_gui_app.py
```

## How to Contribute

### 🐛 รายงานปัญหา (Bug Reports)

เมื่อพบปัญหา กรุณาสร้าง GitHub Issue พร้อม:

1. **ชื่อเรื่องที่ชัดเจน**: อธิบายปัญหาสั้นๆ
2. **ขั้นตอนการทำซ้ำ**: วิธีทำให้เกิดปัญหา  
3. **ผลลัพธ์ที่คาดหวัง**: สิ่งที่ควรเกิดขึ้น
4. **ผลลัพธ์จริง**: สิ่งที่เกิดขึ้นจริง
5. **สภาพแวดล้อม**: OS, Python version, SQL Server version
6. **Screenshots**: ถ้ามี

### ✨ ขอฟีเจอร์ใหม่ (Feature Requests)

1. ตรวจสอบว่ายังไม่มี issue ที่คล้ายกัน
2. สร้าง issue ใหม่พร้อมอธิบาย:
   - ปัญหาที่ฟีเจอร์จะช่วยแก้
   - วิธีการใช้งานที่เสนอ
   - ตัวอย่างการใช้งาน

### 🔧 การส่ง Code

1. สร้าง branch ใหม่:
```bash
git checkout -b feature/amazing-feature
# หรือ
git checkout -b bugfix/fix-connection-issue
```

2. ทำการเปลี่ยนแปลง
3. Commit พร้อม message ที่ชัดเจน
4. Push และสร้าง Pull Request

## Code Style Guidelines

### Python Code Style

เราใช้มาตรฐาน PEP 8 พร้อมปรับแต่งเพิ่มเติม:

```python
# ✅ GOOD
def process_excel_file(file_path: str, logic_type: str) -> Tuple[bool, pd.DataFrame]:
    """
    Process Excel file and return dataframe.
    
    Args:
        file_path: Path to Excel file
        logic_type: Type of data logic
        
    Returns:
        Tuple of success status and dataframe
    """
    pass

# ❌ BAD  
def process_file(file_path, type):
    pass
```

### Key Guidelines

1. **Type Hints**: ใช้ type hints ทุกที่
2. **Docstrings**: เขียน docstring สำหรับทุก public function
3. **Naming**: ใช้ descriptive names
   - Functions: `snake_case`
   - Classes: `PascalCase` 
   - Constants: `UPPER_CASE`
   - Variables: `snake_case`
4. **Comments**: เขียนเป็นภาษาอังกฤษ
5. **Line Length**: ไม่เกิน 100 characters

### Architecture Patterns

```python
# ✅ GOOD - ใช้ Orchestrator pattern
from services.orchestrators.file_orchestrator import FileOrchestrator

file_orchestrator = FileOrchestrator()
success, df = file_orchestrator.read_excel_file(path, logic_type)

# ❌ BAD - เรียก service โดยตรง
from services.file.file_reader_service import FileReaderService
service = FileReaderService()
```

## Testing Guidelines

### การเขียน Tests

1. **Unit Tests**: สำหรับ individual services
2. **Integration Tests**: สำหรับ orchestrators
3. **End-to-End Tests**: สำหรับ complete workflows

### Test Structure

```python
import pytest
from services.orchestrators.file_orchestrator import FileOrchestrator

class TestFileOrchestrator:
    def test_read_excel_file_success(self):
        """Test successful Excel file reading"""
        orchestrator = FileOrchestrator()
        success, df = orchestrator.read_excel_file("test.xlsx", "sales")
        
        assert success is True
        assert df is not None
        assert len(df) > 0
    
    def test_read_excel_file_not_found(self):
        """Test handling of non-existent file"""
        orchestrator = FileOrchestrator()
        success, df = orchestrator.read_excel_file("missing.xlsx", "sales")
        
        assert success is False
        assert df is None
```

### รัน Tests

```bash
# รัน tests ทั้งหมด
pytest

# รัน tests เฉพาะ service
pytest tests/test_file_orchestrator.py

# รัน tests พร้อม coverage
pytest --cov=services

# รัน tests แบบ verbose
pytest -v
```

## Pull Request Process

### 1. ก่อนส่ง PR

```bash
# อัพเดท code จาก upstream
git fetch upstream
git checkout main
git merge upstream/main

# Rebase feature branch
git checkout feature/your-feature
git rebase main

# รัน tests
pytest

# ตรวจสอบ code style
black .
flake8 .
mypy .
```

### 2. สร้าง Pull Request

#### PR Title Format:
- `feat: add new Excel validation feature`
- `fix: resolve database connection timeout`
- `docs: update installation guide` 
- `refactor: improve orchestrator error handling`

#### PR Description Template:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)  
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Code is commented adequately
- [ ] Documentation updated
```

### 3. Review Process

1. **Automatic Checks**: CI/CD จะรัน tests และ code quality checks
2. **Code Review**: Maintainers จะตรวจสอบ code
3. **Feedback**: อาจมีการขอให้แก้ไขเพิ่มเติม
4. **Approval**: หลังจากผ่านการตรวจสอบแล้วจะ merge

## Architecture Guidelines

### Service Organization

ปฏิบัติตาม Clean Architecture v2.0:

```
services/
├── orchestrators/       # High-level coordination
├── database/           # Database operations  
├── file/              # File operations
└── utilities/         # Cross-cutting concerns
```

### Adding New Features

#### 1. New File Type Support
```python
# 1. Add to FileReaderService
# 2. Update FileOrchestrator  
# 3. Add validation rules
# 4. Update documentation
```

#### 2. New Database Operation
```python
# 1. Create service in services/database/
# 2. Integrate with DatabaseOrchestrator
# 3. Add tests
# 4. Update documentation
```

#### 3. New Validation Rule
```python
# 1. Create validator in services/database/validation/
# 2. Register with ValidationOrchestrator
# 3. Add comprehensive tests
```

### Dependencies

- **Orchestrators** ← coordinate → **Services**
- **Services** ← use → **Utilities**
- **UI** ← calls → **Orchestrators** (not Services directly)

## Release Process

1. **Version Bump**: อัพเดท version ใน relevant files
2. **Changelog**: อัพเดท CHANGELOG.md
3. **Documentation**: อัพเดท documentation ถ้าจำเป็น
4. **Testing**: รัน comprehensive tests
5. **Tag**: สร้าง git tag สำหรับ release

## Questions and Help

- **GitHub Discussions**: สำหรับคำถามทั่วไป
- **GitHub Issues**: สำหรับ bugs และ feature requests
- **Code Questions**: ใน PR comments หรือ issue discussion

## Recognition

Contributors จะได้รับการยกย่องใน:
- README.md
- CHANGELOG.md  
- Git commit history
- Release notes

---

**ขอบคุณสำหรับการมีส่วนร่วม! 🙏**

การมีส่วนร่วมของคุณทำให้โครงการนี้ดีขึ้นสำหรับทุกคน