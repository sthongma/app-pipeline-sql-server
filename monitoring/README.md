# Monitoring Dashboard

Simple HTML-based monitoring dashboard for SQL Server Pipeline.

## Features

- Real-time system health status
- Database connection metrics
- Connection pool statistics
- Auto-refreshing dashboard
- Responsive design
- No external dependencies (pure HTML/CSS)

## Usage

### Generate Dashboard (One-time)

```bash
python monitoring/dashboard.py
```

This creates `dashboard.html` in the current directory.

### Generate with Custom Options

```bash
# Custom output file
python monitoring/dashboard.py --output monitoring/status.html

# Custom refresh interval (seconds)
python monitoring/dashboard.py --refresh 60
```

### Continuous Monitoring

```bash
# Regenerate dashboard every 30 seconds
python monitoring/dashboard.py --continuous

# Custom update interval
python monitoring/dashboard.py --continuous --interval 60
```

## Dashboard Metrics

### System Status
- Overall system health (Healthy/Degraded/Unhealthy)
- Component status breakdown
  - Application status
  - Database connectivity

### Database Metrics
- Response Time (milliseconds)
- Connection Pool Size
- Active Connections (Checked Out)
- Idle Connections (Checked In)
- Pool Overflow Count

## Status Indicators

- 🟢 **HEALTHY**: All systems operational, response < 1 second
- 🟡 **DEGRADED**: System slow, response 1-5 seconds
- 🔴 **UNHEALTHY**: System failure or response > 5 seconds
- ⚪ **UNKNOWN**: Status unavailable

## Integration

### Web Server

Serve dashboard with Python HTTP server:

```bash
# Generate dashboard
python monitoring/dashboard.py

# Serve on port 8000
python -m http.server 8000

# Open in browser
# http://localhost:8000/dashboard.html
```

### Scheduled Generation

**Windows Task Scheduler:**
```
Action: Start a program
Program: python
Arguments: C:\path\to\monitoring\dashboard.py --output C:\inetpub\wwwroot\status.html
```

**Linux Cron:**
```bash
# Regenerate every 5 minutes
*/5 * * * * cd /path/to/app && python monitoring/dashboard.py --output /var/www/html/status.html
```

### IIS Integration

1. Generate dashboard to IIS wwwroot:
   ```bash
   python monitoring/dashboard.py --output C:\inetpub\wwwroot\pipeline-status.html
   ```

2. Access via IIS:
   ```
   http://your-server/pipeline-status.html
   ```

3. Setup automatic regeneration (Task Scheduler)

## JSON Report

Dashboard also generates a JSON report (`dashboard.json`) with raw metrics:

```json
{
  "timestamp": "2025-10-29T10:30:00",
  "overall_status": "healthy",
  "components": {
    "application": {
      "status": "healthy",
      "details": {
        "message": "Application is running"
      }
    },
    "database": {
      "status": "healthy",
      "details": {
        "response_time_ms": 45.23,
        "pool_size": 5,
        "pool_checked_out": 1,
        "pool_checked_in": 4
      }
    }
  }
}
```

## Customization

### Custom Refresh Interval

```bash
# Refresh every 60 seconds
python monitoring/dashboard.py --refresh 60
```

### Custom Styling

Edit `dashboard.py` and modify the `HTML_TEMPLATE` variable to customize:
- Colors
- Layout
- Fonts
- Metrics displayed

### Additional Metrics

Add custom metrics by modifying the health check:

```python
# In utils/health_check.py
def check_application_health():
    details = {
        "timestamp": datetime.now().isoformat(),
        "status": HealthStatus.HEALTHY,
        "message": "Application is running",
        "custom_metric": get_custom_metric()  # Add your metric
    }
    return HealthStatus.HEALTHY, details
```

## Troubleshooting

**Dashboard shows "Unknown" status:**
- Check database configuration in `.env`
- Verify SQL Server is running
- Test connection with: `python -c "from config.database import DatabaseConfig; DatabaseConfig().update_engine()"`

**Dashboard not auto-refreshing:**
- Check browser allows meta refresh tags
- Try manual refresh (F5)
- Check HTML file has correct refresh meta tag

**Permission denied:**
- Ensure write permissions for output directory
- Try different output location: `--output ~/dashboard.html`

## Advanced Usage

### Multiple Environments

Monitor multiple environments:

```bash
# Production
python monitoring/dashboard.py --output prod-dashboard.html

# Staging
# (Change .env first)
python monitoring/dashboard.py --output staging-dashboard.html
```

### Alerting Integration

Parse JSON report for alerting:

```python
import json

with open('dashboard.json') as f:
    report = json.load(f)

if report['overall_status'] == 'unhealthy':
    send_alert("System unhealthy!")
```

### API Endpoint

Serve JSON as API:

```python
from flask import Flask, jsonify
import json

app = Flask(__name__)

@app.route('/health')
def health():
    with open('dashboard.json') as f:
        return jsonify(json.load(f))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Screenshots

Dashboard displays:
- **Header**: Application name and subtitle
- **System Status Card**: Overall status and component breakdown
- **Metrics Card**: Database performance metrics
- **Footer**: Version info and refresh indicator

## Best Practices

1. **Regular Updates**: Generate dashboard every 30-60 seconds
2. **Long-term Storage**: Archive JSON reports for historical analysis
3. **Alerting**: Set up alerts based on status changes
4. **Access Control**: Protect dashboard if exposed publicly
5. **Backup**: Keep dashboard generation script under version control

## Limitations

- Client-side only (no real-time updates without page refresh)
- Basic styling (can be enhanced with CSS frameworks)
- No historical trend graphs (use external tools like Grafana for that)
- No authentication (add web server authentication if needed)

## Future Enhancements

Possible improvements:
- [ ] WebSocket for real-time updates
- [ ] Historical trend charts
- [ ] Alert configuration UI
- [ ] Multiple dashboard themes
- [ ] Mobile app integration

---

**Last Updated:** 2025-10-29
**Version:** 1.0.0
