#!/bin/bash

# Project88Hub Provider Integration Deployment Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="project88-provider-sync"
REPO_URL="https://github.com/yourusername/project88-provider-integrations.git"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
check_user() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
    fi
}

# Install Docker if not present
install_docker() {
    if ! command -v docker &> /dev/null; then
        log "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        log "Docker installed. You may need to log out and back in."
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log "Installing Docker Compose..."
        sudo pip3 install docker-compose
    fi
}

# Create directory structure
setup_directories() {
    log "Setting up directory structure..."
    sudo mkdir -p /var/log/project88
    sudo chown $USER:$USER /var/log/project88
    mkdir -p logs backups
}

# Create environment file
create_env_file() {
    if [[ ! -f ".env" ]]; then
        log "Creating environment file..."
        cat > .env << EOF
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=project88_myappdb
DB_USER=project88_myappuser
DB_PASSWORD=CHANGE_THIS_PASSWORD

# Logging Configuration
LOG_LEVEL=INFO
EOF
        warn "Please edit .env file with your database credentials!"
    fi
}

# Deploy using Docker Compose
deploy_docker() {
    log "Deploying with Docker Compose..."
    
    # Check if .env exists
    if [[ ! -f ".env" ]]; then
        error ".env file not found. Run with --setup first."
    fi
    
    # Pull latest changes if this is an update
    if [[ -d ".git" ]]; then
        log "Pulling latest changes from repository..."
        git pull origin main
    fi
    
    # Build and start services
    docker-compose down --remove-orphans
    docker-compose build --no-cache
    docker-compose up -d
    
    log "Deployment complete!"
    log "View logs with: docker-compose logs -f provider-sync"
    log "Check status with: docker-compose ps"
}

# Deploy as systemd service (alternative to Docker)
deploy_systemd() {
    log "Deploying as systemd service..."
    
    # Install Python dependencies
    if [[ ! -d "venv" ]]; then
        log "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Create systemd service file
    sudo tee /etc/systemd/system/${APP_NAME}.service > /dev/null << EOF
[Unit]
Description=Project88Hub Provider Integration System
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$SCRIPT_DIR/venv/bin
ExecStart=$SCRIPT_DIR/venv/bin/python main.py --workers 2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=DB_HOST=${DB_HOST:-localhost}
Environment=DB_NAME=${DB_NAME:-project88_myappdb}
Environment=DB_USER=${DB_USER:-project88_myappuser}
Environment=DB_PASSWORD=${DB_PASSWORD}

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and start service
    sudo systemctl daemon-reload
    sudo systemctl enable ${APP_NAME}
    sudo systemctl restart ${APP_NAME}
    
    log "Systemd service deployed!"
    log "Check status with: sudo systemctl status ${APP_NAME}"
    log "View logs with: sudo journalctl -u ${APP_NAME} -f"
}

# Check service health
check_health() {
    log "Checking service health..."
    
    if docker ps | grep -q "${APP_NAME}"; then
        log "Docker container is running"
        docker-compose exec provider-sync python main.py --test-connection
    elif systemctl is-active --quiet ${APP_NAME}; then
        log "Systemd service is running"
        source venv/bin/activate
        python main.py --test-connection
    else
        warn "Service doesn't appear to be running"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --setup          Initial setup (directories, Docker, env file)"
    echo "  --docker         Deploy using Docker Compose"
    echo "  --systemd        Deploy as systemd service"
    echo "  --update         Update from repository and restart"
    echo "  --health         Check service health"
    echo "  --logs           Show recent logs"
    echo "  --stop           Stop the service"
    echo "  --help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --setup --docker    # Initial setup and Docker deployment"
    echo "  $0 --update            # Update and restart"
    echo "  $0 --health            # Check if everything is working"
}

# Main execution
main() {
    case "${1:-}" in
        --setup)
            check_user
            setup_directories
            install_docker
            create_env_file
            log "Setup complete! Edit .env file and run with --docker or --systemd"
            ;;
        --docker)
            check_user
            deploy_docker
            ;;
        --systemd)
            check_user
            deploy_systemd
            ;;
        --update)
            log "Updating deployment..."
            if docker ps | grep -q "${APP_NAME}"; then
                deploy_docker
            elif systemctl is-active --quiet ${APP_NAME}; then
                deploy_systemd
            else
                error "No active deployment found"
            fi
            ;;
        --health)
            check_health
            ;;
        --logs)
            if docker ps | grep -q "${APP_NAME}"; then
                docker-compose logs -f --tail=100 provider-sync
            else
                sudo journalctl -u ${APP_NAME} -f --lines=100
            fi
            ;;
        --stop)
            log "Stopping service..."
            docker-compose down 2>/dev/null || true
            sudo systemctl stop ${APP_NAME} 2>/dev/null || true
            log "Service stopped"
            ;;
        --help|*)
            usage
            ;;
    esac
}

main "$@" 