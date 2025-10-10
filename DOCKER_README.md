# NH Outreach Agent - Docker Compose Setup

This project includes Docker Compose configuration for easy local development and deployment.

## Services

The Docker Compose setup includes the following services:

- **app**: Main FastAPI application (Port 8000)
- **postgres**: PostgreSQL database (Port 5432)
- **redis**: Redis server for Celery task queue (Port 6379)
- **celery-worker**: Celery worker for background tasks
- **flower**: Celery monitoring dashboard (Port 5555)

## Quick Start

1. **Clone the repository and navigate to the project directory:**
   ```bash
   cd NH_Outreach_Agent
   ```

2. **Set up environment variables:**
   ```bash
   # Copy the example environment file
   cp .env.docker .env
   
   # Edit .env file and add your API keys and configuration
   nano .env
   ```

3. **Build and start all services:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - **FastAPI Application**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **Celery Flower Dashboard**: http://localhost:5555

## Environment Configuration

Edit the `.env` file to configure your application:

```env
# Database (automatically configured for Docker)
DATABASE_URL=postgresql://nh_outreach_user:nh_outreach_password@postgres:5432/nh_outreach_db
REDIS_URL=redis://redis:6379/0

# Add your API keys
GROQ_API_KEY=your_groq_api_key
SENDGRID_API_KEY=your_sendgrid_api_key
SECRET_KEY=your_secret_key
GHL_API_KEY=your_ghl_api_key
```

## Docker Compose Commands

### Start services in background:
```bash
docker-compose up -d
```

### View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f celery-worker
```

### Stop services:
```bash
docker-compose down
```

### Stop and remove volumes (WARNING: This will delete your database data):
```bash
docker-compose down -v
```

### Rebuild services:
```bash
docker-compose up --build
```

### Scale Celery workers:
```bash
docker-compose up --scale celery-worker=3
```

## Database Management

### Access PostgreSQL database:
```bash
docker-compose exec postgres psql -U nh_outreach_user -d nh_outreach_db
```

### Backup database:
```bash
docker-compose exec postgres pg_dump -U nh_outreach_user nh_outreach_db > backup.sql
```

### Restore database:
```bash
docker-compose exec -T postgres psql -U nh_outreach_user -d nh_outreach_db < backup.sql
```

## Troubleshooting

### Check service status:
```bash
docker-compose ps
```

### View resource usage:
```bash
docker-compose top
```

### Restart a specific service:
```bash
docker-compose restart app
```

### Access container shell:
```bash
docker-compose exec app bash
```

### Clear Docker cache (if builds are failing):
```bash
docker system prune -f
docker-compose build --no-cache
```

## Production Considerations

For production deployment, consider:

1. **Use environment-specific compose files:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
   ```

2. **Secure your database:**
   - Change default passwords
   - Use Docker secrets for sensitive data
   - Limit database access

3. **Use external databases:**
   - Consider managed PostgreSQL and Redis services
   - Update connection strings accordingly

4. **Add monitoring:**
   - Health checks
   - Log aggregation
   - Performance monitoring

5. **SSL/TLS:**
   - Add reverse proxy (nginx)
   - Configure SSL certificates

## Data Persistence

The following data is persisted in Docker volumes:
- **postgres_data**: PostgreSQL database files
- **redis_data**: Redis persistence files

These volumes will persist even when containers are stopped and restarted.