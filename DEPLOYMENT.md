# PortGuard CCMS v3 - Docker Deployment Guide

## Overview

This guide covers deploying PortGuard CCMS v3 to a staging environment using Docker, Docker Compose, and Nginx.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB+ RAM
- 10GB+ disk space
- OpenSSL (for generating secrets)

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP/HTTPS
       ▼
┌─────────────────┐
│     Nginx       │ (Port 80/443)
│  (Reverse Proxy)│
└────────┬────────┘
    ┌────┴────┬──────────┐
    │          │          │
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌─────────┐
│ Static │ │Uploads │ │FastAPI  │
│ Files  │ │ Volume │ │  (App)  │
└────────┘ └────────┘ └────┬────┘
                           │
                           ▼
                      ┌──────────┐
                      │PostgreSQL│
                      │   (DB)   │
                      └──────────┘
```

## Quick Start

### 1. Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit with your production values
nano .env

# Generate a strong secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Update SECRET_KEY in .env with the output
```

### 2. Build and Start Services

```bash
# Build Docker images
docker-compose -f docker-compose.staging.yml build

# Start all services
docker-compose -f docker-compose.staging.yml up -d

# View logs
docker-compose -f docker-compose.staging.yml logs -f
```

### 3. Seed Admin User

```bash
# Run inside the app container
docker-compose -f docker-compose.staging.yml exec app python seed_admin.py

# Or set custom credentials
docker-compose -f docker-compose.staging.yml exec app \
  env ADMIN_EMAIL="admin@yourdomain.com" \
  ADMIN_USERNAME="my_admin" \
  ADMIN_PASSWORD="MySecurePassword123!" \
  python seed_admin.py
```

### 4. Run Database Migrations (if needed)

```bash
# Access the database
docker-compose -f docker-compose.staging.yml exec db psql \
  -U portguard \
  -d portguard_db
```

### 5. Verify Deployment

```bash
# Check service health
docker-compose -f docker-compose.staging.yml ps

# Test API health endpoint
curl http://localhost/health

# Test static files
curl http://localhost/static/css/style.css
```

## Configuration Details

### Dockerfile

- **Based on**: python:3.11-slim
- **Installs**: Required system packages (gcc, postgresql-client)
- **Copies**: Application code and static files
- **Exposes**: Port 8000
- **Health Check**: Every 30s via /health endpoint

Key features:
- Multi-stage build support
- Static file directory with proper permissions
- Uploads directory creation
- Health check integration

### docker-compose.staging.yml

#### Services:

**db (PostgreSQL 15)**
- Volume: `postgres_data` for persistence
- Healthcheck: Validates database connectivity
- Network: `portguard_network`
- Start period: 10s (wait before app connects)

**app (FastAPI)**
- Build: Uses Dockerfile
- Environment: Database URL, JWT secrets, tokens
- Volumes:
  - `static_files`: Shared with Nginx (read-only for Nginx, read-write for app)
  - `uploads`: For storing file uploads
- Dependencies: Waits for DB health check
- Healthcheck: Every 30s via /health endpoint

**nginx (Nginx Alpine)**
- Ports: 80 (HTTP), 443 (HTTPS - if configured)
- Volumes:
  - `nginx.conf`: Main configuration (read-only)
  - `static_files`: Static assets (read-only)
  - `uploads`: User uploads (read-only)
- Depends on: app service
- Healthcheck: HTTP GET on /health

#### Volumes:
- `postgres_data`: Database files
- `static_files`: CSS, JS, images (shared)
- `uploads`: Multipart file uploads

### nginx.conf

**Key locations:**

1. `/health` - Docker healthcheck endpoint
2. `/static/` - Static assets with aggressive caching (30 days)
3. `/uploads/` - User uploads with moderate caching (7 days)
4. `/` - Proxy to FastAPI application

**Features:**
- Gzip compression for text assets
- Proper MIME types
- CORS headers for static files
- Request buffering optimization
- X-Forwarded headers for FastAPI to see real client IP
- Security: Denies access to hidden `.` files

## Security Considerations

### 1. Password Hashing

The deployment uses:
- **bcrypt**: 3.1.7 (with rounds=12)
- **passlib**: 1.7.4

