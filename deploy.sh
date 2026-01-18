#!/bin/bash

# Prashayan Backend Deployment Script for AWS EC2
# Run this script on your EC2 instance

set -e

echo "🚀 Starting Prashayan Backend Deployment..."

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

# Check if running as root or with sudo
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Please run as a regular user with sudo privileges."
   exit 1
fi

print_status "Updating system packages..."
sudo apt-get update -y

print_status "Installing Docker and Docker Compose..."
sudo apt-get install -y docker.io docker-compose git curl

print_status "Adding user to docker group..."
sudo usermod -aG docker $USER

print_status "Cloning/pulling repository..."
if [ -d "prashayan-backend" ]; then
    cd prashayan-backend
    git pull origin main
    cd ..
else
    git clone https://github.com/kundanplays/prashayan-backend.git
fi

cd prashayan-backend

print_status "Checking if .env file exists..."
if [ ! -f ".env" ]; then
    print_error ".env file not found! Please ensure your environment variables are set."
    print_warning "You need to manually create .env file with your credentials or copy it from your local machine."
    exit 1
fi

print_status "Building and starting Docker containers..."
sudo docker-compose down || true
sudo docker-compose up -d --build

print_status "Waiting for application to start..."
sleep 10

print_status "Checking container status..."
sudo docker-compose ps

print_status "Checking application logs..."
sudo docker-compose logs -f --tail=20

print_status "Deployment completed successfully! 🎉"
print_warning "Note: You may need to log out and log back in for docker group changes to take effect."
print_warning "Your application should be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"

# Optional: Check if the application is responding
print_status "Testing application health..."
if curl -f http://localhost/docs > /dev/null 2>&1; then
    print_status "✅ Application is responding on port 80"
else
    print_warning "⚠️  Application may still be starting up. Check logs with: docker-compose logs -f"
fi