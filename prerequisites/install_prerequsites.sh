#!/bin/bash

# Update package lists
sudo apt update

# Install common utilities
sudo apt install -y unzip wget

# Install Python 3 and pip
sudo apt install -y python3 python3-pip

# Install required Python packages (using apt with deadsnakes PPA)
sudo add-apt-repository -y --no-interaction ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3-flask python3-boto3

# Install Terraform (check for the latest version on HashiCorp's website and update URL)
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip  # Update version if needed
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Install AWS CLI (Corrected)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install Nginx
sudo apt install -y nginx

# Create project directories (if they don't exist)
mkdir -p aws-monitoring-tool/frontend aws-monitoring-tool/backend aws-monitoring-tool/terraform

# Create empty files (if they don't exist)
touch aws-monitoring-tool/frontend/index.html aws-monitoring-tool/backend/app.py aws-monitoring-tool/terraform/main.tf

# Set up AWS credentials (using profiles - IMPORTANT)
mkdir -p ~/.aws  # Ensure.aws directory exists
cat << EOF > ~/.aws/credentials
[default]  # Or your profile name
aws_access_key_id = YOUR_AWS_ACCESS_KEY_ID  # REPLACE WITH YOUR KEY
aws_secret_access_key = YOUR_AWS_SECRET_ACCESS_KEY # REPLACE WITH YOUR SECRET
EOF

echo "export AWS_PROFILE=\"default\"" >> ~/.bashrc
source ~/.bashrc

echo "Prerequisites installed. Now copy your application files into the correct locations and run the application."