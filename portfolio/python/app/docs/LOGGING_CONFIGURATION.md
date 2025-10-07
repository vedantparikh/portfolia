# Logging Configuration Guide

## Overview

The Portfolia API now includes comprehensive logging throughout the application, providing detailed insights into API requests, database operations, security events, and performance metrics.

## Features

### 🎨 **Colored Console Output**
- **DEBUG**: Cyan
- **INFO**: Green  
- **WARNING**: Yellow
- **ERROR**: Red
- **CRITICAL**: Magenta

### 📁 **File Logging with Rotation**
- Automatic log file creation with timestamps
- Configurable file size limits (default: 10MB)
- Automatic backup rotation (default: 5 files)
- UTF-8 encoding support

### 📊 **Structured Logging**
- Function call logging with parameters
- Database operation tracking
- API request/response logging
- Security event monitoring
- Performance metrics
- Error context logging

## Configuration

### Environment Variables

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log file name (optional, auto-generated if not provided)
LOG_FILE=portfolia_api.log

# Log directory (default: logs)
LOG_DIR=logs

# Enable JSON format (default: false)
LOG_JSON=false
```

### Python Configuration

```python
from core.logging_config import setup_logging

# Basic setup
setup_logging()

# Custom setup
setup_logging(
    log_level="DEBUG",
    log_file="custom.log",
    log_dir="custom_logs",
    enable_console=True,
    enable_file=True,
    enable_json=True,
    max_file_size=20*1024*1024,  # 20MB
    backup_count=10
)
```

## Usage Examples

### Getting a Logger

```python
from core.logging_config import get_logger

logger = get_logger(__name__)
logger.info("Application started")
logger.debug("Debug information")
logger.warning("Warning message")
logger.error("Error occurred")
```

### Function Call Logging

```python
from core.logging_config import log_function_call, log_function_result
import time

def process_data(data, user_id):
    start_time = time.time()
    
    # Log function call
    log_function_call(logger, "process_data", data_type=type(data).__name__, user_id=user_id)
    
    # Process data...
    result = do_something(data)
    
    # Log function result
    execution_time = time.time() - start_time
    log_function_result(logger, "process_data", result, execution_time)
    
    return result
```

### Database Operation Logging

```python
from core.logging_config import log_database_operation

# Log database operations
log_database_operation(logger, "SELECT", "users", user_id, email=email)
log_database_operation(logger, "INSERT", "users", new_user_id, username=username)
log_database_operation(logger, "UPDATE", "users", user_id, field="email")
log_database_operation(logger, "DELETE", "sessions", session_id)
```

### API Request/Response Logging

```python
from core.logging_config import log_api_request, log_api_response
import time

@app.get("/api/data")
async def get_data(request: Request, user_id: str = None):
    start_time = time.time()
    client_ip = get_client_ip(request)
    
    # Log request
    log_api_request(logger, "GET", "/api/data", user_id, client_ip, query="data")
    
    # Process request...
    data = fetch_data()
    
    # Log response
    response_time = time.time() - start_time
    log_api_response(logger, "GET", "/api/data", 200, response_time, data_size=len(data))
    
    return data
```

### Security Event Logging

```python
from core.logging_config import log_security_event

# Log security events
log_security_event(logger, "LOGIN_ATTEMPT", user_id, client_ip, "Failed password")
log_security_event(logger, "RATE_LIMIT_EXCEEDED", None, client_ip, "API endpoint")
log_security_event(logger, "SUSPICIOUS_ACTIVITY", user_id, client_ip, "Multiple failed logins")
```

### Performance Metrics

```python
from core.logging_config import log_performance_metric

# Log performance metrics
log_performance_metric(logger, "database_query_time", 0.125, "seconds", table="users")
log_performance_metric(logger, "api_response_time", 45.2, "milliseconds", endpoint="/api/data")
log_performance_metric(logger, "memory_usage", 128.5, "MB", component="data_processor")
```

### Error Logging with Context

```python
from core.logging_config import log_error_with_context

try:
    # Some operation
    result = risky_operation()
except Exception as e:
    # Log error with context
    log_error_with_context(
        logger, 
        e, 
        "Data processing operation", 
        user_id=user_id, 
        data_id=data_id,
        operation_type="transform"
    )
    raise
