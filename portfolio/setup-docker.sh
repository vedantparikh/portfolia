#!/bin/bash

# Portfolia Docker Environment Validation Script
# This script validates your Docker and environment setup

set -e  # Exit on error

echo "🚀 Portfolia Docker Environment Validation"
echo "==========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Track if there are any errors
HAS_ERRORS=0

# Check if Docker is installed
echo "Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    HAS_ERRORS=1
else
    print_success "Docker is installed"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    HAS_ERRORS=1
else
    print_success "Docker Compose is installed"
fi

echo ""
echo "Checking environment files..."

# Check root .env file
if [ ! -f .env ]; then
    print_error ".env file is missing in root directory"
    print_info "Please create .env file. See .env.example for reference"
    HAS_ERRORS=1
else
    print_success "Root .env file exists"
    
    # Check required variables
    source .env 2>/dev/null || true
    
    if [ -z "$FRONTEND_PORT" ]; then
        print_warning "FRONTEND_PORT not set in .env"
    fi
    
    if [ -z "$API_PORT" ]; then
        print_warning "API_PORT not set in .env"
    fi
    
    if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
        print_error "PostgreSQL configuration incomplete in .env"
        HAS_ERRORS=1
    else
        print_success "PostgreSQL configuration found in .env"
    fi
    
    if [ -z "$REDIS_PORT" ]; then
        print_warning "REDIS_PORT not set in .env"
    fi
fi

# Check backend .env.docker file
if [ ! -f python/app/.env.docker ]; then
    print_error "python/app/.env.docker is missing"
    print_info "Please create this file. See python/app/.env.docker.example for reference"
    HAS_ERRORS=1
else
    print_success "Backend .env.docker file exists"
fi

# Check frontend .env.docker file
if [ ! -f js/.env.docker ]; then
    print_error "js/.env.docker is missing"
    print_info "Please create this file. See js/.env.docker.example for reference"
    HAS_ERRORS=1
else
    print_success "Frontend .env.docker file exists"
fi

echo ""
echo "Validating compose files..."

if docker compose -f compose.dev.yaml config -q && docker compose -f compose.yaml config -q; then
    print_success "compose.dev.yaml and compose.yaml are valid"
else
    print_error "compose files have errors"
    print_info "Run 'docker compose -f compose.dev.yaml config -q' to see details"
    HAS_ERRORS=1
fi

echo ""
echo "Security check..."

# Check for default passwords
if [ -f .env ]; then
    if grep -q "portfolia_password_change_in_production\|change_this_password" .env 2>/dev/null; then
        print_warning "Default database password detected in .env"
        print_info "Please change POSTGRES_PASSWORD for production use"
    fi
fi

if [ -f python/app/.env.docker ]; then
    if grep -q "change-this-secret-key\|change-this-jwt-secret" python/app/.env.docker 2>/dev/null; then
        print_warning "Default secret keys detected in python/app/.env.docker"
        print_info "Please change SECRET_KEY and JWT_SECRET_KEY for production use"
        print_info "Generate secure keys with: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
    fi
fi

echo ""
echo "==========================================="

if [ $HAS_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "You can now start the application with:"
    echo -e "${BLUE}  docker-compose up -d${NC}"
    echo ""
    echo "Access the application at:"
    echo "  - Frontend: http://localhost:${FRONTEND_PORT}"
    echo "  - API: http://localhost:${API_PORT}"
    echo "  - API Docs: http://localhost:${API_PORT}/docs"
    echo ""
    echo "To view logs:"
    echo -e "${BLUE}  docker-compose logs -f${NC}"
    exit 0
else
    echo -e "${RED}❌ Validation failed!${NC}"
    echo ""
    echo "Please fix the errors above before proceeding."
    echo ""
    echo "Reference files for creating missing .env files:"
    echo "  - .env.example (root directory)"
    echo "  - python/app/.env.docker.example"
    echo "  - js/.env.docker.example"
    exit 1
fi

