"""
Simple monitoring dashboard for SQL Server Pipeline

Generates HTML dashboard with system metrics and health status

Usage:
    python monitoring/dashboard.py
    python monitoring/dashboard.py --output dashboard.html --refresh 30
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from config.database import DatabaseConfig
from utils.health_check import perform_full_health_check


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQL Server Pipeline - Monitoring Dashboard</title>
    <meta http-equiv="refresh" content="{refresh_interval}">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        .header {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .header h1 {{
            color: #667eea;
            margin-bottom: 10px;
        }}

        .header .subtitle {{
            color: #666;
            font-size: 14px;
        }}

        .status-card {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .status-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}

        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .status-healthy {{
            background: #d1fae5;
            color: #065f46;
        }}

        .status-degraded {{
            background: #fed7aa;
            color: #92400e;
        }}

        .status-unhealthy {{
            background: #fecaca;
            color: #991b1b;
        }}

        .status-unknown {{
            background: #e5e7eb;
            color: #374151;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}

        .metric {{
            background: #f9fafb;
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #667eea;
        }}

        .metric-label {{
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}

        .metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: #1f2937;
        }}

        .metric-unit {{
            font-size: 14px;
            color: #9ca3af;
            margin-left: 4px;
        }}

        .components-list {{
            list-style: none;
        }}

        .component {{
            background: #f9fafb;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .component-name {{
            font-weight: 600;
            color: #1f2937;
        }}

        .timestamp {{
            text-align: right;
            color: #9ca3af;
            font-size: 12px;
            margin-top: 20px;
        }}

        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            font-size: 14px;
        }}

        .refresh-info {{
            background: rgba(255,255,255,0.1);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 10px;
            font-size: 12px;
        }}

        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 SQL Server Pipeline</h1>
            <p class="subtitle">System Monitoring Dashboard</p>
        </div>

        <div class="status-card">
            <div class="status-header">
                <h2>Overall System Status</h2>
                <span class="status-badge status-{overall_status}">{overall_status_text}</span>
            </div>

            <ul class="components-list">
                {components_html}
            </ul>
        </div>

        <div class="status-card">
            <h2>Database Metrics</h2>
            <div class="metrics-grid">
                {metrics_html}
            </div>
        </div>

        <div class="timestamp">
            Last updated: {timestamp}<br>
            Auto-refresh: {refresh_interval} seconds
        </div>

        <div class="footer">
            <p>SQL Server Pipeline v2.2.0 | Monitoring Dashboard</p>
            <div class="refresh-info">
                ⟳ Page refreshes automatically every {refresh_interval} seconds
            </div>
        </div>
    </div>
</body>
</html>"""


def get_status_class(status: str) -> str:
    """Get CSS class for status"""
    return status.replace('_', '-').lower()


def format_metric_value(value, decimals: int = 2) -> str:
    """Format metric value"""
    if isinstance(value, (int, float)):
        if decimals == 0:
            return f"{value:,.0f}"
        else:
            return f"{value:,.{decimals}f}"
    return str(value)


def generate_dashboard_html(health_report: Dict, refresh_interval: int = 30) -> str:
    """
    Generate HTML dashboard from health report

    Args:
        health_report: Health check report dictionary
        refresh_interval: Page refresh interval in seconds

    Returns:
        str: HTML dashboard content
    """
    # Overall status
    overall_status = health_report.get('overall_status', 'unknown')
    overall_status_text = overall_status.upper().replace('_', ' ')

    # Components
    components_html = ""
    for component_name, component_data in health_report.get('components', {}).items():
        status = component_data.get('status', 'unknown')
        details = component_data.get('details', {})
        message = details.get('message', 'No details available')

        components_html += f"""
        <li class="component">
            <span class="component-name">📦 {component_name.title()}</span>
            <span class="status-badge status-{get_status_class(status)}">{status.upper()}</span>
        </li>
        """

    # Database metrics
    db_details = health_report.get('components', {}).get('database', {}).get('details', {})

    metrics = [
        ('Response Time', db_details.get('response_time_ms', 0), 'ms', 2),
        ('Pool Size', db_details.get('pool_size', 0), '', 0),
        ('Checked Out', db_details.get('pool_checked_out', 0), 'connections', 0),
        ('Checked In', db_details.get('pool_checked_in', 0), 'connections', 0),
        ('Pool Overflow', db_details.get('pool_overflow', 0), '', 0),
    ]

    metrics_html = ""
    for label, value, unit, decimals in metrics:
        formatted_value = format_metric_value(value, decimals)
        metrics_html += f"""
        <div class="metric">
            <div class="metric-label">{label}</div>
            <div class="metric-value">
                {formatted_value}
                <span class="metric-unit">{unit}</span>
            </div>
        </div>
        """

    # Timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Fill template
    html = HTML_TEMPLATE.format(
        overall_status=get_status_class(overall_status),
        overall_status_text=overall_status_text,
        components_html=components_html,
        metrics_html=metrics_html,
        timestamp=timestamp,
        refresh_interval=refresh_interval
    )

    return html


def generate_dashboard(output_file: str = "dashboard.html", refresh_interval: int = 30):
    """
    Generate monitoring dashboard

    Args:
        output_file: Output HTML file path
        refresh_interval: Page refresh interval in seconds
    """
    print(f"🔍 Generating monitoring dashboard...")

    # Load database config
    db_config = DatabaseConfig()
    db_config.update_engine()
    engine = db_config.get_engine()

    if not engine:
        print("❌ Failed to create database engine. Check your configuration.")
        return

    # Perform health check
    print("   Performing health check...")
    health_report = perform_full_health_check(engine)

    # Generate HTML
    print("   Generating HTML...")
    html = generate_dashboard_html(health_report, refresh_interval)

    # Write to file
    output_path = Path(output_file)
    output_path.write_text(html, encoding='utf-8')

    print(f"✅ Dashboard generated: {output_path.absolute()}")
    print(f"   Open in browser: file://{output_path.absolute()}")
    print(f"   Auto-refresh: {refresh_interval} seconds")

    # Also save JSON report
    json_file = output_path.with_suffix('.json')
    json_file.write_text(json.dumps(health_report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"   JSON report: {json_file}")


def continuous_monitoring(output_file: str = "dashboard.html",
                          refresh_interval: int = 30,
                          update_interval: int = 30):
    """
    Run continuous monitoring (regenerate dashboard periodically)

    Args:
        output_file: Output HTML file path
        refresh_interval: HTML page auto-refresh interval
        update_interval: Dashboard regeneration interval
    """
    print(f"🔍 Starting continuous monitoring...")
    print(f"   Dashboard: {output_file}")
    print(f"   Update interval: {update_interval} seconds")
    print(f"   Press Ctrl+C to stop")
    print()

    try:
        while True:
            generate_dashboard(output_file, refresh_interval)
            print(f"   Next update in {update_interval} seconds...")
            time.sleep(update_interval)

    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped")


def main():
    parser = argparse.ArgumentParser(description='SQL Server Pipeline Monitoring Dashboard')

    parser.add_argument(
        '--output', '-o',
        default='dashboard.html',
        help='Output HTML file (default: dashboard.html)'
    )

    parser.add_argument(
        '--refresh',
        type=int,
        default=30,
        help='Page auto-refresh interval in seconds (default: 30)'
    )

    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuous monitoring (regenerate dashboard periodically)'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Update interval for continuous monitoring in seconds (default: 30)'
    )

    args = parser.parse_args()

    if args.continuous:
        continuous_monitoring(args.output, args.refresh, args.interval)
    else:
        generate_dashboard(args.output, args.refresh)


if __name__ == '__main__':
    main()
