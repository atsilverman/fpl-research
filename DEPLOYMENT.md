# FPL Data Service - Production Deployment

## Overview

The FPL Data Service is a unified Python service that monitors Fantasy Premier League data changes and automatically refreshes your Supabase database when needed. It's designed to run continuously on a server without manual intervention.

## Service Features

- **Intelligent Monitoring**: Checks for data changes every hour
- **Automatic Refresh**: Only refreshes data when changes are detected
- **Robust Error Handling**: Continues running even if individual operations fail
- **State Persistence**: Remembers previous state to detect changes
- **Comprehensive Logging**: Detailed logs for monitoring and troubleshooting

## Server Requirements

- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **Python**: 3.8 or higher
- **Memory**: 512MB RAM minimum (1GB recommended)
- **Storage**: 1GB free space
- **Network**: Internet access for FPL API and Supabase

## Quick Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Create application directory
sudo mkdir -p /opt/fpl-service
sudo chown $USER:$USER /opt/fpl-service
cd /opt/fpl-service
```

### 2. Application Setup

```bash
# Clone or upload your code
# (Upload fpl_service.py, requirements.txt, and supabase_migrations/)

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test the service
python3 fpl_service.py --test
```

### 3. Service Configuration

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/fpl-service.service
```

Add this content:

```ini
[Unit]
Description=FPL Data Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/fpl-service
Environment=PATH=/opt/fpl-service/venv/bin
ExecStart=/opt/fpl-service/venv/bin/python fpl_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 4. Start the Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable fpl-service

# Start the service
sudo systemctl start fpl-service

# Check status
sudo systemctl status fpl-service
```

## Service Management

### Basic Commands

```bash
# Start service
sudo systemctl start fpl-service

# Stop service
sudo systemctl stop fpl-service

# Restart service
sudo systemctl restart fpl-service

# Check status
sudo systemctl status fpl-service

# View logs
sudo journalctl -u fpl-service -f
```

### Service Logs

```bash
# View recent logs
sudo journalctl -u fpl-service -n 50

# Follow logs in real-time
sudo journalctl -u fpl-service -f

# View logs from today
sudo journalctl -u fpl-service --since today
```

## Monitoring

### Health Checks

The service provides several ways to check its health:

```bash
# Test connections only
python3 fpl_service.py --test

# Check once and exit
python3 fpl_service.py --once

# Force immediate refresh
python3 fpl_service.py --refresh
```

### Log Monitoring

Key log messages to watch for:

- `✅ FPL API connection successful` - API connectivity
- `✅ Supabase connection successful` - Database connectivity
- `Changes detected, performing refresh...` - Data refresh triggered
- `Complete data refresh finished successfully` - Refresh completed
- `No changes detected, no refresh needed` - Normal operation

### Troubleshooting

#### Service Won't Start

```bash
# Check service status
sudo systemctl status fpl-service

# Check logs for errors
sudo journalctl -u fpl-service -n 20

# Test manually
cd /opt/fpl-service
source venv/bin/activate
python3 fpl_service.py --test
```

#### API Connection Issues

```bash
# Test FPL API
curl -s "https://fantasy.premierleague.com/api/bootstrap-static/" | head

# Test Supabase (replace with your URL)
curl -s "https://your-project.supabase.co/rest/v1/teams?select=count" \
  -H "apikey: YOUR_API_KEY"
```

#### Database Issues

```bash
# Check Supabase project status
# Verify API keys are correct
# Check database schema matches migrations
```

## Advanced Configuration

### Custom Check Interval

To change the check interval from 1 hour to 30 minutes:

```python
# Edit fpl_service.py
self.check_interval = 1800  # 30 minutes in seconds
```

### Log Rotation

Create logrotate configuration:

```bash
sudo nano /etc/logrotate.d/fpl-service
```

Add:

```
/opt/fpl-service/fpl_service.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 ubuntu ubuntu
}
```

### Resource Monitoring

Monitor service resource usage:

```bash
# Check memory usage
ps aux | grep fpl_service

# Monitor system resources
htop

# Check disk usage
df -h /opt/fpl-service
```

## Backup and Recovery

### State File Backup

The service maintains state in `service_state.json`. Backup this file:

```bash
# Create backup
cp /opt/fpl-service/service_state.json /opt/fpl-service/service_state.json.backup

# Restore if needed
cp /opt/fpl-service/service_state.json.backup /opt/fpl-service/service_state.json
```

### Database Backup

Ensure your Supabase database has regular backups configured through the Supabase dashboard.

## Security Considerations

1. **API Keys**: Store Supabase credentials securely
2. **File Permissions**: Ensure service files are not world-readable
3. **Network Security**: Use firewall rules to restrict access
4. **Updates**: Keep the system and Python packages updated

## Performance Optimization

1. **Memory**: Monitor memory usage, restart if needed
2. **CPU**: Service is lightweight, minimal CPU impact
3. **Network**: Service respects FPL API rate limits
4. **Database**: Optimize Supabase queries if needed

## Expected Behavior

### Normal Operation

- Service runs continuously
- Checks for changes every hour
- Logs "No changes detected" when data is up-to-date
- Automatically refreshes when changes are detected

### During Data Changes

- Detects new finished gameweeks
- Detects new fixtures
- Detects gameweek transitions
- Performs complete data refresh
- Updates state file

### Error Handling

- Continues running if individual operations fail
- Logs errors for troubleshooting
- Retries on next check interval
- Maintains service state

## Support

For issues or questions:

1. Check service logs: `sudo journalctl -u fpl-service -f`
2. Test connections: `python3 fpl_service.py --test`
3. Review this documentation
4. Check Supabase project status
5. Verify FPL API availability
