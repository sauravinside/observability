import os
import urllib.request
import json

# Function to download dashboards by ID
def download_dashboard(dashboard_id, output_path):
    """
    Download a Grafana dashboard JSON by its ID
    """
    url = f"https://grafana.com/api/dashboards/{dashboard_id}/revisions/latest/download"
    try:
        # Download the dashboard JSON
        with urllib.request.urlopen(url) as response:
            dashboard_json = json.loads(response.read().decode('utf-8'))
            
        # Update the dashboard to use the default Prometheus data source
        if '__inputs' in dashboard_json:
            for input_item in dashboard_json.get('__inputs', []):
                if input_item['name'] == 'DS_PROMETHEUS':
                    # Remove the inputs section as we're setting a default data source
                    input_var = input_item['name']
                    # Replace all occurrences of the variable with the default Prometheus data source
                    dashboard_str = json.dumps(dashboard_json)
                    dashboard_str = dashboard_str.replace(f"${{{input_var}}}", "Prometheus")
                    dashboard_json = json.loads(dashboard_str)
            
            # Remove the __inputs section as it's no longer needed
            if '__inputs' in dashboard_json:
                del dashboard_json['__inputs']
        
        # Write the modified dashboard to file
        with open(output_path, 'w') as f:
            json.dump(dashboard_json, f, indent=2)
            
        print(f"Successfully downloaded and modified dashboard {dashboard_id} to {output_path}")
        return True
    except Exception as e:
        print(f"Error downloading dashboard {dashboard_id}: {str(e)}")
        return False

# Setup the directory structure for Grafana provisioning
def setup_grafana_provisioning():
    """
    Create the necessary directory structure for Grafana provisioning
    """
    # Base directories
    grafana_provisioning_base = '/etc/grafana/provisioning'
    dashboards_dir = f"{grafana_provisioning_base}/dashboards"
    datasources_dir = f"{grafana_provisioning_base}/datasources"
    dashboards_json_dir = f"/var/lib/grafana/dashboards"
    
    # Create directories if they don't exist
    os.makedirs(dashboards_dir, exist_ok=True)
    os.makedirs(datasources_dir, exist_ok=True)
    os.makedirs(dashboards_json_dir, exist_ok=True)
    
    # Create datasource configuration for Prometheus
    datasource_yaml = """apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    version: 1
    editable: true
"""
    
    # Write the datasource configuration
    with open(f"{datasources_dir}/prometheus.yaml", 'w') as f:
        f.write(datasource_yaml)
    
    # Create dashboard provider configuration
    dashboard_provider_yaml = """apiVersion: 1
providers:
  - name: 'default'
    orgId: 1
    folder: 'Monitoring'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
"""
    
    # Write the dashboard provider configuration
    with open(f"{dashboards_dir}/default.yaml", 'w') as f:
        f.write(dashboard_provider_yaml)
    
    # Download the required dashboards
    node_exporter_path = f"{dashboards_json_dir}/node-exporter-full.json"
    process_exporter_path = f"{dashboards_json_dir}/process-exporter.json"
    
    download_dashboard(1860, node_exporter_path)
    download_dashboard(22161, process_exporter_path)
    
    # Set proper permissions for the dashboard files
    os.system(f"chown -R grafana:grafana {dashboards_json_dir}")
    os.system(f"chown -R grafana:grafana {grafana_provisioning_base}")
    
    print("Grafana provisioning setup completed")
    return True

# Main function to be called from the install script
if __name__ == "__main__":
    setup_grafana_provisioning()