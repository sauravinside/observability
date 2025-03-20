#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Variables
CLOUDWATCH_VERSION="0.16.0"
CLOUDWATCH_JAR="cloudwatch_exporter-$CLOUDWATCH_VERSION-jar-with-dependencies.jar"
CLOUDWATCH_URL="https://github.com/prometheus/cloudwatch_exporter/releases/download/v$CLOUDWATCH_VERSION/$CLOUDWATCH_JAR"
INSTALL_DIR="/home/ubuntu/cloudwatch_exporter"
CONFIG_FILE="$INSTALL_DIR/config.yml"

# Step 1: Install Java
sudo apt update
sudo apt install -y default-jre

# Step 2: Download CloudWatch Exporter
mkdir -p $INSTALL_DIR
wget $CLOUDWATCH_URL -O $INSTALL_DIR/$CLOUDWATCH_JAR

# Step 3: Create systemd service file
sudo tee /etc/systemd/system/cloudwatch_exporter.service > /dev/null << EOF
[Unit]
Description=CloudWatch Exporter
After=network.target

[Service]
User=ubuntu
ExecStart=/usr/bin/java -jar $INSTALL_DIR/$CLOUDWATCH_JAR 9106 $CONFIG_FILE
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Step 3.5: create config.yml:


# Step 4: Reload systemd, enable and start CloudWatch Exporter
sudo systemctl daemon-reload
sudo systemctl enable cloudwatch_exporter
sudo systemctl start cloudwatch_exporter

# Print success message
echo "CloudWatch Exporter installation complete. Ensure the configuration file at $CONFIG_FILE is correctly set up."


# #!/bin/bash
# # scripts/install_cloudwatch_exporter.sh

# # Install Java
# apt-get update
# apt-get install -y openjdk-11-jre-headless

# # Download CloudWatch Exporter
# cd /tmp
# wget https://github.com/prometheus/cloudwatch_exporter/releases/download/0.13.0/cloudwatch_exporter-0.13.0-jar-with-dependencies.jar

# # Create directory and move JAR file
# mkdir -p /opt/cloudwatch_exporter
# cp cloudwatch_exporter-*-jar-with-dependencies.jar /opt/cloudwatch_exporter/cloudwatch_exporter.jar

# # Create default config
# cat > /opt/cloudwatch_exporter/config.yml << EOF
# region: us-east-1
# metrics:
#   - aws_namespace: AWS/EC2
#     aws_metric_name: CPUUtilization
#     aws_dimensions: [InstanceId]
#     aws_statistics: [Average]
#   - aws_namespace: AWS/EC2
#     aws_metric_name: NetworkIn
#     aws_dimensions: [InstanceId]
#     aws_statistics: [Average]
#   - aws_namespace: AWS/EC2
#     aws_metric_name: NetworkOut
#     aws_dimensions: [InstanceId]
#     aws_statistics: [Average]
# EOF

# # Create CloudWatch Exporter systemd service
# cat > /etc/systemd/system/cloudwatch-exporter.service << EOF
# [Unit]
# Description=CloudWatch Exporter
# Wants=network-online.target
# After=network-online.target

# [Service]
# User=root
# Group=root
# Type=simple
# ExecStart=/usr/bin/java -jar /opt/cloudwatch_exporter/cloudwatch_exporter.jar 9106 /opt/cloudwatch_exporter/config.yml

# [Install]
# WantedBy=multi-user.target
# EOF

# # Enable and start CloudWatch Exporter
# systemctl daemon-reload
# systemctl enable cloudwatch-exporter
# systemctl start cloudwatch-exporter

# echo "CloudWatch Exporter installation completed"