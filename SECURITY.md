# Security Policy

## Overview

This document outlines the security measures, best practices, and configurations for deploying the SQL Server Pipeline application in production environments.

## Version Information

**Current Version:** 2.2.0
**Last Security Update:** 2025-10-29

---

## 🔒 Security Features

### 1. SQL Injection Prevention

**Status:** ✅ **FIXED** (v2.2.0+)

The application now includes comprehensive SQL injection prevention:

- **Identifier Sanitization**: All schema, table, and column names are validated using `sanitize_sql_identifier()`
- **Parameterized Queries**: All user-supplied data uses parameterized queries via SQLAlchemy
- **Whitelist Validation**: Identifiers must match `^[a-zA-Z_][a-zA-Z0-9_]*$` pattern
- **Keyword Blacklist**: Dangerous SQL keywords are blocked (DROP, DELETE, EXEC, etc.)

**Implementation:**
```python
from utils.sql_utils import sanitize_sql_identifier, quote_identifier

# Always sanitize identifiers before use in SQL
safe_schema = sanitize_sql_identifier(schema_name)
safe_table = sanitize_sql_identifier(table_name)

# Use parameterized queries for data
query = text("SELECT * FROM sys.schemas WHERE name = :schema_name")
result = conn.execute(query, {"schema_name": safe_schema})
```

### 2. Credential Management

**Recommended for Production:** Windows Authentication

#### Windows Authentication (RECOMMENDED)
```env
# .env file
DB_SERVER=your_server
DB_NAME=your_database
DB_SCHEMA=bronze
DB_USERNAME=
DB_PASSWORD=
```

**Advantages:**
- No credentials stored in files
- Uses current Windows user account
- Automatic credential rotation
- Audit trail through Windows security

#### SQL Server Authentication (If Required)
```env
DB_SERVER=your_server
DB_NAME=your_database
DB_SCHEMA=bronze
DB_USERNAME=sql_user
DB_PASSWORD=strong_password_here
```

**Security Requirements:**
- Minimum 12 characters password
- Use Azure Key Vault or HashiCorp Vault in production
- Never commit `.env` file to version control
- Rotate passwords every 90 days
- Use service accounts with minimum required permissions

### 3. File System Security

**Protected Files:**
```gitignore
.env                    # Database credentials
config/*.json           # User-specific settings (except examples)
logs/                   # May contain sensitive data
processed/              # Processed files
```

**Recommendations:**
- Set appropriate file permissions (chmod 600 for .env)
- Store uploaded files in secure location
- Regular cleanup of processed files
- Enable disk encryption for sensitive data

### 4. Database Permissions

**Minimum Required Permissions:**
```sql
-- Grant minimum permissions to application service account
USE [YourDatabase];

-- Schema permissions
GRANT CREATE SCHEMA TO [app_service_account];
GRANT ALTER ON SCHEMA::[bronze] TO [app_service_account];

-- Table permissions
GRANT CREATE TABLE TO [app_service_account];
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::[bronze] TO [app_service_account];

-- Validation permissions
GRANT SELECT ON INFORMATION_SCHEMA.COLUMNS TO [app_service_account];
GRANT SELECT ON INFORMATION_SCHEMA.TABLES TO [app_service_account];
GRANT SELECT ON sys.schemas TO [app_service_account];
```

**Do NOT Grant:**
- `sysadmin` role
- `db_owner` role
- Permission to execute stored procedures
- Permission to create/modify logins
- Access to system databases

---

## 🛡️ Production Deployment Checklist

### Pre-Deployment

- [ ] Run security scan: `bandit -r . -f json -o security-report.json`
- [ ] Check for vulnerabilities: `pip-audit`
- [ ] Review and update `.env.example`
- [ ] Verify `.gitignore` includes `.env` and sensitive files
- [ ] Test with minimum database permissions
- [ ] Enable SQL Server audit logging

### Deployment

- [ ] Use `requirements-lock.txt` for consistent versions
- [ ] Create `.env` file with production credentials (use Key Vault in production)
- [ ] Set file permissions: `chmod 600 .env`
- [ ] Configure log rotation
- [ ] Set up monitoring and alerting
- [ ] Document the deployment in change management system

### Post-Deployment

