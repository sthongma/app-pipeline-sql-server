"""
Tests for security utilities including SQL injection prevention and password masking
"""

import pytest
from utils.sql_utils import (
    sanitize_sql_identifier,
    quote_identifier,
    build_qualified_table_name,
    validate_identifier_list
)
from utils.security_helpers import (
    mask_password,
    mask_connection_string,
    mask_credentials_in_dict
)


class TestSQLIdentifierSanitization:
    """Test SQL identifier sanitization for SQL injection prevention"""

    def test_valid_identifiers(self):
        """Test that valid identifiers pass validation"""
        valid_names = ['table1', 'my_table', 'Table_Name_123', '_private', 'bronze']
        for name in valid_names:
            assert sanitize_sql_identifier(name) == name

    def test_invalid_characters(self):
        """Test that identifiers with invalid characters are rejected"""
        invalid_names = [
            'table;DROP',
            'table--comment',
            'table name',  # space
            'table@special',
            'table$pecial',
            '123table',  # starts with number
            'table.column',  # dot
        ]
        for name in invalid_names:
            with pytest.raises(ValueError):
                sanitize_sql_identifier(name)

    def test_dangerous_keywords(self):
        """Test that dangerous SQL keywords are blocked"""
        dangerous = ['drop', 'DROP', 'delete', 'DELETE', 'exec', 'truncate']
        for keyword in dangerous:
            with pytest.raises(ValueError, match="SQL keyword"):
                sanitize_sql_identifier(keyword)

    def test_length_limit(self):
        """Test that identifiers exceeding max length are rejected"""
        long_name = 'a' * 129  # 129 characters (max is 128)
        with pytest.raises(ValueError, match="too long"):
            sanitize_sql_identifier(long_name)

    def test_empty_identifier(self):
        """Test that empty identifiers are rejected"""
        with pytest.raises(ValueError):
            sanitize_sql_identifier('')
        with pytest.raises(ValueError):
            sanitize_sql_identifier(None)

    def test_quote_identifier(self):
        """Test that identifiers are properly quoted"""
        assert quote_identifier('mytable') == '[mytable]'
        assert quote_identifier('My_Table_123') == '[My_Table_123]'

    def test_build_qualified_table_name(self):
        """Test building schema.table names"""
        result = build_qualified_table_name('bronze', 'sales')
        assert result == '[bronze].[sales]'

    def test_validate_identifier_list(self):
        """Test batch validation of identifiers"""
        valid_list = ['table1', 'table2', 'column_name']
        assert validate_identifier_list(valid_list) == True

        invalid_list = ['table1', 'drop', 'table2']
        with pytest.raises(ValueError):
            validate_identifier_list(invalid_list)


class TestPasswordMasking:
    """Test password masking utilities"""

    def test_mask_password_basic(self):
        """Test basic password masking"""
        assert mask_password('MyPassword123') == '*************'
        assert mask_password('secret') == '******'

    def test_mask_password_with_visible_chars(self):
        """Test password masking with visible characters"""
        assert mask_password('MyPassword123', visible_chars=3) == '**********123'
        assert mask_password('secret', visible_chars=2) == '****et'

    def test_mask_connection_string(self):
        """Test masking passwords in connection strings"""
        # SQLAlchemy format
        conn_str = "mssql+pyodbc://user:password123@server/db"
        masked = mask_connection_string(conn_str)
        assert 'password123' not in masked
        assert '****' in masked
        assert 'user' in masked
        assert 'server/db' in masked

        # ODBC PWD format
        odbc_str = "SERVER=localhost;DATABASE=mydb;PWD=secret123;UID=admin"
        masked = mask_connection_string(odbc_str)
        assert 'secret123' not in masked
        assert 'PWD=****' in masked

    def test_mask_credentials_in_dict(self):
        """Test masking credentials in configuration dictionaries"""
        config = {
            'server': 'localhost',
            'database': 'mydb',
            'username': 'admin',
            'password': 'secret123',
            'port': 1433
        }
        masked = mask_credentials_in_dict(config)
        assert masked['password'] == '****'
        assert masked['server'] == 'localhost'
        assert masked['username'] == 'admin'  # username is not masked
        assert 'secret123' not in str(masked)

    def test_mask_various_password_keys(self):
        """Test masking various password-like keys"""
        config = {
            'api_key': 'key123',
            'access_token': 'token456',
            'db_password': 'pass789',
            'regular_field': 'normal_value'
        }
        masked = mask_credentials_in_dict(config)
        assert masked['api_key'] == '****'
        assert masked['access_token'] == '****'
        assert masked['db_password'] == '****'
        assert masked['regular_field'] == 'normal_value'


class TestSQLInjectionPrevention:
    """Integration tests for SQL injection prevention"""

    def test_sql_injection_attempts(self):
        """Test that common SQL injection attempts are blocked"""
        injection_attempts = [
            "'; DROP TABLE users--",
            "1' OR '1'='1",
            "admin'--",
            "' OR 1=1--",
            "'; DELETE FROM users WHERE '1'='1",
            "1'; EXEC xp_cmdshell('dir')--"
        ]

        for attempt in injection_attempts:
            with pytest.raises(ValueError):
                sanitize_sql_identifier(attempt)

    def test_safe_schema_table_construction(self):
        """Test that schema.table names are safely constructed"""
        # These should work
        safe_schema = sanitize_sql_identifier('bronze')
        safe_table = sanitize_sql_identifier('sales_data')
        qualified = build_qualified_table_name('bronze', 'sales_data')
        assert qualified == '[bronze].[sales_data]'

        # This should fail
        with pytest.raises(ValueError):
            sanitize_sql_identifier("bronze'; DROP TABLE--")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
