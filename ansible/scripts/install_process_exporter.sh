#!/bin/bash
curl -LO https://github.com/ncabatoff/process-exporter/releases/download/v0.7.10/process-exporter-0.7.10.linux-amd64.tar.gz
tar xzvf process-exporter-*.linux-amd64.tar.gz
cp -rvi process-exporter-*.linux-amd64/process-exporter /usr/local/bin
useradd --no-create-home --shell /bin/false process_exporter

tee /etc/process-exporter.yml > /dev/null << EOF
process_names:
  - name: "{{.Comm}}"
    cmdline:
    - '.+'
EOF

tee /etc/systemd/system/process-exporter.service > /dev/null << EOF
[Unit]
Description=process_exporter
Wants=network-online.target
After=network-online.target

[Service]
User=process_exporter
Type=simple
ExecStart=/usr/local/bin/process-exporter --config.path /etc/process-exporter.yml
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl start process-exporter
systemctl enable process-exporter

# #!/bin/bash
# # scripts/install_process_exporter.sh

# # Download Process Exporter
# cd /tmp
# wget https://github.com/ncabatoff/process-exporter/releases/download/v0.7.10/process-exporter-0.7.10.linux-amd64.tar.gz
# tar xvfz process-exporter-*.tar.gz
# cd process-exporter-*

# # Copy binary to the correct location
# cp process-exporter /usr/local/bin/

# # Create default config
# mkdir -p /etc/process-exporter
# cat > /etc/process-exporter/config.yml << EOF
# process_names:
#   - name: "{{.Comm}}"
#     cmdline:
#     - '.+'
# EOF

# # Create Process Exporter systemd service
# cat > /etc/systemd/system/process-exporter.service << EOF
# [Unit]
# Description=Process Exporter
# Wants=network-online.target
# After=network-online.target

# [Service]
# User=root
# Group=root
# Type=simple
# ExecStart=/usr/local/bin/process-exporter --config.path=/etc/process-exporter/config.yml --web.listen-address=":9256"

# [Install]
# WantedBy=multi-user.target
# EOF

# # Enable and start Process Exporter
# systemctl daemon-reload
# systemctl enable process-exporter
# systemctl start process-exporter

# echo "Process Exporter installation completed"