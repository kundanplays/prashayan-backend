#!/bin/bash

# EC2 Key Pair Setup and Alternative Connection Methods
# Run this after installing AWS CLI

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

# Configuration
REGION="ap-south-1"
KEY_NAME="prashayan-key-$(date +%Y%m%d-%H%M%S)"
KEY_PATH="$HOME/.ssh/${KEY_NAME}.pem"

# Check AWS CLI
check_aws_cli() {
    print_step "Checking AWS CLI installation..."

    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed."
        print_status "Installing AWS CLI v2..."

        # Download and install AWS CLI
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install

        # Clean up
        rm -rf aws awscliv2.zip
    fi

    print_status "AWS CLI is installed"

    # Configure AWS CLI if not configured
    if ! aws sts get-caller-identity &> /dev/null; then
        print_warning "AWS CLI is not configured. Please run:"
        echo "aws configure"
        echo ""
        echo "You'll need to provide your AWS credentials:"
        echo "- AWS Access Key ID"
        echo "- AWS Secret Access Key"
        echo "- Default region: ap-south-1"
        echo "- Default output format: json"
        exit 1
    fi

    print_status "AWS CLI is configured and ready"
}

# Create new key pair
create_keypair() {
    print_step "Creating new EC2 key pair: $KEY_NAME"

    # Create .ssh directory if it doesn't exist
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"

    # Create key pair
    aws ec2 create-key-pair \
        --region $REGION \
        --key-name $KEY_NAME \
        --query 'KeyMaterial' \
        --output text > "$KEY_PATH"

    # Set correct permissions
    chmod 400 "$KEY_PATH"

    print_status "Key pair created successfully!"
    print_status "Private key saved to: $KEY_PATH"
    print_warning "Keep this file secure and don't share it!"
}

# List existing key pairs
list_keypairs() {
    print_step "Listing existing EC2 key pairs..."

    aws ec2 describe-key-pairs \
        --region $REGION \
        --query 'KeyPairs[*].[KeyName,KeyPairId,KeyType]' \
        --output table
}

# Associate key pair with running instance
associate_keypair() {
    echo ""
    print_step "To associate this key pair with your existing EC2 instance:"
    echo ""
    echo "1. Stop your EC2 instance (if it's running):"
    echo "   aws ec2 stop-instances --instance-ids YOUR_INSTANCE_ID --region $REGION"
    echo ""
    echo "2. Modify the instance to use the new key pair:"
    echo "   aws ec2 modify-instance-attribute \\"
    echo "     --instance-id YOUR_INSTANCE_ID \\"
    echo "     --region $REGION \\"
    echo "     --attribute sshKeys \\"
    echo "     --value '{\"Add\":[{\"KeyName\":\"$KEY_NAME\"}]}'"
    echo ""
    echo "3. Start your instance:"
    echo "   aws ec2 start-instances --instance-ids YOUR_INSTANCE_ID --region $REGION"
    echo ""
    echo "4. Update the deployment script with:"
    echo "   KEY_PAIR_PATH=\"$KEY_PATH\""
}

# Alternative connection methods
show_alternatives() {
    echo ""
    print_step "ALTERNATIVE CONNECTION METHODS (if you can't use SSH keys):"
    echo ""

    echo "1. AWS EC2 Instance Connect:"
    echo "   - Go to EC2 console → Instances"
    echo "   - Select your instance → Connect → EC2 Instance Connect"
    echo "   - Click 'Connect' (works without key pairs)"
    echo ""

    echo "2. AWS Systems Manager Session Manager:"
    echo "   - Install SSM agent on your instance"
    echo "   - Use: aws ssm start-session --target YOUR_INSTANCE_ID"
    echo "   - No SSH keys required, works through AWS API"
    echo ""

    echo "3. Create new instance with new key pair:"
    echo "   - Launch new EC2 instance with the new key pair"
    echo "   - Migrate your data if needed"
    echo ""

    echo "4. Password-based authentication (NOT RECOMMENDED):"
    echo "   - Modify instance to allow password auth"
    echo "   - Set a strong password for the ubuntu/ec2-user"
}

# Main function
main() {
    echo "🔑 EC2 Key Pair Setup for Prashayan Deployment"
    echo "=============================================="

    check_aws_cli

    echo ""
    echo "Choose an option:"
    echo "1) Create a new key pair"
    echo "2) List existing key pairs"
    echo "3) Show alternative connection methods"
    echo ""

    read -p "Enter your choice (1-3): " choice

    case $choice in
        1)
            create_keypair
            associate_keypair
            ;;
        2)
            list_keypairs
            ;;
        3)
            show_alternatives
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac

    echo ""
    print_status "Setup completed!"
    print_status "Next steps:"
    echo "1. Associate the key pair with your EC2 instance (see instructions above)"
    echo "2. Update aws_deploy_cli.sh with: KEY_PAIR_PATH=\"$KEY_PATH\""
    echo "3. Run: ./aws_deploy_cli.sh"
}

# Run main function
main