# Deployment Guide for AWS EC2

This guide assumes you have an existing EC2 instance, VPC, Security Group, and Database (RDS or self-hosted).

## Prerequisites

1.  **EC2 Instance**: Running Ubuntu or Amazon Linux 2.
2.  **Security Group**: Ports 80 (HTTP) and 22 (SSH) must be open.
3.  **Database**: Connection details (Host, Port, User, Password, Database Name).

## Steps

1.  **SSH into your EC2 Instance**
    ```bash
    ssh -i /path/to/your-key.pem ubuntu@your-ec2-ip
    ```

2.  **Install Docker and Git**
    *For Ubuntu:*
    ```bash
    sudo apt-get update
    sudo apt-get install -y docker.io git docker-compose
    sudo usermod -aG docker $USER
    # Log out and log back in for group changes to take effect
    ```
    *For Amazon Linux 2:*
    ```bash
    sudo amazon-linux-extras install docker
    sudo service docker start
    sudo usermod -aG docker $USER
    sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    ```

3.  **Clone or Copy the Code**
    Clone your repository:
    ```bash
    git clone <your-repo-url>
    cd prashayan-backend
    ```

4.  **Configure Environment Variables**
    Copy the example configuration:
    ```bash
    cp env.example .env
    ```
    Edit `.env` with your actual values:
    ```bash
    nano .env
    ```
    *Crucial Updates:*
    - `DATABASE_URL`: Change `sqlite:///...` to your Postgres connection string (e.g., `postgresql://user:password@rds-endpoint:5432/dbname`).
    - `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`: For S3 access.

5.  **Run the Application**
    ```bash
    docker-compose up -d --build
    ```

6.  **Verify**
    Visit `http://your-ec2-ip` (or `http://your-ec2-ip/docs` for Swagger UI).

## Troubleshooting

-   **Database Connection**: Ensure the Security Group of your RDS/Database allows traffic from the EC2 instance's Security Group.
-   **Logs**: Check application logs with:
    ```bash
    docker-compose logs -f
    ```
