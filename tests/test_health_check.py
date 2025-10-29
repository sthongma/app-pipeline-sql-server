"""
Tests for health check functionality
"""

import pytest
from unittest.mock import Mock, MagicMock
from utils.health_check import (
    HealthStatus,
    check_application_health,
    check_database_health,
    perform_full_health_check
)


class TestHealthCheck:
    """Test health check utilities"""

    def test_application_health_check(self):
        """Test basic application health check"""
        status, details = check_application_health()
        assert status == HealthStatus.HEALTHY
        assert 'timestamp' in details
        assert details['status'] == HealthStatus.HEALTHY

    def test_database_health_check_success(self):
        """Test successful database health check"""
        # Create mock engine
        mock_engine = Mock()
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)

        # Setup mock behavior
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value = mock_conn
        mock_engine.pool = Mock()
        mock_engine.pool.size = Mock(return_value=5)
        mock_engine.pool.checkedin = Mock(return_value=4)
        mock_engine.pool.checkedout = Mock(return_value=1)
        mock_engine.pool.overflow = Mock(return_value=0)

        status, details = check_database_health(mock_engine)

        assert status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert 'response_time_ms' in details
        assert 'timestamp' in details
        assert details['response_time_ms'] >= 0

    def test_database_health_check_failure(self):
        """Test database health check with connection failure"""
        # Create mock engine that raises exception
        mock_engine = Mock()
        mock_engine.connect.side_effect = Exception("Connection refused")

        status, details = check_database_health(mock_engine)

        assert status == HealthStatus.UNHEALTHY
        assert 'Connection refused' in details['message']
        assert 'response_time_ms' in details

    def test_full_health_check_without_db(self):
        """Test full health check without database engine"""
        report = perform_full_health_check(engine=None)

        assert 'timestamp' in report
        assert 'overall_status' in report
        assert 'components' in report
        assert 'application' in report['components']
        assert 'database' in report['components']
        assert report['components']['database']['status'] == HealthStatus.UNKNOWN

    def test_full_health_check_with_db(self):
        """Test full health check with database engine"""
        # Create mock engine with successful connection
        mock_engine = Mock()
        mock_conn = MagicMock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)

        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value = mock_conn
        mock_engine.pool = Mock()
        mock_engine.pool.size = Mock(return_value=5)
        mock_engine.pool.checkedin = Mock(return_value=4)
        mock_engine.pool.checkedout = Mock(return_value=1)
        mock_engine.pool.overflow = Mock(return_value=0)

        report = perform_full_health_check(engine=mock_engine)

        assert 'components' in report
        assert 'application' in report['components']
        assert 'database' in report['components']
        assert report['components']['application']['status'] == HealthStatus.HEALTHY


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
