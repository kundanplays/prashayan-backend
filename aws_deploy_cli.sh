#!/bin/bash

# AWS CLI Deployment Script for Prashayan Backend
# Run this script from your local machine with AWS CLI configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Configuration - Update these values
EC2_INSTANCE_ID=""  # Your EC2 instance ID (e.g., i-1234567890abcdef0)
EC2_PUBLIC_IP=""    # Your EC2 public IP (leave empty if using instance ID)
KEY_PAIR_PATH=""    # Path to your EC2 key pair (e.g., ~/.ssh/my-key.pem)
SSH_USER="ubuntu"   # EC2 user (ubuntu for Ubuntu, ec2-user for Amazon Linux)
REGION="ap-south-1" # AWS region

# Check if AWS CLI is installed and configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first:"
        echo "  curl 'https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip' -o 'awscliv2.zip'"
        echo "  unzip awscliv2.zip"
        echo "  sudo ./aws/install"
        exit 1
    fi

    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run: aws configure"
        exit 1
    fi

    print_status "AWS CLI is configured and ready"
}

# Get EC2 instance information
get_ec2_info() {
    if [ -z "$EC2_INSTANCE_ID" ]; then
        print_warning "EC2_INSTANCE_ID not set. Attempting to find instance by IP..."
        if [ -n "$EC2_PUBLIC_IP" ]; then
            EC2_INSTANCE_ID=$(aws ec2 describe-instances \
                --region $REGION \
                --filters "Name=ip-address,Values=$EC2_PUBLIC_IP" \
                --query 'Reservations[0].Instances[0].InstanceId' \
                --output text 2>/dev/null)

            if [ -z "$EC2_INSTANCE_ID" ] || [ "$EC2_INSTANCE_ID" = "None" ]; then
                print_error "Could not find EC2 instance with IP: $EC2_PUBLIC_IP"
                print_warning "Please set EC2_INSTANCE_ID in this script or ensure EC2_PUBLIC_IP is correct"
                exit 1
            fi
        else
            print_error "Please set either EC2_INSTANCE_ID or EC2_PUBLIC_IP in this script"
            exit 1
        fi
    fi

    # Get public IP if not set
    if [ -z "$EC2_PUBLIC_IP" ]; then
        EC2_PUBLIC_IP=$(aws ec2 describe-instances \
            --region $REGION \
            --instance-ids $EC2_INSTANCE_ID \
            --query 'Reservations[0].Instances[0].PublicIpAddress' \
            --output text)
    fi

    print_status "EC2 Instance ID: $EC2_INSTANCE_ID"
    print_status "EC2 Public IP: $EC2_PUBLIC_IP"
}

# Check EC2 instance state
check_ec2_state() {
    print_step "Checking EC2 instance state..."

    STATE=$(aws ec2 describe-instances \
        --region $REGION \
        --instance-ids $EC2_INSTANCE_ID \
        --query 'Reservations[0].Instances[0].State.Name' \
        --output text)

    print_status "EC2 instance state: $STATE"

    if [ "$STATE" != "running" ]; then
        print_warning "EC2 instance is not running. Current state: $STATE"
        print_warning "Starting instance..."
        aws ec2 start-instances --region $REGION --instance-ids $EC2_INSTANCE_ID

        print_status "Waiting for instance to start..."
        aws ec2 wait instance-running --region $REGION --instance-ids $EC2_INSTANCE_ID

        # Wait a bit more for SSH to be available
        sleep 30
    fi
}

# Copy .env file to EC2 instance
copy_env_file() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found in current directory"
        exit 1
    fi

    print_step "Copying environment file to EC2 instance..."

    # Use scp to copy the .env file
    scp -i "$KEY_PAIR_PATH" -o StrictHostKeyChecking=no .env $SSH_USER@$EC2_PUBLIC_IP:~/.env
    print_status "Environment file copied successfully"
}