- [ ] Verify no `.env` file in version control
- [ ] Test connection with service account
- [ ] Validate SQL injection prevention with test cases
- [ ] Review application logs for anomalies
- [ ] Schedule regular security scans
- [ ] Set up automated vulnerability monitoring

---

## 🔍 Security Scanning

### Recommended Tools

1. **Bandit** - Python security linter
   ```bash
   pip install bandit
   bandit -r . -f json -o security-report.json
   ```

2. **pip-audit** - Check for known vulnerabilities
   ```bash
   pip install pip-audit
   pip-audit -r requirements-lock.txt
   ```

3. **Safety** - Check dependencies for known issues
   ```bash
   pip install safety
   safety check -r requirements-lock.txt
   ```

### Automated Scanning

**GitHub Actions (Recommended):**
```yaml
# .github/workflows/security-scan.yml
name: Security Scan
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install bandit pip-audit safety
      - run: bandit -r . -f json -o security-report.json
      - run: pip-audit -r requirements-lock.txt
      - run: safety check -r requirements-lock.txt
```

---

## 📋 Secure Configuration Guidelines

### 1. Database Connection

**Bad Practice ❌:**
```python
# Never hardcode credentials
conn_string = "mssql+pyodbc://sa:password123@server/db"
```

**Good Practice ✅:**
```python
# Use environment variables
from config.database import DatabaseConfig
db_config = DatabaseConfig()  # Loads from .env
```

### 2. Error Messages

**Bad Practice ❌:**
```python
# Don't expose internal details to users
except Exception as e:
    messagebox.showerror("Error", f"Database error: {str(e)}")
```

**Good Practice ✅:**
```python
# Log detailed errors, show generic message to user
except Exception as e:
    logger.error(f"Database error: {e}", exc_info=True)
    messagebox.showerror("Error", "An error occurred. Please contact support.")
```

### 3. SQL Query Construction

**Bad Practice ❌:**
```python
# SQL injection vulnerability!
query = f"SELECT * FROM {user_table} WHERE id = {user_id}"
```

**Good Practice ✅:**
```python
# Use sanitization and parameterized queries
safe_table = sanitize_sql_identifier(user_table)
query = text(f"SELECT * FROM {quote_identifier(safe_table)} WHERE id = :user_id")
conn.execute(query, {"user_id": user_id})
```

---

## 🚨 Incident Response

### Suspected SQL Injection Attack

1. **Immediate Actions:**
   - Disconnect application from database
   - Review SQL Server audit logs
   - Check for unauthorized schema/table changes
   - Verify data integrity

2. **Investigation:**
   - Review application logs for suspicious queries
   - Check for unusual user activity
   - Analyze failed login attempts
   - Document findings

3. **Recovery:**
   - Restore from backup if data compromised
   - Update credentials
   - Patch application if vulnerability found
   - Notify stakeholders

### Credential Exposure

1. **Immediate Actions:**
   - Rotate all exposed credentials immediately
   - Review recent database activity
   - Check for unauthorized access
   - Remove exposed credentials from version control history

2. **Prevention:**
   - Use git-secrets to prevent credential commits
   - Implement pre-commit hooks
   - Use secret scanning tools (GitHub Advanced Security)

---

## 📞 Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

**Instead:**
1. Email security concerns to your security team
2. Include detailed description and reproduction steps
3. Wait for acknowledgment before public disclosure
4. Follow responsible disclosure guidelines

---

## 🔄 Security Update Policy

- **Critical vulnerabilities**: Patched within 24 hours
- **High severity**: Patched within 7 days
- **Medium severity**: Patched within 30 days
- **Low severity**: Patched in next regular release

---

## 📚 References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [Microsoft SQL Server Security Best Practices](https://learn.microsoft.com/en-us/sql/relational-databases/security/security-center-for-sql-server-database-engine-and-azure-sql-database)

---

## ✅ Security Audit History

| Date | Version | Audit Type | Findings | Status |
|------|---------|------------|----------|--------|
| 2025-10-29 | 2.2.0 | SQL Injection Review | Fixed all critical SQL injection vulnerabilities | ✅ Complete |
| 2025-10-29 | 2.2.0 | Dependency Audit | Locked dependency versions | ✅ Complete |
| 2025-10-29 | 2.2.0 | Credential Management | Documented best practices | ✅ Complete |

---

**Last Updated:** 2025-10-29
**Next Review:** 2025-11-29
