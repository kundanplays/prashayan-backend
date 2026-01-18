#!/bin/bash

# Browser-based EC2 Deployment (No SSH Keys Required)
# Uses AWS EC2 Instance Connect

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check AWS CLI
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is required for this method."
        print_status "Installing AWS CLI..."

        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf aws awscliv2.zip
    fi

    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI not configured. Run: aws configure"
        exit 1
    fi
}

# Get EC2 instance info
get_instance_info() {
    print_step "Getting EC2 instance information..."

    # List instances
    echo "Your EC2 instances:"
    aws ec2 describe-instances \
        --region ap-south-1 \
        --query 'Reservations[*].Instances[*].[InstanceId,PublicIpAddress,State.Name,Tags[?Key==`Name`].Value|[0]]' \
        --output table

    echo ""
    read -p "Enter your EC2 Instance ID: " INSTANCE_ID

    if [ -z "$INSTANCE_ID" ]; then
        print_error "Instance ID is required"
        exit 1
    fi

    # Get instance details
    INSTANCE_INFO=$(aws ec2 describe-instances \
        --region ap-south-1 \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].[PublicIpAddress,State.Name]' \
        --output text)

    PUBLIC_IP=$(echo $INSTANCE_INFO | awk '{print $1}')
    STATE=$(echo $INSTANCE_INFO | awk '{print $2}')

    print_status "Instance ID: $INSTANCE_ID"
    print_status "Public IP: $PUBLIC_IP"
    print_status "State: $STATE"
}

# Start instance if needed
start_instance() {
    if [ "$STATE" != "running" ]; then
        print_warning "Instance is not running. Starting it..."
        aws ec2 start-instances --instance-ids $INSTANCE_ID --region ap-south-1

        print_status "Waiting for instance to start..."
        aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region ap-south-1

        # Wait for services to start
        sleep 30

        # Refresh instance info
        PUBLIC_IP=$(aws ec2 describe-instances \
            --region ap-south-1 \
            --instance-ids $INSTANCE_ID \
            --query 'Reservations[0].Instances[0].PublicIpAddress' \
            --output text)
    fi
}

# Main browser-based deployment
main() {
    echo "🌐 Browser-Based EC2 Deployment (No SSH Keys Required)"
    echo "======================================================"

    check_aws_cli
    get_instance_info
    start_instance

    echo ""
    print_step "DEPLOYMENT INSTRUCTIONS:"
    echo ""
    echo "1. Open AWS EC2 Console in your browser:"
    echo "   https://console.aws.amazon.com/ec2/"
    echo ""
    echo "2. Go to Instances → Select your instance ($INSTANCE_ID)"
    echo ""
    echo "3. Click 'Connect' button → Choose 'EC2 Instance Connect' tab"
    echo ""
    echo "4. Click 'Connect' button (opens browser-based terminal)"
    echo ""
    echo "5. In the browser terminal, run these commands:"
    echo ""
    echo "   # Update system and install requirements"
    echo "   sudo apt-get update -y"
    echo "   sudo apt-get install -y docker.io docker-compose git"
    echo ""
    echo "   # Clone your repository"
    echo "   git clone https://github.com/kundanplays/prashayan-backend.git"
    echo "   cd prashayan-backend"
    echo ""
    echo "   # Create environment file (you'll need to paste your .env content)"
    echo "   nano .env  # or use another editor"
    echo ""
    echo "   # Add user to docker group"
    echo "   sudo usermod -aG docker ubuntu"
    echo ""
    echo "   # Deploy the application"
    echo "   sudo docker-compose up -d --build"
    echo ""
    echo "   # Check status"
    echo "   sudo docker-compose ps"
    echo ""

    print_status "Browser URL: https://console.aws.amazon.com/ec2/v2/home?region=ap-south-1#ConnectToInstance:instanceId=$INSTANCE_ID"
    echo ""
    print_status "After deployment, your app will be available at: http://$PUBLIC_IP"
    print_status "API Documentation: http://$PUBLIC_IP/docs"
}

main