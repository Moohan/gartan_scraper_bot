# Docker Compose Configuration Guide

This project uses a unified `docker-compose.yml` configuration with environment-specific overrides for different deployment scenarios.

## Configuration Files

### 🏠 **docker-compose.yml** (Base Configuration)
- **Purpose**: Main configuration used by all environments
- **Features**: 
  - Environment variable driven (configurable via `.env`)
  - Health checks using root endpoint `/`
  - Proper user permissions for volume mounts
  - JSON file logging with rotation

### 🛠️ **docker-compose.dev.yml** (Development Override)
- **Purpose**: Development-specific settings
- **Usage**: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`
- **Features**:
  - Hot-reload by mounting source code
  - Development Flask environment
  - No automatic restart (for debugging)

### 🚀 **docker-compose.production.yml** (Production Override)
- **Purpose**: Production hardening
- **Usage**: `docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d`
- **Features**:
  - Production Flask environment
  - Automatic restart policy
  - Optimized for stability

## Environment Configuration

### 📝 **.env Files**

#### **Local Development (.env)**
```bash
# Basic configuration for local development
GARTAN_USERNAME=your_username
GARTAN_PASSWORD=your_password
PORT=5000
FLASK_ENV=development
FLASK_DEBUG=true
```

#### **Raspberry Pi Deployment (.env.pi.example → .env)**
```bash
# Pi-specific configuration with custom paths
GARTAN_USERNAME=your_username
GARTAN_PASSWORD=your_password
PORT=5000
USER_ID=1000
GROUP_ID=1000

# Pi-specific storage paths
DATA_PATH=/media/elements/gartan/data
CACHE_PATH=/media/elements/gartan/cache
LOGS_PATH=/media/elements/gartan/logs

# Production settings
DOCKER_IMAGE=jamesmcmahon0/gartan_scraper_bot:latest
FLASK_ENV=production
FLASK_DEBUG=false
```

## Deployment Scenarios

### 🏠 **Local Development**
```bash
# 1. Copy example environment
cp .env.example .env

# 2. Edit credentials
nano .env

# 3. Start with development settings
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 🐧 **Raspberry Pi Deployment**
```bash
# 1. Use automated script (recommended)
./deploy_to_pi.sh

# 2. Manual deployment
scp docker-compose.yml pi@your-pi:/home/pi/gartan/
scp .env.pi.example pi@your-pi:/home/pi/gartan/.env
ssh pi@your-pi "cd gartan && docker-compose up -d"
```

### ☁️ **Production Server**
```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with production values

# 2. Deploy with production overrides
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d

# 3. Monitor health
curl http://localhost:5000/health
```

## Volume Management

### 🎯 **Default (Docker Volumes)**
- Uses named Docker volumes (`gartan_data`, `gartan_cache`, `gartan_logs`)
- Good for: Local development, simple deployments
- Data location: Docker's volume directory

### 📁 **Custom Host Paths**
- Override with environment variables (`DATA_PATH`, `CACHE_PATH`, `LOGS_PATH`)
- Good for: Production deployments, external storage, backups
- Data location: Your specified directories

### 🔧 **Examples**

#### Local with Docker Volumes
```bash
# Uses gartan_data, gartan_cache, gartan_logs volumes
docker-compose up -d
```

#### Pi with Custom Paths
```bash
# Set in .env:
DATA_PATH=/media/elements/gartan/data
CACHE_PATH=/media/elements/gartan/cache
LOGS_PATH=/media/elements/gartan/logs

docker-compose up -d
```

## Health Monitoring

### 🏥 **Built-in Health Check**
- **Endpoint**: `http://localhost:5000/`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Start Period**: 60 seconds (allows startup time)

### 📊 **Manual Health Check**
```bash
# Check container health
docker-compose ps

# Check application health
curl http://localhost:5000/health

# View logs
docker-compose logs -f
```

## Troubleshooting

### 🔍 **Common Issues**

#### **Permission Errors**
```bash
# Fix: Set correct user/group in .env
USER_ID=1000
GROUP_ID=1000
```

#### **Port Conflicts**
```bash
# Fix: Change port in .env
PORT=5001
```

#### **Database Path Issues**
```bash
# Fix: Ensure DATA_PATH exists and is writable
sudo mkdir -p /your/data/path
sudo chown 1000:1000 /your/data/path
```

#### **Image Pull Failures**
```bash
# Fix: Check image name in .env
DOCKER_IMAGE=jamesmcmahon0/gartan_scraper_bot:latest
```

### 🔧 **Debug Commands**
```bash
# View environment variables
docker-compose config

# Check container status
docker-compose ps

# View logs
docker-compose logs --tail=50

# Interactive shell
docker-compose exec gartan-scraper bash

# Restart services
docker-compose restart
```

## Migration from Old Setup

### 📦 **Old Files → New Structure**

- ❌ `docker-compose.prod.yml` → ✅ `docker-compose.production.yml`
- ❌ `deploy/pi-docker-compose.yml` → ✅ `docker-compose.yml` + `.env`
- ❌ Hardcoded paths → ✅ Environment variables

### 🔄 **Migration Steps**

1. **Update deployment scripts**:
   ```bash
   # Old
   docker-compose -f docker-compose.prod.yml up -d
   
   # New
   docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d
   ```

2. **Convert environment configuration**:
   ```bash
   # Create .env from old hardcoded values
   echo "DATA_PATH=/media/elements/gartan/data" >> .env
   ```

3. **Test new configuration**:
   ```bash
   docker-compose config  # Verify configuration
   docker-compose up -d   # Deploy with new setup
   ```

## Best Practices

### ✅ **Do**
- Use `.env` files for environment-specific configuration
- Set proper user permissions for volume mounts
- Use health checks for monitoring
- Keep credentials in `.env` (never commit to git)
- Use override files for environment-specific settings

### ❌ **Don't**
- Hardcode paths in docker-compose files
- Commit `.env` files to version control
- Run containers as root in production
- Skip health checks in production deployments
- Mix environment settings in the same file
