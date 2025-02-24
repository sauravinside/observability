#!/bin/bash

# Update package lists
sudo apt update

# Install common utilities
sudo apt install -y unzip wget

# Install Python 3 and pip along with Flask CORS
sudo apt install -y python3 python3-pip python3-flask-cors python3-paramiko python3-scp

# Install required Python packages (using apt with deadsnakes PPA)
sudo add-apt-repository -y --no-interaction ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3-flask python3-boto3

# Additional package installations
sudo apt install -y awscli python3-boto3 python3-flask-cors \
    python3-paramiko python3-scp \
    awscli-plugin-rds awscli-plugin-lambda

# Install AWS CLI (Corrected)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install Nginx
sudo apt install -y nginx

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Create CloudWatch agent configuration
sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc
sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json > /dev/null << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "root"
    },
    "metrics": {
        "namespace": "CWAgent",
        "metrics_collected": {
            "mem": {
                "measurement": [
                    {"name": "mem_used_percent", "rename": "MemoryUtilization"}
                ],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": [
                    {"name": "disk_used_percent", "rename": "DiskSpaceUtilization"}
                ],
                "resources": ["/"],
                "metrics_collection_interval": 60
            }
        },
        "append_dimensions": {
            "InstanceId": "${aws:InstanceId}"
        }
    }
}
EOF

# Start CloudWatch agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
sudo systemctl start amazon-cloudwatch-agent
sudo systemctl enable amazon-cloudwatch-agent

# Clean up installation files
rm amazon-cloudwatch-agent.deb

echo "CloudWatch agent installed and configured for memory and disk metrics."

echo "Prerequisites installed. Now copy your application files into the correct locations and run the application."
