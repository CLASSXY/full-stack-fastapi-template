#!/bin/bash

# Backend-only deployment management script

set -e

COMPOSE_FILE="docker-compose.backend.yml"
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
    print_status "Checking requirements..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed!"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        print_error "Docker Compose is not installed!"
        exit 1
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        print_error "$ENV_FILE file not found!"
        print_warning "Please create $ENV_FILE with your production settings."
        exit 1
    fi
    
    print_success "All requirements met!"
}

deploy() {
    print_status "Starting backend deployment..."
    
    # Copy production env file
    cp $ENV_FILE .env
    
    # Build and start services
    print_status "Building backend image..."
    docker compose -f $COMPOSE_FILE build backend
    
    print_status "Starting services..."
    docker compose -f $COMPOSE_FILE up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check health
    if docker compose -f $COMPOSE_FILE ps | grep -q "healthy\|Up"; then
        print_success "Backend deployment successful!"
        show_urls
    else
        print_error "Deployment failed. Checking logs..."
        docker compose -f $COMPOSE_FILE logs backend
        exit 1
    fi
}

show_status() {
    print_status "Current service status:"
    docker compose -f $COMPOSE_FILE ps
}

show_logs() {
    print_status "Showing backend logs..."
    docker compose -f $COMPOSE_FILE logs -f backend
}

show_urls() {
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo ""
    print_success "Deployment completed successfully!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Service URLs:"
    echo "   Backend API: http://$SERVER_IP:9102"
    echo "   API Documentation: http://$SERVER_IP:9102/docs"
    echo "   Health Check: http://$SERVER_IP:9102/api/v1/utils/health-check/"
    echo ""
    echo "🔧 Management Commands:"
    echo "   View logs: ./scripts/backend-only-deploy.sh logs"
    echo "   Check status: ./scripts/backend-only-deploy.sh status"
    echo "   Restart: ./scripts/backend-only-deploy.sh restart"
    echo "   Stop: ./scripts/backend-only-deploy.sh stop"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

restart_services() {
    print_status "Restarting services..."
    docker compose -f $COMPOSE_FILE restart
    print_success "Services restarted!"
}

stop_services() {
    print_status "Stopping services..."
    docker compose -f $COMPOSE_FILE down
    print_success "Services stopped!"
}

update_deployment() {
    print_status "Updating deployment..."
    
    # Pull latest changes (if using git)
    if [ -d ".git" ]; then
        print_status "Pulling latest changes..."
        git pull
    fi
    
    # Rebuild and restart
    cp $ENV_FILE .env
    docker compose -f $COMPOSE_FILE build backend
    docker compose -f $COMPOSE_FILE up -d
    
    print_success "Deployment updated!"
    show_urls
}

backup_database() {
    print_status "Creating database backup..."
    
    # Load environment variables
    source $ENV_FILE
    
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # Create backup using pg_dump
    docker run --rm \
        -e PGPASSWORD="$POSTGRES_PASSWORD" \
        postgres:17 \
        pg_dump -h "$POSTGRES_SERVER" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        > "$BACKUP_FILE"
    
    print_success "Database backup created: $BACKUP_FILE"
}

case "$1" in
    "deploy")
        check_requirements
        deploy
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "restart")
        restart_services
        ;;
    "stop")
        stop_services
        ;;
    "update")
        check_requirements
        update_deployment
        ;;
    "backup")
        backup_database
        ;;
    "urls")
        show_urls
        ;;
    *)
        echo "Usage: $0 {deploy|status|logs|restart|stop|update|backup|urls}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy the backend service"
        echo "  status  - Show service status"
        echo "  logs    - Show backend logs"
        echo "  restart - Restart services"
        echo "  stop    - Stop services"
        echo "  update  - Update and redeploy"
        echo "  backup  - Backup external database"
        echo "  urls    - Show service URLs"
        exit 1
        ;;
esac