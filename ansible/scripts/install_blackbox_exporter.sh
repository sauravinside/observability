#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Variables
BLACKBOX_VERSION="0.25.0"
BLACKBOX_ARCHIVE="blackbox_exporter-$BLACKBOX_VERSION.linux-amd64.tar.gz"
BLACKBOX_URL="https://github.com/prometheus/blackbox_exporter/releases/download/v$BLACKBOX_VERSION/$BLACKBOX_ARCHIVE"
BLACKBOX_DIR="blackbox_exporter-$BLACKBOX_VERSION.linux-amd64"

# Step 1: Download and extract Blackbox Exporter
wget $BLACKBOX_URL
tar -xvf $BLACKBOX_ARCHIVE
rm $BLACKBOX_ARCHIVE

# Step 2: Create blackbox user and set up directories
sudo useradd -r -s /bin/false blackbox
sudo mv $BLACKBOX_DIR/blackbox_exporter /usr/local/bin/
sudo mkdir -p /etc/blackbox_exporter
sudo mv $BLACKBOX_DIR/blackbox.yml /etc/blackbox_exporter/
sudo chown -R blackbox:blackbox /usr/local/bin/blackbox_exporter
sudo chown -R blackbox:blackbox /etc/blackbox_exporter

# Step 3: Create systemd service file
sudo tee /etc/systemd/system/blackbox_exporter.service > /dev/null << EOF
[Unit]
Description=Blackbox Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=blackbox
Group=blackbox
Type=simple
ExecStart=/usr/local/bin/blackbox_exporter --config.file=/etc/blackbox_exporter/blackbox.yml
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Step 4: Reload systemd, enable and start Blackbox Exporter
sudo systemctl daemon-reload
sudo systemctl enable blackbox_exporter
sudo systemctl start blackbox_exporter

# Print success message
echo "Blackbox Exporter installation complete. Ensure the configuration file at /etc/blackbox_exporter/blackbox.yml is correctly set up."

# #!/bin/bash
# # scripts/install_blackbox_exporter.sh

# # Download Blackbox Exporter
# cd /tmp
# wget https://github.com/prometheus/blackbox_exporter/releases/download/v0.23.0/blackbox_exporter-0.23.0.linux-amd64.tar.gz
# tar xvfz blackbox_exporter-*.tar.gz
# cd blackbox_exporter-*

# # Copy binary and config to the correct location
# cp blackbox_exporter /usr/local/bin/
# mkdir -p /etc/blackbox_exporter
# cp blackbox.yml /etc/blackbox_exporter/

# # Create Blackbox Exporter systemd service
# cat > /etc/systemd/system/blackbox-exporter.service << EOF
# [Unit]
# Description=Blackbox Exporter
# Wants=network-online.target
# After=network-online.target

# [Service]
# User=root
# Group=root
# Type=simple
# ExecStart=/usr/local/bin/blackbox_exporter --config.file=/etc/blackbox_exporter/blackbox.yml --web.listen-address=":9115"

# [Install]
# WantedBy=multi-user.target
# EOF

# # Enable and start Blackbox Exporter
# systemctl daemon-reload
# systemctl enable blackbox-exporter
# systemctl start blackbox-exporter

# echo "Blackbox Exporter installation completed"