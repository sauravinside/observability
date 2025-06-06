#!/bin/bash
set -e

VERSION="1.8.2"
DOWNLOAD_URL="https://github.com/prometheus/node_exporter/releases/download/v${VERSION}/node_exporter-${VERSION}.linux-amd64.tar.gz"
INSTALL_DIR="/usr/local/bin"
SERVICE_FILE="/etc/systemd/system/node_exporter.service"

wget $DOWNLOAD_URL
tar xvfz node_exporter-*.tar.gz
sudo mv node_exporter-${VERSION}.linux-amd64/node_exporter $INSTALL_DIR
rm -r node_exporter-${VERSION}.linux-amd64*
sudo useradd -rs /bin/false node_exporter || true

sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
Restart=on-failure
RestartSec=5s
ExecStart=$INSTALL_DIR/node_exporter

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter

# #!/bin/bash
# # scripts/install_node_exporter.sh

# # Download Node Exporter
# cd /tmp
# wget https://github.com/prometheus/node_exporter/releases/download/v1.4.0/node_exporter-1.4.0.linux-amd64.tar.gz
# tar xvfz node_exporter-*.tar.gz
# cd node_exporter-*

# # Copy binary to the correct location
# cp node_exporter /usr/local/bin/

# # Create Node Exporter systemd service
# cat > /etc/systemd/system/node_exporter.service << EOF
# [Unit]
# Description=Node Exporter
# Wants=network-online.target
# After=network-online.target

# [Service]
# User=root
# Group=root
# Type=simple
# ExecStart=/usr/local/bin/node_exporter

# [Install]
# WantedBy=multi-user.target
# EOF

# # Enable and start Node Exporter
# systemctl daemon-reload
# systemctl enable node_exporter
# systemctl start node_exporter

# echo "Node Exporter installation completed"