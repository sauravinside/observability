#!/bin/bash

# Update package lists
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
# Install common utilities and Python dependencies
sudo apt install -y unzip wget nginx ansible python3 python3-pip python3-flask-cors python3-paramiko python3-scp python3-flask python3-boto3

# Install AWS CLI (Corrected)
sudo curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo unzip awscliv2.zip
sudo ./aws/install

# Install CloudWatch agent
sudo wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
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
sudo rm amazon-cloudwatch-agent.deb awscliv2.zip

# Create systemd service for CloudWatch Monitoring application
sudo tee /etc/systemd/system/cloudwatch_monitoring.service > /dev/null << 'EOF'
[Unit]
Description=CloudWatch Monitoring Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/observability/cloudwatch/backend
ExecStart=sudo /usr/bin/python3 /opt/observability/cloudwatch/backend/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon and start the CloudWatch Monitoring service
sudo systemctl daemon-reload
sudo systemctl enable cloudwatch_monitoring
sudo systemctl start cloudwatch_monitoring