```

## Log Formats

### Detailed Format (Default)
```
2024-01-15 10:30:45,123 - core.auth.router - INFO - register_user:45 - 👤 User registration initiated | Email: user@example.com | Username: testuser | IP: 192.168.1.100
```

### JSON Format
```json
{
  "timestamp": "2024-01-15 10:30:45,123",
  "logger": "core.auth.router",
  "level": "INFO",
  "function": "register_user",
  "line": 45,
  "message": "👤 User registration initiated | Email: user@example.com | Username: testuser | IP: 192.168.1.100"
}
```

## Log Levels

### DEBUG
- Function calls and parameters
- Database query details
- Internal state information
- Performance measurements

### INFO
- API requests and responses
- Database operations
- User actions
- Application state changes

### WARNING
- Security events
- Rate limiting
- Deprecated feature usage
- Performance degradation

### ERROR
- Exceptions and errors
- Failed operations
- System failures
- Critical issues

### CRITICAL
- System crashes
- Data corruption
- Security breaches
- Unrecoverable errors

## Best Practices

### 1. **Use Appropriate Log Levels**
- DEBUG: Detailed debugging information
- INFO: General application flow
- WARNING: Potential issues
- ERROR: Actual errors
- CRITICAL: System-breaking issues

### 2. **Include Relevant Context**
```python
# Good
logger.info(f"User {user_id} updated profile | Fields: {updated_fields} | IP: {client_ip}")

# Avoid
logger.info("Profile updated")
```

### 3. **Use Structured Logging Functions**
```python
# Use the provided logging functions
log_api_request(logger, "GET", "/api/users", user_id, client_ip)
log_database_operation(logger, "SELECT", "users", user_id)

# Instead of manual formatting
logger.info(f"API GET /api/users | User: {user_id} | IP: {client_ip}")
```

### 4. **Filter Sensitive Information**
The logging system automatically filters sensitive parameters:
- `password`
- `password_hash`
- `token`
- `api_key`
- `secret`

### 5. **Performance Considerations**
- Use DEBUG level sparingly in production
- Avoid logging in tight loops
- Use lazy evaluation for expensive operations

## Monitoring and Analysis

### Log File Locations
- **Console**: Real-time output with colors
- **Files**: `logs/` directory (configurable)
- **Rotation**: Automatic based on size and count

### Log Analysis Tools
- **grep**: Search for specific patterns
- **awk**: Parse and analyze log data
- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Splunk**: Enterprise log management
- **Custom scripts**: Python, bash, etc.

### Example Analysis Commands
```bash
# Count errors by type
grep "ERROR" logs/portfolia_api.log | awk '{print $8}' | sort | uniq -c

# Find slow API responses
grep "API.*took" logs/portfolia_api.log | awk '$NF > 1.0 {print $0}'

# Monitor security events
grep "SECURITY" logs/portfolia_api.log | tail -f
```

## Troubleshooting

### Common Issues

1. **Logs not appearing**
   - Check LOG_LEVEL environment variable
   - Verify log directory permissions
   - Check console output

2. **Performance impact**
   - Reduce log level in production
   - Use async logging for high-volume operations
   - Monitor log file sizes

3. **Missing context**
   - Ensure all logging calls include relevant parameters
   - Use structured logging functions
   - Check function parameter types

### Debug Mode
Enable debug logging to see detailed information:
```bash
export LOG_LEVEL=DEBUG
python -m app.main
```

## Migration from Basic Logging

If you're migrating from basic `logging.basicConfig()`:

1. **Replace logger creation**
```python
# Old
import logging
logger = logging.getLogger(__name__)

# New
from core.logging_config import get_logger
logger = get_logger(__name__)
```

2. **Use structured logging functions**
```python
# Old
logger.info(f"User {user_id} logged in from {ip}")

# New
log_api_request(logger, "POST", "/login", user_id, ip)
```

3. **Update environment variables**
```bash
# Add to your .env file
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_JSON=false
```

## Future Enhancements

- **Elasticsearch integration** for centralized logging
- **Log aggregation** across multiple services
- **Real-time monitoring** and alerting
- **Custom log formatters** for different outputs
- **Log compression** and archival
- **Performance impact monitoring**
