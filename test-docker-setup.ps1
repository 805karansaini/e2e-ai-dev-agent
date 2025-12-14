# PowerShell test script for Docker setup validation

Write-Host "=== Testing Docker Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "1. Checking Docker daemon..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "   ✅ Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Docker daemon is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Validate docker-compose.yml
Write-Host ""
Write-Host "2. Validating docker-compose.yml..." -ForegroundColor Yellow
try {
    docker-compose config | Out-Null
    Write-Host "   ✅ docker-compose.yml is valid" -ForegroundColor Green
} catch {
    Write-Host "   ❌ docker-compose.yml has errors" -ForegroundColor Red
    docker-compose config
    exit 1
}

# Check if .env file exists
Write-Host ""
Write-Host "3. Checking .env file..." -ForegroundColor Yellow
if (Test-Path .env) {
    Write-Host "   ✅ .env file exists" -ForegroundColor Green
    $envContent = Get-Content .env -Raw
    if ($envContent -match "OPENROUTER_API_KEY") {
        Write-Host "   ✅ OPENROUTER_API_KEY found in .env" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  OPENROUTER_API_KEY not found in .env (may cause backend to fail)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️  .env file not found (backend will fail without required variables)" -ForegroundColor Yellow
}

# Check if data directory exists
Write-Host ""
Write-Host "4. Checking data directory..." -ForegroundColor Yellow
if (Test-Path data) {
    Write-Host "   ✅ data directory exists" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  data directory will be created automatically by Docker" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path data | Out-Null
    Write-Host "   ✅ Created data directory" -ForegroundColor Green
}

# Test building backend image
Write-Host ""
Write-Host "5. Testing backend Dockerfile build..." -ForegroundColor Yellow
try {
    docker build -t e2e-ai-backend-test -f Dockerfile . 2>&1 | Out-Null
    Write-Host "   ✅ Backend Dockerfile builds successfully" -ForegroundColor Green
    docker rmi e2e-ai-backend-test 2>&1 | Out-Null
} catch {
    Write-Host "   ❌ Backend Dockerfile build failed" -ForegroundColor Red
    exit 1
}

# Test building frontend image
Write-Host ""
Write-Host "6. Testing frontend Dockerfile build..." -ForegroundColor Yellow
try {
    docker build -t e2e-ai-frontend-test --build-arg VITE_BACKEND_URL=http://localhost:8080 -f frontend/Dockerfile frontend 2>&1 | Out-Null
    Write-Host "   ✅ Frontend Dockerfile builds successfully" -ForegroundColor Green
    docker rmi e2e-ai-frontend-test 2>&1 | Out-Null
} catch {
    Write-Host "   ❌ Frontend Dockerfile build failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== All checks passed! ===" -ForegroundColor Green
Write-Host ""
Write-Host "To start the services, run:" -ForegroundColor Cyan
Write-Host "  docker-compose up -d"
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Cyan
Write-Host "  docker-compose logs -f"
Write-Host ""
Write-Host "To stop the services:" -ForegroundColor Cyan
Write-Host "  docker-compose down"