This prevents the "password cannot be longer than 72 bytes" error by:
- Using bcrypt's native 72-byte handling properly
- Configuring passlib with explicit rounds parameter
- Hashing passwords client-side before transmission (if possible)

### 2. Secrets Management

**Never commit `.env` to version control:**

```bash
# Ensure .env is ignored
echo ".env" >> .gitignore
echo ".env.*.local" >> .gitignore

# Use .env.example as template
git add .env.example
```

**Generate strong credentials:**

```bash
# Secret key (for JWT)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Database password
openssl rand -base64 32

# Admin password
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

### 3. HTTPS in Production

To enable HTTPS with Let's Encrypt:

```bash
# Install certbot and Nginx plugin
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com

# Update nginx.conf with SSL configuration (see example below)
```

**SSL Example Addition to nginx.conf:**

```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Redirect HTTP to HTTPS
    if ($scheme != "https") {
        return 301 https://$server_name$request_uri;
    }
    
    # ... rest of configuration
}
```

### 4. Database Security

- PostgreSQL runs on internal network only (no external port exposure in production)
- Authentication required for all DB connections
- Database backups recommended
- Volume encryption recommended for `postgres_data`

## Troubleshooting

### Static Files Return 404

```bash
# Check if static volume is mounted
docker-compose -f docker-compose.staging.yml exec app ls -la /app/static/

# Check Nginx volume mount
docker-compose -f docker-compose.staging.yml exec nginx ls -la /app/static/

# Restart services to remount volumes
docker-compose -f docker-compose.staging.yml restart nginx
```

### Database Connection Error

```bash
# Check database service health
docker-compose -f docker-compose.staging.yml ps db

# View database logs
docker-compose -f docker-compose.staging.yml logs db

# Verify environment variables
docker-compose -f docker-compose.staging.yml exec app env | grep POSTGRES
```

### Password Hashing Error

```bash
# Verify bcrypt and passlib versions
docker-compose -f docker-compose.staging.yml exec app pip list | grep -E "bcrypt|passlib"

# Should show:
# bcrypt                    3.1.7
# passlib                   1.7.4
```

### Application Won't Start

```bash
# View application logs
docker-compose -f docker-compose.staging.yml logs -f app

# Common issues:
# - Database not ready (wait for healthcheck)
# - Import errors (missing dependencies)
# - Configuration errors (check .env file)
```

## Monitoring and Maintenance

### View Logs

```bash
# All services
docker-compose -f docker-compose.staging.yml logs

# Specific service
docker-compose -f docker-compose.staging.yml logs app
docker-compose -f docker-compose.staging.yml logs db
docker-compose -f docker-compose.staging.yml logs nginx

# Follow logs in real-time
docker-compose -f docker-compose.staging.yml logs -f

# View last 100 lines
docker-compose -f docker-compose.staging.yml logs --tail=100
```

### CPU and Memory Usage

```bash
docker stats
```

### Database Backup

```bash
# Create backup
docker-compose -f docker-compose.staging.yml exec db pg_dump \
  -U portguard portguard_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker-compose -f docker-compose.staging.yml exec -T db psql \
  -U portguard portguard_db < backup_20260217_120000.sql
```

### Clean Up

```bash
# Stop services
docker-compose -f docker-compose.staging.yml down

# Remove containers and volumes (WARNING: deletes data)
docker-compose -f docker-compose.staging.yml down -v

# Prune unused images and volumes
docker system prune -a --volumes
```

## Deployment Checklist

- [ ] `.env` file created with production values
- [ ] `SECRET_KEY` is securely generated
- [ ] Database credentials are strong (3+ special chars)
- [ ] Admin user created via `seed_admin.py`
- [ ] Static files accessible via `/static/`
- [ ] API responds to `/health` endpoint
- [ ] All services show "healthy" in `docker-compose ps`
- [ ] Database backup created before going live
- [ ] Nginx logs monitored for errors
- [ ] HTTPS configured (recommended for production)

## Further Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## Support

For issues or questions:
1. Check logs: `docker-compose -f docker-compose.staging.yml logs`
2. Review this deployment guide
3. Check application error messages
4. Verify environment configuration
