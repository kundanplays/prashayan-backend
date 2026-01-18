# AWS CLI Deployment for Prashayan Backend

This script allows you to deploy your Prashayan backend application to AWS EC2 using AWS CLI from your local machine.

## Prerequisites

1. **AWS CLI installed and configured:**
   ```bash
   # Install AWS CLI v2
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # Configure AWS CLI
   aws configure
   ```

2. **EC2 instance running Ubuntu**
3. **SSH key pair for EC2 access**
4. **Proper IAM permissions** for:
   - EC2 instance management
   - Starting/stopping instances

## Quick Start

### Method 1: Configure and Run

1. **Edit the script variables:**
   ```bash
   nano aws_deploy_cli.sh
   ```

   Update these variables at the top of the script:
   ```bash
   EC2_INSTANCE_ID="i-1234567890abcdef0"  # Your EC2 instance ID
   EC2_PUBLIC_IP=""                       # Or set public IP if you don't have instance ID
   KEY_PAIR_PATH="~/.ssh/my-key.pem"      # Path to your EC2 key pair
   SSH_USER="ubuntu"                      # EC2 user (ubuntu/ec2-user)
   REGION="ap-south-1"                    # Your AWS region
   ```

2. **Run the deployment:**
   ```bash
   ./aws_deploy_cli.sh
   ```

### Method 2: Command Line Arguments

You can also pass configuration via command line:

```bash
./aws_deploy_cli.sh \
  --instance-id=i-1234567890abcdef0 \
  --key-path=~/.ssh/my-key.pem \
  --region=ap-south-1
```

Or using public IP:

```bash
./aws_deploy_cli.sh \
  --public-ip=13.234.56.789 \
  --key-path=~/.ssh/my-key.pem \
  --region=ap-south-1
```

## What the Script Does

1. **Validates AWS CLI configuration**
2. **Checks EC2 instance state** and starts it if needed
3. **Copies your `.env` file** to the EC2 instance
4. **Runs automated deployment** on the EC2 instance:
   - Updates system packages
   - Installs Docker and Docker Compose
   - Clones/pulls your repository
   - Builds and starts Docker containers
5. **Tests the deployment** and provides access URLs

## Configuration Options

| Variable | Description | Example |
|----------|-------------|---------|
| `EC2_INSTANCE_ID` | Your EC2 instance ID | `i-1234567890abcdef0` |
| `EC2_PUBLIC_IP` | Public IP of your EC2 instance | `13.234.56.789` |
| `KEY_PAIR_PATH` | Path to SSH key pair | `~/.ssh/my-key.pem` |
| `SSH_USER` | SSH user for EC2 | `ubuntu` or `ec2-user` |
| `REGION` | AWS region | `ap-south-1` |

## Finding Your EC2 Information

### Get Instance ID:
```bash
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,PublicIpAddress,State.Name]' --output table
```

### Get Public IP from Instance ID:
```bash
aws ec2 describe-instances --instance-ids i-1234567890abcdef0 --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```

## Troubleshooting

### AWS CLI Not Configured
```bash
aws configure
# Enter your AWS Access Key ID, Secret Key, region, and output format
```

### Permission Denied (SSH)
- Ensure your key pair file has correct permissions: `chmod 400 ~/.ssh/my-key.pem`
- Verify the key pair is associated with your EC2 instance

### EC2 Instance Not Found
- Check your instance ID is correct
- Ensure you're in the right AWS region
- Verify the instance exists and is running

### Docker Permission Issues
The script handles this automatically by adding the user to the docker group, but you may need to log out and back in on the EC2 instance.

## Security Notes

- The script copies your `.env` file securely via SCP
- SSH connections use strict host key checking disabled for automation
- Consider enabling host key checking in production environments

## Post-Deployment

After successful deployment:
- **Application URL**: `http://your-ec2-public-ip`
- **API Documentation**: `http://your-ec2-public-ip/docs`
- **Check logs**: `ssh ubuntu@your-ip 'cd prashayan-backend && sudo docker-compose logs -f'`

## Alternative Deployment Methods

If you prefer different approaches:

1. **Manual deployment**: Use `deploy.sh` script directly on EC2
2. **AWS CodeDeploy**: For blue-green deployments
3. **AWS Elastic Beanstalk**: For managed deployments
4. **GitHub Actions**: CI/CD pipeline deployment

## Support

For issues:
1. Check the script output for error messages
2. Verify your AWS permissions and configuration
3. Ensure your EC2 instance security group allows SSH (port 22) and HTTP (port 80)
4. Check EC2 instance logs if deployment fails