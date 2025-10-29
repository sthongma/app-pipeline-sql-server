"""
Health check utilities for monitoring application and database status
"""

import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class HealthStatus:
    """Health check status codes"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


def check_database_health(engine: Engine, timeout: int = 5) -> Tuple[str, Dict]:
    """
    Check database connection health.

    Args:
        engine: SQLAlchemy engine
        timeout: Query timeout in seconds

    Returns:
        Tuple[str, Dict]: (status, details)
            status: One of HealthStatus values
            details: Dictionary with diagnostic information
    """
    start_time = time.time()
    details = {
        "timestamp": datetime.now().isoformat(),
        "response_time_ms": 0,
        "pool_size": 0,
        "pool_checked_in": 0,
        "pool_checked_out": 0,
        "pool_overflow": 0,
        "message": ""
    }

    try:
        # Test basic connectivity with simple query
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS health_check"))
            row = result.fetchone()

            # Calculate response time
            elapsed = (time.time() - start_time) * 1000
            details["response_time_ms"] = round(elapsed, 2)

            # Get connection pool stats if available
            if hasattr(engine.pool, 'size'):
                details["pool_size"] = engine.pool.size()
            if hasattr(engine.pool, 'checkedin'):
                details["pool_checked_in"] = engine.pool.checkedin()
            if hasattr(engine.pool, 'checkedout'):
                details["pool_checked_out"] = engine.pool.checkedout()
            if hasattr(engine.pool, 'overflow'):
                details["pool_overflow"] = engine.pool.overflow()

            # Determine health status based on response time
            if elapsed < 1000:  # < 1 second
                status = HealthStatus.HEALTHY
                details["message"] = "Database connection is healthy"
            elif elapsed < 5000:  # < 5 seconds
                status = HealthStatus.DEGRADED
                details["message"] = "Database connection is slow"
                logger.warning(f"Slow database response: {elapsed}ms")
            else:
                status = HealthStatus.UNHEALTHY
                details["message"] = "Database connection is very slow"
                logger.error(f"Very slow database response: {elapsed}ms")

            return status, details

    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        details["response_time_ms"] = round(elapsed, 2)
        details["message"] = f"Database connection failed: {str(e)[:200]}"
        logger.error(f"Database health check failed: {e}")
        return HealthStatus.UNHEALTHY, details


def check_application_health() -> Tuple[str, Dict]:
    """
    Check overall application health.

    Returns:
        Tuple[str, Dict]: (status, details)
    """
    details = {
        "timestamp": datetime.now().isoformat(),
        "status": HealthStatus.HEALTHY,
        "message": "Application is running"
    }

    try:
        # Add more checks as needed (disk space, memory, etc.)
        return HealthStatus.HEALTHY, details
    except Exception as e:
        details["status"] = HealthStatus.UNHEALTHY
        details["message"] = f"Application health check failed: {e}"
        return HealthStatus.UNHEALTHY, details


def perform_full_health_check(engine: Optional[Engine] = None) -> Dict:
    """
    Perform a comprehensive health check of all components.

    Args:
        engine: SQLAlchemy engine (optional)

    Returns:
        Dict: Complete health check report
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": HealthStatus.HEALTHY,
        "components": {}
    }

    # Check application health
    app_status, app_details = check_application_health()
    report["components"]["application"] = {
        "status": app_status,
        "details": app_details
    }

    # Check database health if engine provided
    if engine:
        db_status, db_details = check_database_health(engine)
        report["components"]["database"] = {
            "status": db_status,
            "details": db_details
        }

        # Determine overall status
        if db_status == HealthStatus.UNHEALTHY or app_status == HealthStatus.UNHEALTHY:
            report["overall_status"] = HealthStatus.UNHEALTHY
        elif db_status == HealthStatus.DEGRADED or app_status == HealthStatus.DEGRADED:
            report["overall_status"] = HealthStatus.DEGRADED
    else:
        report["components"]["database"] = {
            "status": HealthStatus.UNKNOWN,
            "details": {"message": "No database engine provided"}
        }

    return report


def save_health_check_to_file(report: Dict, file_path: str = "health_status.json") -> bool:
    """
    Save health check report to JSON file.

    Args:
        report: Health check report
        file_path: Path to save file

    Returns:
        bool: Success status
    """
    try:
        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save health check report: {e}")
        return False
