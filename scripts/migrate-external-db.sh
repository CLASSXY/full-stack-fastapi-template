#!/bin/bash

# Database migration script for external PostgreSQL

set -e

ENV_FILE=".env.production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    if [ ! -f "$ENV_FILE" ]; then
        print_error "$ENV_FILE file not found!"
        exit 1
    fi
    
    # Load environment variables
    source $ENV_FILE
    
    if [ -z "$POSTGRES_SERVER" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
        print_error "Database configuration incomplete in $ENV_FILE"
        exit 1
    fi
}

test_connection() {
    print_status "Testing database connection..."
    
    source $ENV_FILE
    
    # Test connection using docker
    if docker run --rm \
        -e PGPASSWORD="$POSTGRES_PASSWORD" \
        postgres:17 \
        psql -h "$POSTGRES_SERVER" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -c "SELECT version();" > /dev/null 2>&1; then
        print_success "Database connection successful!"
    else
        print_error "Failed to connect to database!"
        print_warning "Please check your database configuration in $ENV_FILE"
        exit 1
    fi
}

run_migrations() {
    print_status "Running database migrations..."
    
    # Copy production env file
    cp $ENV_FILE .env
    
    # Build backend image if it doesn't exist
    if ! docker images | grep -q "backend"; then
        print_status "Building backend image..."
        docker compose -f docker-compose.backend.yml build backend
    fi
    
    # Run migrations using the backend container
    docker run --rm \
        --env-file .env \
        -v "$(pwd)/backend:/app" \
        -w /app \
        $(docker images --format "table {{.Repository}}:{{.Tag}}" | grep backend | head -1) \
        alembic upgrade head
    
    print_success "Database migrations completed!"
}

create_initial_data() {
    print_status "Creating initial data..."
    
    # Copy production env file
    cp $ENV_FILE .env
    
    # Run initial data script
    docker run --rm \
        --env-file .env \
        -v "$(pwd)/backend:/app" \
        -w /app \
        $(docker images --format "table {{.Repository}}:{{.Tag}}" | grep backend | head -1) \
        python app/initial_data.py
    
    print_success "Initial data created!"
}

show_migration_status() {
    print_status "Checking migration status..."
    
    cp $ENV_FILE .env
    
    docker run --rm \
        --env-file .env \
        -v "$(pwd)/backend:/app" \
        -w /app \
        $(docker images --format "table {{.Repository}}:{{.Tag}}" | grep backend | head -1) \
        alembic current
}

case "$1" in
    "test")
        check_requirements
        test_connection
        ;;
    "migrate")
        check_requirements
        test_connection
        run_migrations
        ;;
    "init-data")
        check_requirements
        test_connection
        create_initial_data
        ;;
    "status")
        check_requirements
        show_migration_status
        ;;
    "full-setup")
        check_requirements
        test_connection
        run_migrations
        create_initial_data
        print_success "Database setup completed!"
        ;;
    *)
        echo "Usage: $0 {test|migrate|init-data|status|full-setup}"
        echo ""
        echo "Commands:"
        echo "  test      - Test database connection"
        echo "  migrate   - Run database migrations"
        echo "  init-data - Create initial data (superuser, etc.)"
        echo "  status    - Show current migration status"
        echo "  full-setup - Run migrations and create initial data"
        exit 1
        ;;
esac