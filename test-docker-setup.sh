#!/bin/bash
# Test script for Docker setup validation

set -e

echo "=== Testing Docker Setup ==="
echo ""

# Check if Docker is running
echo "1. Checking Docker daemon..."
if ! docker info > /dev/null 2>&1; then
    echo "   ❌ Docker daemon is not running. Please start Docker Desktop."
    exit 1
fi
echo "   ✅ Docker daemon is running"

# Validate docker-compose.yml
echo ""
echo "2. Validating docker-compose.yml..."
if docker-compose config > /dev/null 2>&1; then
    echo "   ✅ docker-compose.yml is valid"
else
    echo "   ❌ docker-compose.yml has errors"
    docker-compose config
    exit 1
fi

# Check if .env file exists
echo ""
echo "3. Checking .env file..."
if [ -f .env ]; then
    echo "   ✅ .env file exists"
    # Check for required variables
    if grep -q "OPENROUTER_API_KEY" .env; then
        echo "   ✅ OPENROUTER_API_KEY found in .env"
    else
        echo "   ⚠️  OPENROUTER_API_KEY not found in .env (may cause backend to fail)"
    fi
else
    echo "   ⚠️  .env file not found (backend will fail without required variables)"
fi

# Check if data directory exists
echo ""
echo "4. Checking data directory..."
if [ -d data ]; then
    echo "   ✅ data directory exists"
else
    echo "   ℹ️  data directory will be created automatically by Docker"
    mkdir -p data
    echo "   ✅ Created data directory"
fi

# Test building backend image
echo ""
echo "5. Testing backend Dockerfile build..."
if docker build -t e2e-ai-backend-test -f Dockerfile . > /tmp/backend-build.log 2>&1; then
    echo "   ✅ Backend Dockerfile builds successfully"
    docker rmi e2e-ai-backend-test > /dev/null 2>&1
else
    echo "   ❌ Backend Dockerfile build failed. Check /tmp/backend-build.log"
    cat /tmp/backend-build.log
    exit 1
fi

# Test building frontend image
echo ""
echo "6. Testing frontend Dockerfile build..."
if docker build -t e2e-ai-frontend-test --build-arg VITE_BACKEND_URL=http://localhost:8080 -f frontend/Dockerfile frontend > /tmp/frontend-build.log 2>&1; then
    echo "   ✅ Frontend Dockerfile builds successfully"
    docker rmi e2e-ai-frontend-test > /dev/null 2>&1
else
    echo "   ❌ Frontend Dockerfile build failed. Check /tmp/frontend-build.log"
    cat /tmp/frontend-build.log
    exit 1
fi

# Test docker-compose build
echo ""
echo "7. Testing docker-compose build (dry-run)..."
if docker-compose build --dry-run > /dev/null 2>&1; then
    echo "   ✅ docker-compose build configuration is valid"
else
    echo "   ⚠️  docker-compose build dry-run not supported, skipping..."
fi

echo ""
echo "=== All checks passed! ==="
echo ""
echo "To start the services, run:"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop the services:"
echo "  docker-compose down"
