#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Variables
PROMETHEUS_VERSION="3.1.0"
PROMETHEUS_ARCHIVE="prometheus-$PROMETHEUS_VERSION.linux-amd64.tar.gz"
PROMETHEUS_URL="https://github.com/prometheus/prometheus/releases/download/v$PROMETHEUS_VERSION/$PROMETHEUS_ARCHIVE"
PROMETHEUS_DIR="prometheus-$PROMETHEUS_VERSION.linux-amd64"

# Step 1: Download and extract Prometheus
wget $PROMETHEUS_URL

tar xvfz $PROMETHEUS_ARCHIVE
rm $PROMETHEUS_ARCHIVE

# Step 2: Create necessary directories
sudo mkdir -p /etc/prometheus /var/lib/prometheus

# Step 3: Move binaries and configuration
cd $PROMETHEUS_DIR
sudo mv prometheus promtool /usr/local/bin/
sudo mv prometheus.yml /etc/prometheus/prometheus.yml
#sudo mv consoles/ console_libraries/ /etc/prometheus/

# Step 4: Create Prometheus user
sudo useradd -rs /bin/false prometheus
sudo chown -R prometheus: /etc/prometheus /var/lib/prometheus

# Step 5: Create systemd service file
sudo tee /etc/systemd/system/prometheus.service > /dev/null << EOF
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
Restart=on-failure
RestartSec=5s
ExecStart=/usr/local/bin/prometheus \\
    --config.file /etc/prometheus/prometheus.yml \\
    --storage.tsdb.path /var/lib/prometheus/ \\
    --web.console.templates=/etc/prometheus/consoles \\
    --web.console.libraries=/etc/prometheus/console_libraries \\
    --web.listen-address=0.0.0.0:9090 \\
    --web.enable-lifecycle \\
    --log.level=info

[Install]
WantedBy=multi-user.target
EOF

# Step 6: Reload systemd, enable and start Prometheus
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus

# Print success message
echo "Prometheus installation and configuration complete. Access it at http://<your-server-ip>:9090"

# Exit immediately if a command exits with a non-zero status
set -e

# Step 1: Install prerequisites
sudo apt-get install -y software-properties-common wget

# Step 2: Add Grafana GPG key and repository
sudo wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key
echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list

# Step 3: Update package list and install Grafana
sudo apt-get update
sudo apt-get install -y grafana

# Step 3.5: Create provisioning directory if it doesn't exist
echo "Setting up Grafana provisioning directory..."
sudo mkdir -p /etc/grafana/provisioning/datasources
sudo chown -R grafana:grafana /etc/grafana/provisioning

# Add Prometheus datasource configuration
echo "Adding Prometheus as the default datasource for Grafana..."
sudo tee /etc/grafana/provisioning/datasources/prometheus-datasource.yaml > /dev/null <<EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    url: http://localhost:9090
    access: proxy
    isDefault: true
EOF

# Ensure proper permissions
sudo chown grafana:grafana /etc/grafana/provisioning/datasources/prometheus-datasource.yaml

# Step 4: Start and enable Grafana service
sudo systemctl daemon-reload
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Print success message
echo "Grafana installation complete. Access it at http://<your-server-ip>:3000 with default credentials (admin/admin)."

# #!/bin/bash
# # scripts/install_prometheus_grafana.sh

# # Update package lists
# apt-get update

# # Install dependencies
# apt-get install -y apt-transport-https software-properties-common wget

# # Add Grafana GPG key and repository
# wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -
# echo "deb https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list

# # Download Prometheus
# mkdir -p /tmp/prometheus && cd /tmp/prometheus
# wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
# tar xvfz prometheus-*.tar.gz
# cd /tmp/prometheus && cd prometheus-*

# # Setup Prometheus directories
# mkdir -p /etc/prometheus
# mkdir -p /var/lib/prometheus

# # Copy Prometheus files
# cp prometheus /usr/local/bin/
# cp promtool /usr/local/bin/
# cp -r consoles /etc/prometheus
# cp -r console_libraries /etc/prometheus

# # Create prometheus.yml if it doesn't exist
# if [ ! -f /etc/prometheus/prometheus.yml ]; then
#     cp prometheus.yml /etc/prometheus/prometheus.yml
# fi

# # Create Prometheus systemd service
# cat > /etc/systemd/system/prometheus.service << EOF
# [Unit]
# Description=Prometheus
# Wants=network-online.target
# After=network-online.target

# [Service]
# User=root
# Group=root
# Type=simple
# ExecStart=/usr/local/bin/prometheus \
#     --config.file /etc/prometheus/prometheus.yml \
#     --storage.tsdb.path /var/lib/prometheus/ \
#     --web.console.templates=/etc/prometheus/consoles \
#     --web.console.libraries=/etc/prometheus/console_libraries

# [Install]
# WantedBy=multi-user.target
# EOF

# # Update package lists again for Grafana
# apt-get update

# # Install Grafana
# apt-get install -y grafana

# # Create alert rules file if it doesn't exist
# if [ ! -f /etc/prometheus/alert.rules.yml ]; then
#     cat > /etc/prometheus/alert.rules.yml << EOF
# groups:
# - name: example
#   rules:
#   - alert: HighLoad
#     expr: node_load1 > 0.8
#     for: 5m
#     labels:
#       severity: warning
#     annotations:
#       summary: "High load on {{ \$labels.instance }}"
#       description: "{{ \$labels.instance }} has a high load ({{ \$value }})."
# EOF
# fi

# # Enable and start Prometheus and Grafana
# systemctl daemon-reload
# systemctl enable prometheus
# systemctl enable grafana-server
# systemctl start prometheus
# systemctl start grafana-server

# echo "Prometheus and Grafana installation completed"