# Run deployment commands on EC2 instance
deploy_to_ec2() {
    print_step "Starting deployment on EC2 instance..."

    # Commands to run on EC2 instance
    DEPLOY_COMMANDS="
        set -e
        echo 'Updating system packages...'
        sudo apt-get update -y

        echo 'Installing Docker and Docker Compose...'
        sudo apt-get install -y docker.io docker-compose git curl

        echo 'Adding user to docker group...'
        sudo usermod -aG docker \$USER

        echo 'Cloning/updating repository...'
        if [ -d 'prashayan-backend' ]; then
            cd prashayan-backend
            git pull origin main
            cd ..
        else
            git clone https://github.com/kundanplays/prashayan-backend.git
        fi

        cd prashayan-backend

        echo 'Copying environment file...'
        cp ~/.env .env

        echo 'Building and starting Docker containers...'
        sudo docker-compose down || true
        sudo docker-compose up -d --build

        echo 'Waiting for application to start...'
        sleep 15

        echo 'Checking container status...'
        sudo docker-compose ps

        echo 'Deployment completed successfully!'
        echo 'Application should be available at: http://$EC2_PUBLIC_IP'
    "

    # Run commands on EC2 instance via SSH
    ssh -i "$KEY_PAIR_PATH" -o StrictHostKeyChecking=no $SSH_USER@$EC2_PUBLIC_IP "$DEPLOY_COMMANDS"
}

# Test deployment
test_deployment() {
    print_step "Testing deployment..."

    echo "Testing application health..."
    if curl -f --max-time 10 http://$EC2_PUBLIC_IP/docs > /dev/null 2>&1; then
        print_status "✅ Application is responding on port 80"
        print_status "🌐 API Documentation: http://$EC2_PUBLIC_IP/docs"
        print_status "🚀 Application URL: http://$EC2_PUBLIC_IP"
    else
        print_warning "⚠️  Application may still be starting up or not accessible"
        print_warning "   Check logs on EC2: ssh -i $KEY_PAIR_PATH $SSH_USER@$EC2_PUBLIC_IP 'cd prashayan-backend && sudo docker-compose logs -f'"
    fi
}

# Main deployment function
main() {
    echo "🚀 AWS CLI Deployment for Prashayan Backend"
    echo "=========================================="

    # Validate configuration
    if [ -z "$KEY_PAIR_PATH" ]; then
        print_error "Please set KEY_PAIR_PATH in this script (path to your EC2 key pair)"
        exit 1
    fi

    if [ ! -f "$KEY_PAIR_PATH" ]; then
        print_error "Key pair file not found: $KEY_PAIR_PATH"
        exit 1
    fi

    check_aws_cli
    get_ec2_info
    check_ec2_state
    copy_env_file
    deploy_to_ec2
    test_deployment

    echo ""
    echo "🎉 Deployment completed!"
    echo "======================"
    print_status "Your application should be available at: http://$EC2_PUBLIC_IP"
    print_status "API Documentation: http://$EC2_PUBLIC_IP/docs"
}

# Show usage if no arguments provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Before running, please configure the following variables in this script:"
    echo "  - EC2_INSTANCE_ID: Your EC2 instance ID (or set EC2_PUBLIC_IP)"
    echo "  - EC2_PUBLIC_IP: Your EC2 public IP address"
    echo "  - KEY_PAIR_PATH: Path to your EC2 key pair file"
    echo "  - REGION: AWS region (default: ap-south-1)"
    echo ""
    echo "Example:"
    echo "  EC2_INSTANCE_ID='i-1234567890abcdef0'"
    echo "  KEY_PAIR_PATH='~/.ssh/my-key.pem'"
    echo ""
    echo "Then run: ./aws_deploy_cli.sh"
    exit 1
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --instance-id=*)
            EC2_INSTANCE_ID="${1#*=}"
            shift
            ;;
        --public-ip=*)
            EC2_PUBLIC_IP="${1#*=}"
            shift
            ;;
        --key-path=*)
            KEY_PAIR_PATH="${1#*=}"
            shift
            ;;
        --region=*)
            REGION="${1#*=}"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

main