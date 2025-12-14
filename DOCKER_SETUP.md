# Docker Setup Guide

This project includes Docker configuration for both the backend (FastAPI) and frontend (React/Vite) services.

## Files Created

1. **`Dockerfile`** - Backend Python/FastAPI service
2. **`frontend/Dockerfile`** - Frontend React/Vite application (multi-stage build)
3. **`docker-compose.yml`** - Orchestrates both services
4. **`test-docker-setup.ps1`** - PowerShell test script (Windows)
5. **`test-docker-setup.sh`** - Bash test script (Linux/Mac)

## Prerequisites

- Docker Desktop installed and running
- `.env` file in the project root with required environment variables (see `.env.example`)

## Quick Start

1. **Ensure Docker is running**
   ```powershell
   docker info
   ```

2. **Start all services**
   ```powershell
   docker-compose up -d
   ```

3. **View logs**
   ```powershell
   docker-compose logs -f
   ```

4. **Stop services**
   ```powershell
   docker-compose down
   ```

## Services

### Backend Service
- **Container name**: `e2e-ai-backend`
- **Port**: `8080:8080`
- **Health endpoint**: `http://localhost:8080/health/liveness`
- **Environment**: Loads from `.env` file
- **Database**: SQLite stored in `./data/tasks.db` (mounted volume)

### Frontend Service
- **Container name**: `e2e-ai-frontend`
- **Port**: `80:80`
- **URL**: `http://localhost`
- **Backend URL**: Configured via build arg `VITE_BACKEND_URL` (default: `http://localhost:8080`)

## Configuration

### Environment Variables

The backend service loads environment variables from the `.env` file. Required variables include:

- `OPENROUTER_API_KEY` - Required for LLM functionality
- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` - Optional, for Jira integration
- Other variables as defined in `src/core/config.py`

### CORS Configuration

The backend is configured to allow CORS from:
- `http://localhost:80`
- `http://127.0.0.1:80`

This can be overridden in the `.env` file via `BACKEND_CORS_ORIGINS`.

### Frontend Backend URL

The frontend's backend URL is set at build time via the `VITE_BACKEND_URL` build argument. Default is `http://localhost:8080`.

To change it, modify the `docker-compose.yml`:
```yaml
frontend:
  build:
    args:
      - VITE_BACKEND_URL=http://your-backend-url:8080
```

## Testing the Setup

Run the test script to validate the Docker configuration:

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File test-docker-setup.ps1
```

**Linux/Mac (Bash):**
```bash
chmod +x test-docker-setup.sh
./test-docker-setup.sh
```

## Building Images Separately

### Backend
```powershell
docker build -t e2e-ai-backend -f Dockerfile .
```

### Frontend
```powershell
docker build -t e2e-ai-frontend --build-arg VITE_BACKEND_URL=http://localhost:8080 -f frontend/Dockerfile frontend
```

## Troubleshooting

### Backend won't start
- Check that `.env` file exists and contains `OPENROUTER_API_KEY`
- Verify Docker has enough resources allocated
- Check logs: `docker-compose logs backend`

### Frontend can't connect to backend
- Verify backend is running: `docker-compose ps`
- Check backend logs for errors
- Ensure `VITE_BACKEND_URL` in docker-compose matches your setup
- Check browser console for CORS errors

### Database issues
- Ensure `./data` directory exists and is writable
- Check volume mount: `docker-compose exec backend ls -la /app/data`

### Health checks failing
- Backend: Verify `/health/liveness` endpoint is accessible
- Frontend: Ensure nginx is serving files correctly

## Development vs Production

This setup is suitable for development. For production, consider:

- Using environment-specific `.env` files
- Setting up proper SSL/TLS certificates
- Using a production-grade database (PostgreSQL, MySQL)
- Configuring proper logging and monitoring
- Setting resource limits in docker-compose
- Using Docker secrets for sensitive data

## Network

Both services are on the same Docker network (`e2e-ai-network`), allowing them to communicate using service names:
- Frontend can reach backend at `http://backend:8080` (internal)
- External access: Frontend at `http://localhost`, Backend at `http://localhost:8080`
