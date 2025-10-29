"""
Integration tests for SQL Server Pipeline
These tests require a real SQL Server instance with proper configuration
Run with: pytest tests/test_integration.py -v -m integration
"""

import pytest
import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text, inspect

from config.database import DatabaseConfig
from services.database.schema_service import SchemaService
from services.database.connection_service import ConnectionService
from utils.health_check import check_database_health, HealthStatus


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_config():
    """
    Load database configuration from environment.

    Requires .env file or environment variables:
    - DB_SERVER
    - DB_NAME
    - DB_USERNAME (optional for Windows Auth)
    - DB_PASSWORD (optional for Windows Auth)
    """
    config = DatabaseConfig()

    # Skip if no valid configuration
    if not config.config or not config.config.get('server'):
        pytest.skip("No database configuration found. Set DB_SERVER and DB_NAME in .env")

    return config


@pytest.fixture(scope="module")
def engine(db_config):
    """Create database engine for testing"""
    db_config.update_engine()
    engine = db_config.get_engine()

    if not engine:
        pytest.skip("Could not create database engine")

    yield engine

    # Cleanup: Close all connections
    engine.dispose()


@pytest.fixture(scope="module")
def test_schema_name():
    """Test schema name - will be created and cleaned up"""
    return "test_pipeline"


@pytest.fixture(scope="function")
def clean_test_schema(engine, test_schema_name):
    """
    Fixture to clean up test schema before and after each test
    """
    # Cleanup before test
    with engine.begin() as conn:
        # Drop test schema if exists
        conn.execute(text(f"""
            IF EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{test_schema_name}')
            BEGIN
                DECLARE @sql NVARCHAR(MAX) = '';
                SELECT @sql += 'DROP TABLE [' + '{test_schema_name}' + '].[' + name + ']; '
                FROM sys.tables
                WHERE schema_id = SCHEMA_ID('{test_schema_name}');
                EXEC sp_executesql @sql;
                DROP SCHEMA [{test_schema_name}];
            END
        """))

    yield

    # Cleanup after test
    with engine.begin() as conn:
        conn.execute(text(f"""
            IF EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{test_schema_name}')
            BEGIN
                DECLARE @sql NVARCHAR(MAX) = '';
                SELECT @sql += 'DROP TABLE [' + '{test_schema_name}' + '].[' + name + ']; '
                FROM sys.tables
                WHERE schema_id = SCHEMA_ID('{test_schema_name}');
                EXEC sp_executesql @sql;
                DROP SCHEMA [{test_schema_name}];
            END
        """))


class TestDatabaseConnection:
    """Test database connectivity"""

    def test_database_connection(self, engine):
        """Test basic database connection"""
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS test"))
            assert result.fetchone()[0] == 1

    def test_connection_service(self, db_config):
        """Test ConnectionService"""
        conn_service = ConnectionService(db_config)
        success, message = conn_service.check_connection(show_warning=False)
        assert success is True
        assert "successful" in message.lower()

    def test_health_check(self, engine):
        """Test database health check"""
        status, details = check_database_health(engine)

        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert details['response_time_ms'] >= 0
        assert 'timestamp' in details

        # Response time should be reasonable
        assert details['response_time_ms'] < 5000  # Less than 5 seconds


class TestSchemaOperations:
    """Test schema creation and management"""

    def test_create_schema(self, engine, test_schema_name, clean_test_schema):
        """Test schema creation"""
        schema_service = SchemaService(engine)
        success, message = schema_service.ensure_schemas_exist([test_schema_name])

        assert success is True
        assert test_schema_name in message

        # Verify schema exists
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT COUNT(*) FROM sys.schemas WHERE name = '{test_schema_name}'
            """))
            assert result.scalar() == 1

    def test_create_duplicate_schema(self, engine, test_schema_name, clean_test_schema):
        """Test creating schema that already exists"""
        schema_service = SchemaService(engine)

        # Create first time
        success1, _ = schema_service.ensure_schemas_exist([test_schema_name])
        assert success1 is True

        # Create again (should succeed without error)
        success2, _ = schema_service.ensure_schemas_exist([test_schema_name])
        assert success2 is True


class TestDataUpload:
    """Test data upload operations"""

    def test_create_and_upload_data(self, engine, test_schema_name, clean_test_schema):
        """Test creating table and uploading data"""
        # Create test data
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie'],
            'value': [100, 200, 300]
        })

        # Create schema
        schema_service = SchemaService(engine)
        schema_service.ensure_schemas_exist([test_schema_name])

        # Upload data
        df.to_sql(
            name='test_table',
            con=engine,
            schema=test_schema_name,
            if_exists='replace',
            index=False
        )

        # Verify data
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM [{test_schema_name}].[test_table]"))
            count = result.scalar()
            assert count == 3

            # Check data content
            result = conn.execute(text(f"SELECT name FROM [{test_schema_name}].[test_table] ORDER BY id"))
            names = [row[0] for row in result.fetchall()]
            assert names == ['Alice', 'Bob', 'Charlie']

    def test_large_batch_upload(self, engine, test_schema_name, clean_test_schema):
        """Test uploading larger dataset"""
        # Create larger dataset
        df = pd.DataFrame({
            'id': range(1000),
            'value': [i * 10 for i in range(1000)],
            'text': [f'row_{i}' for i in range(1000)]
        })

        # Create schema
        schema_service = SchemaService(engine)
        schema_service.ensure_schemas_exist([test_schema_name])

        # Upload data
        df.to_sql(
            name='large_test_table',
            con=engine,
            schema=test_schema_name,
            if_exists='replace',
            index=False
        )

        # Verify data
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM [{test_schema_name}].[large_test_table]"))
            count = result.scalar()
            assert count == 1000


class TestConnectionPooling:
    """Test connection pooling behavior"""

    def test_multiple_connections(self, engine):
        """Test that multiple connections work correctly"""
        results = []

        # Open multiple connections
        for i in range(5):
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT {i} AS num"))
                results.append(result.fetchone()[0])

        assert results == [0, 1, 2, 3, 4]

    def test_connection_pool_exhaustion(self, engine):
        """Test behavior when connection pool is exhausted"""
        # Get pool configuration
        pool_size = getattr(engine.pool, 'size', lambda: 5)()
        max_overflow = getattr(engine.pool, '_max_overflow', 10)

        # Try to open more connections than pool allows
        connections = []
        try:
            for i in range(pool_size + max_overflow + 1):
                conn = engine.connect()
                connections.append(conn)
                # Do simple query to verify connection works
                conn.execute(text("SELECT 1"))
        except Exception as e:
            # Should eventually timeout or fail
            assert "timeout" in str(e).lower() or "pool" in str(e).lower()
        finally:
            # Cleanup connections
            for conn in connections:
                try:
                    conn.close()
                except:
                    pass


class TestSQLInjectionPrevention:
    """Integration tests for SQL injection prevention"""

    def test_schema_name_injection_prevention(self, engine):
        """Test that malicious schema names are rejected"""
        from utils.sql_utils import sanitize_sql_identifier

        malicious_names = [
            "'; DROP TABLE users--",
            "test; DELETE FROM data--",
            "1' OR '1'='1"
        ]

        for name in malicious_names:
            with pytest.raises(ValueError):
                sanitize_sql_identifier(name)


# Skip integration tests by default
# Run with: pytest -v -m integration
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires SQL Server)"
    )
