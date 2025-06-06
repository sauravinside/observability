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
sudo systemctl start cloudwatch_monitoring
sudo systemctl enable cloudwatch_monitoring
sudo systemctl stop cloudwatch_monitoring

# Create systemd service for Grafana application
sudo tee /etc/systemd/system/grafanamonitoring.service > /dev/null << 'EOF'
[Unit]
Description=Grafana Monitoring Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/observability/grafana
ExecStart=sudo /usr/bin/python3 /opt/observability/grafana/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon and start the CloudWatch Monitoring service
sudo systemctl daemon-reload
sudo systemctl start grafanamonitoring
sudo systemctl enable grafanamonitoring
sudo systemctl stop grafanamonitoring

# Create the systemd service file for EKS app
sudo tee /etc/systemd/system/eksmonitoring.service > /dev/null << 'EOF'
[Unit]
Description=EKS Monitoring Portal
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/opt/observability/EKS
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/observability/EKS"
Environment="FLASK_APP=/opt/observability/EKS/app.py"
Environment="FLASK_ENV=production"
Environment="PYTHONUNBUFFERED=1"

# Change the ExecStart to capture more detailed errors
ExecStart=/usr/bin/python3 -u /opt/observability/EKS/app.py

# Restart configuration
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/eksmonitoring.log
StandardError=append:/var/log/eksmonitoring.error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable eksmonitoring.service
sudo systemctl start eksmonitoring.service
sudo systemctl stop eksmonitoring.service

# Create the systemd service file for Ansible app
sudo tee /etc/systemd/system/ansiblemonitoring.service > /dev/null << 'EOF'
[Unit]
Description=Ansible Monitoring Portal
After=network.target

[Service]
User=root
WorkingDirectory=/opt/observability/ansible
ExecStart=/usr/bin/python3 /opt/observability/ansible/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable ansiblemonitoring.service
sudo systemctl start ansiblemonitoring.service
sudo systemctl stop ansiblemonitoring.service

# Create the systemd service file for main app
sudo tee /etc/systemd/system/observability.service > /dev/null << 'EOF'
[Unit]
Description=AWS Observability Portal
After=network.target

[Service]
User=root
WorkingDirectory=/opt/observability/main
ExecStart=/usr/bin/python3 /opt/observability/main/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable and start the service
sudo systemctl enable observability.service
sudo systemctl start observability.service

# Configure Nginx to serve the Main Observability Portal on port 80
sudo tee /etc/nginx/sites-available/observability > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

# Create symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/observability /etc/nginx/sites-enabled/

# Remove default site if it exists
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Restart Nginx to apply changes
sudo systemctl restart nginx

# Check service status
sudo systemctl status observability.service