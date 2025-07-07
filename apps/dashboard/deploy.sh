#!/bin/bash

# Project88 Dashboard Deployment Script
# Run this script on your production server (69.62.69.90)

set -e

echo "🚀 Project88 Dashboard Deployment Script"
echo "=========================================="

# Configuration
DASHBOARD_DIR="/home/appuser/projects/project88-production-repo/apps/dashboard"
SERVICE_NAME="project88-dashboard"
DOMAIN="dashboard.project88hub.com"
PORT=5004

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check Python
if ! command_exists python3; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check PostgreSQL
if ! command_exists psql; then
    print_error "PostgreSQL client is required but not installed"
    exit 1
fi

# Check Redis
if ! command_exists redis-cli; then
    print_error "Redis client is required but not installed"
    exit 1
fi

# Test database connection
print_status "Testing database connection..."
if ! psql -h localhost -U postgres -d project88_myappdb -c "SELECT 1;" >/dev/null 2>&1; then
    print_error "Cannot connect to PostgreSQL database"
    exit 1
fi

# Test Redis connection
print_status "Testing Redis connection..."
if ! redis-cli ping >/dev/null 2>&1; then
    print_error "Cannot connect to Redis server"
    exit 1
fi

# Navigate to dashboard directory
print_status "Navigating to dashboard directory..."
cd "$DASHBOARD_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing Python dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Create .env file if it doesn't exist
if [ ! -f "backend/.env" ]; then
    print_status "Creating environment configuration..."
    cp backend/.env.example backend/.env
    print_warning "Please edit backend/.env with your database credentials"
fi

# Test the application
print_status "Testing application startup..."
timeout 10 python start_dashboard.py &
PYTHON_PID=$!
sleep 5

# Check if the application is running
if kill -0 $PYTHON_PID 2>/dev/null; then
    print_status "Application test successful"
    kill $PYTHON_PID
    wait $PYTHON_PID 2>/dev/null
else
    print_error "Application test failed"
    exit 1
fi

# Install systemd service
print_status "Installing systemd service..."
sudo cp dashboard.service /etc/systemd/system/${SERVICE_NAME}.service

# Reload systemd and enable service
print_status "Enabling systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.service

# Start the service
print_status "Starting dashboard service..."
sudo systemctl start ${SERVICE_NAME}.service

# Check service status
if sudo systemctl is-active --quiet ${SERVICE_NAME}.service; then
    print_status "Dashboard service started successfully"
else
    print_error "Failed to start dashboard service"
    sudo systemctl status ${SERVICE_NAME}.service
    exit 1
fi

# Configure Apache virtual host
print_status "Configuring Apache virtual host..."
cat > /tmp/dashboard-vhost.conf << EOF
<VirtualHost *:443>
    ServerName ${DOMAIN}
    
    # Proxy to dashboard application
    ProxyPass / http://localhost:${PORT}/
    ProxyPassReverse / http://localhost:${PORT}/
    
    # Headers for better performance
    ProxyPreserveHost On
    ProxyAddHeaders On
    
    # SSL Configuration (using existing certificates)
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/project88hub.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/project88hub.com/privkey.pem
    
    # Security headers
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    
    # Logging
    ErrorLog /var/log/apache2/dashboard_error.log
    CustomLog /var/log/apache2/dashboard_access.log combined
</VirtualHost>

# Redirect HTTP to HTTPS
<VirtualHost *:80>
    ServerName ${DOMAIN}
    Redirect permanent / https://${DOMAIN}/
</VirtualHost>
EOF

# Install Apache configuration
sudo mv /tmp/dashboard-vhost.conf /etc/apache2/sites-available/dashboard.conf
sudo a2ensite dashboard.conf
sudo systemctl reload apache2

# Test the deployment
print_status "Testing deployment..."
sleep 3

# Test local connection
if curl -s -o /dev/null -w "%{http_code}" http://localhost:${PORT}/api/health | grep -q "200"; then
    print_status "Local connection test passed"
else
    print_error "Local connection test failed"
fi

# Show service status
print_status "Service status:"
sudo systemctl status ${SERVICE_NAME}.service --no-pager

# Show logs
print_status "Recent logs:"
sudo journalctl -u ${SERVICE_NAME}.service --no-pager -n 10

# Final instructions
echo ""
echo "🎉 Dashboard deployment completed successfully!"
echo "============================================="
echo ""
echo "Dashboard is now running at:"
echo "  - Local: http://localhost:${PORT}"
echo "  - Domain: https://${DOMAIN}"
echo ""
echo "Service management:"
echo "  - Start:   sudo systemctl start ${SERVICE_NAME}"
echo "  - Stop:    sudo systemctl stop ${SERVICE_NAME}"
echo "  - Restart: sudo systemctl restart ${SERVICE_NAME}"
echo "  - Status:  sudo systemctl status ${SERVICE_NAME}"
echo "  - Logs:    sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "Configuration:"
echo "  - App directory: ${DASHBOARD_DIR}"
echo "  - Service file: /etc/systemd/system/${SERVICE_NAME}.service"
echo "  - Apache config: /etc/apache2/sites-available/dashboard.conf"
echo "  - Environment: ${DASHBOARD_DIR}/backend/.env"
echo ""
print_warning "Remember to update your DNS to point ${DOMAIN} to your server IP!"
echo ""
print_status "Deployment complete! 🚀" 