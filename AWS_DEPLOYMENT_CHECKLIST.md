# AWS Deployment Checklist for Prashayan Backend

## ✅ Prerequisites Checklist

### 1. AWS Resources
- [ ] **EC2 Instance**: Ubuntu 20.04+ or Amazon Linux 2
- [ ] **Security Group**: Open ports 80 (HTTP), 22 (SSH), and optionally 443 (HTTPS)
- [ ] **RDS PostgreSQL Database**: Configured with your credentials
- [ ] **S3 Bucket**: Created for file storage
- [ ] **IAM User**: With S3 access permissions

### 2. Local Setup
- [x] Code pushed to main branch on GitHub
- [x] Environment variables configured in `.env` file
- [x] Sensitive files added to `.gitignore`

## 🚀 Deployment Steps

### On your AWS EC2 Instance:

1. **SSH into your EC2 instance:**
   ```bash
   ssh -i /path/to/your-key.pem ubuntu@your-ec2-public-ip
   ```

2. **Run the automated deployment script:**
   ```bash
   # Download and run the deployment script
   wget https://raw.githubusercontent.com/kundanplays/prashayan-backend/main/deploy.sh
   chmod +x deploy.sh
   ./deploy.sh
   ```

   Or manually follow these steps if you prefer:

   ```bash
   # Update system
   sudo apt-get update -y

   # Install Docker and Docker Compose
   sudo apt-get install -y docker.io docker-compose git curl

   # Add user to docker group
   sudo usermod -aG docker $USER

   # Clone repository
   git clone https://github.com/kundanplays/prashayan-backend.git
   cd prashayan-backend

   # Copy environment file (you'll need to upload this)
   # scp your .env file to the server first

   # Build and run
   sudo docker-compose up -d --build
   ```

3. **Verify deployment:**
   ```bash
   # Check container status
   sudo docker-compose ps

   # View logs
   sudo docker-compose logs -f

   # Test application
   curl http://localhost/docs
   ```

## 🔧 Configuration Details

### Environment Variables (already configured in your .env)
- **Database**: PostgreSQL on RDS
- **AWS S3**: For file uploads
- **Razorpay**: Payment processing
- **Zoho Mail**: Email notifications

### Network Configuration
- **Port 80**: Application accessible via HTTP
- **Security Group**: Ensure EC2 can access RDS

## 📊 Post-Deployment Checks

- [ ] Application accessible at `http://your-ec2-ip`
- [ ] API documentation available at `http://your-ec2-ip/docs`
- [ ] Database connection working
- [ ] File uploads to S3 working
- [ ] Email notifications working
- [ ] Payment integration working

## 🔍 Troubleshooting

### Common Issues:

1. **Permission denied with Docker:**
   ```bash
   sudo usermod -aG docker $USER
   # Log out and log back in
   ```

2. **Database connection failed:**
   - Check RDS security group allows traffic from EC2
   - Verify DATABASE_URL in .env file

3. **Application not starting:**
   ```bash
   sudo docker-compose logs -f
   ```

4. **Port 80 already in use:**
   ```bash
   sudo netstat -tulpn | grep :80
   sudo docker-compose down
   sudo docker-compose up -d
   ```

## 🔒 Security Recommendations

- [ ] Change default SECRET_KEY in production
- [ ] Set up HTTPS with SSL certificate (Let's Encrypt)
- [ ] Configure firewall rules properly
- [ ] Use IAM roles instead of access keys for EC2
- [ ] Enable CloudWatch monitoring
- [ ] Set up backup strategy for RDS

## 📞 Support

If you encounter issues:
1. Check application logs: `sudo docker-compose logs -f`
2. Verify environment variables in .env file
3. Ensure AWS resources are properly configured
4. Check DEPLOYMENT.md for detailed troubleshooting

---

**Your application will be available at:** `http://your-ec2-instance-public-ip`

**API Documentation:** `http://your-ec2-instance-public-ip/docs`