# app.py
import os
import pwd
import json
import boto3
import subprocess
import traceback
import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import yaml
import jinja2

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = '/opt/observability/ansible/keys'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Ensure the keys directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_configuration_type')
def get_configuration_type():
    return render_template('configuration_type.html')

@app.route('/select_monitoring_server', methods=['POST'])
def select_monitoring_server():
    config_type = request.form.get('config_type')
    session['config_type'] = config_type
    
    if config_type == 'monitoring':
        return render_template('select_monitoring_server.html')
    else:
        return render_template('random_script.html')

@app.route('/get_ec2_instances')
def get_ec2_instances():
    region = request.args.get('region', 'us-east-1')
    
    # Comprehensive list of AWS regions including Mumbai (ap-south-1)
    all_regions = [
        'us-east-1',      # US East (N. Virginia)
        'us-east-2',      # US East (Ohio)
        'us-west-1',      # US West (N. California)
        'us-west-2',      # US West (Oregon)
        'ap-south-1',     # Asia Pacific (Mumbai)
        'ap-northeast-1', # Asia Pacific (Tokyo)
        'ap-northeast-2', # Asia Pacific (Seoul)
        'ap-northeast-3', # Asia Pacific (Osaka)
        'ap-southeast-1', # Asia Pacific (Singapore)
        'ap-southeast-2', # Asia Pacific (Sydney)
        'ap-southeast-3', # Asia Pacific (Jakarta)
        'ca-central-1',   # Canada (Central)
        'eu-central-1',   # Europe (Frankfurt)
        'eu-west-1',      # Europe (Ireland)
        'eu-west-2',      # Europe (London)
        'eu-west-3',      # Europe (Paris)
        'eu-north-1',     # Europe (Stockholm)
        'sa-east-1',      # South America (São Paulo)
        'af-south-1',     # Africa (Cape Town)
        'me-south-1',     # Middle East (Bahrain)
        'me-central-1'    # Middle East (UAE)
    ]
    
    # Initialize boto3 client with explicit region
    ec2_client = boto3.client('ec2', region_name=region)
    
    # Get instances in the specified region
    instances = []
    try:
        response = ec2_client.describe_instances()
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                if instance['State']['Name'] == 'running':
                    instance_info = {
                        'id': instance['InstanceId'],
                        'public_ip': instance.get('PublicIpAddress', 'N/A'),
                        'private_ip': instance.get('PrivateIpAddress', 'N/A'),
                        'key_name': instance.get('KeyName', 'N/A'),
                        'region': region
                    }
                    instances.append(instance_info)
    except Exception as e:
        return jsonify({'error': str(e), 'instances': [], 'regions': all_regions})
    
    return jsonify({'instances': instances, 'regions': all_regions})
    
@app.route('/select_monitoring_server_submit', methods=['POST'])
def select_monitoring_server_submit():
    monitoring_server = request.form.get('monitoring_server')
    session['monitoring_server'] = json.loads(monitoring_server)
    
    return redirect(url_for('select_monitored_servers'))

@app.route('/select_monitored_servers')
def select_monitored_servers():
    return render_template('select_monitored_servers.html')

@app.route('/select_monitored_servers_submit', methods=['POST'])
def select_monitored_servers_submit():
    monitored_servers = request.form.getlist('monitored_servers')
    session['monitored_servers'] = [json.loads(server) for server in monitored_servers]
    
    return redirect(url_for('select_monitoring_tools'))

@app.route('/select_monitoring_tools')
def select_monitoring_tools():
    return render_template('select_monitoring_tools.html')

@app.route('/select_monitored_tools')
def select_monitored_tools():
    return render_template('select_monitored_tools.html')

@app.route('/select_monitoring_tools_submit', methods=['POST'])
def select_monitoring_tools_submit():
    monitoring_tools = request.form.getlist('monitoring_tools')
    session['monitoring_tools'] = monitoring_tools
    
    return redirect(url_for('select_monitored_tools'))

@app.route('/select_monitored_tools_submit', methods=['POST'])
def select_monitored_tools_submit():
    monitored_tools = request.form.getlist('monitored_tools')
    session['monitored_tools'] = monitored_tools
    
    return redirect(url_for('enter_role_arn'))

@app.route('/enter_role_arn')
def enter_role_arn():
    return render_template('enter_role_arn.html')

@app.route('/deploy', methods=['POST'])
def deploy():
    role_arn = request.form.get('role_arn')
    session['role_arn'] = role_arn
    
    # Create the ansible inventory file
    create_inventory()
    
    # Create the prometheus config file
    create_prometheus_config()
    
    # Create the ansible playbook
    create_playbook()
    
    # Execute the playbook - this now includes adding summary info and URLs
    result = execute_playbook()
    
    # Simply render the template with the complete result
    return render_template('deployment_result.html', result=result)

def save_key_mapping(instance_id, key_path):
    key_mapping_file = '/opt/observability/ansible/key_mapping.json'
    try:
        if os.path.exists(key_mapping_file):
            with open(key_mapping_file, 'r') as f:
                key_mapping = json.load(f)
        else:
            key_mapping = {}
        
        key_mapping[instance_id] = key_path
        
        with open(key_mapping_file, 'w') as f:
            json.dump(key_mapping, f)
        
        # Set permissions
        os.chmod(key_mapping_file, 0o644)
        print(f"Saved key mapping: {instance_id} -> {key_path}")
    except Exception as e:
        print(f"Error saving key mapping: {str(e)}")

def get_key_path(instance_id):
    # First try to get from session
    session_keys = session.get('instance_keys', {})
    if instance_id in session_keys and session_keys[instance_id]:
        return session_keys[instance_id]
    
    # If not in session, try from the mapping file
    key_mapping_file = '/opt/observability/ansible/key_mapping.json'
    if os.path.exists(key_mapping_file):
        try:
            with open(key_mapping_file, 'r') as f:
                key_mapping = json.load(f)
            if instance_id in key_mapping and key_mapping[instance_id]:
                return key_mapping[instance_id]
        except Exception as e:
            print(f"Error reading key mapping: {str(e)}")
    
    return None

@app.route('/upload_key/<instance_id>', methods=['POST'])
def upload_key(instance_id):
    if 'key_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})
    
    file = request.files['key_file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'})
    
    if file:
        filename = secure_filename(instance_id + "_" + file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Set proper permissions for the key
        os.chmod(file_path, 0o600)
        
        # Change ownership to ubuntu user if running as root
        try:
            import pwd
            ubuntu_uid = pwd.getpwnam('ubuntu').pw_uid
            ubuntu_gid = pwd.getpwnam('ubuntu').pw_gid
            os.chown(file_path, ubuntu_uid, ubuntu_gid)
            print(f"Changed ownership of {file_path} to ubuntu user")
        except (ImportError, KeyError) as e:
            print(f"Warning: Could not change ownership to ubuntu: {str(e)}")
        
        # Verify the file exists and has correct permissions
        if os.path.exists(file_path):
            os.system(f"ls -la {file_path}")
        
        # Store the key path in session and persistent storage
        if 'instance_keys' not in session:
            session['instance_keys'] = {}
        
        session['instance_keys'][instance_id] = file_path
        save_key_mapping(instance_id, file_path)
        
        return jsonify({'success': True, 'message': 'Key uploaded successfully', 'key_path': file_path})

def create_inventory():
    inventory = {
        'all': {
            'hosts': {}
        },
        'monitoring': {
            'hosts': {}
        },
        'clients': {
            'hosts': {}
        }
    }

    # Add monitoring server
    monitoring_server = session.get('monitoring_server')
    server_id = monitoring_server['id']
    key_path = get_key_path(server_id)
    
    print(f"Monitoring server ID: {server_id}, Key path: {key_path}")

    # Ensure the key has proper permissions
    if key_path and os.path.exists(key_path):
        os.chmod(key_path, 0o600)
        try:
            import pwd
            ubuntu_uid = pwd.getpwnam('ubuntu').pw_uid
            ubuntu_gid = pwd.getpwnam('ubuntu').pw_gid
            os.chown(key_path, ubuntu_uid, ubuntu_gid)
            print(f"Changed ownership of {key_path} to ubuntu user")
        except (ImportError, KeyError) as e:
            print(f"Warning: Could not change ownership to ubuntu: {str(e)}")

    # Use private IP for SSH connection
    inventory['all']['hosts'][server_id] = {
        'ansible_host': monitoring_server['private_ip'],
        'ansible_user': 'ubuntu',
        'ansible_ssh_private_key_file': key_path,
        'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes',
        'private_ip': monitoring_server['private_ip'],
        'ansible_become': True
    }

    inventory['monitoring']['hosts'][server_id] = None

    # Add monitored servers
    for server in session.get('monitored_servers', []):
        server_id = server['id']
        key_path = get_key_path(server_id)
        
        print(f"Client server ID: {server_id}, Key path: {key_path}")

        # Ensure the key has proper permissions
        if key_path and os.path.exists(key_path):
            os.chmod(key_path, 0o600)
            try:
                import pwd
                ubuntu_uid = pwd.getpwnam('ubuntu').pw_uid
                ubuntu_gid = pwd.getpwnam('ubuntu').pw_gid
                os.chown(key_path, ubuntu_uid, ubuntu_gid)
                print(f"Changed ownership of {key_path} to ubuntu user")
            except (ImportError, KeyError) as e:
                print(f"Warning: Could not change ownership to ubuntu: {str(e)}")

        # Use private IP for SSH connection
        inventory['all']['hosts'][server_id] = {
            'ansible_host': server['private_ip'],
            'ansible_user': 'ubuntu',
            'ansible_ssh_private_key_file': key_path,
            'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes',
            'private_ip': server['private_ip'],
            'ansible_become': True
        }

        inventory['clients']['hosts'][server_id] = None

    # Write inventory to file
    inventory_path = '/opt/observability/ansible/inventory.yaml'
    with open(inventory_path, 'w') as f:
        yaml.dump(inventory, f)
    
    # Debug - print the inventory
    print(f"Generated inventory: {inventory}")

def execute_playbook():
    role_arn = session.get('role_arn', '')
    
    # Set environment variable for AWS role
    os.environ['AWS_ROLE_ARN'] = role_arn
    
    # Make sure inventory and playbook files exist
    inventory_path = '/opt/observability/ansible/inventory.yaml'
    playbook_path = '/opt/observability/ansible/playbook.yaml'
    
    if not os.path.exists(inventory_path) or not os.path.exists(playbook_path):
        return {
            'success': False,
            'output': 'Inventory or playbook file missing',
            'error': f'Check if {inventory_path} and {playbook_path} exist'
        }
    
    # Fix permissions for all keys one more time
    for server_id, key_path in session.get('instance_keys', {}).items():
        if key_path and os.path.exists(key_path):
            os.chmod(key_path, 0o600)
            try:
                import pwd
                ubuntu_uid = pwd.getpwnam('ubuntu').pw_uid
                ubuntu_gid = pwd.getpwnam('ubuntu').pw_gid
                os.chown(key_path, ubuntu_uid, ubuntu_gid)
                print(f"Final permission fix for {key_path}")
            except Exception as e:
                print(f"Error fixing permissions: {str(e)}")
    
    # Execute the ansible playbook with verbose output
    cmd = [
        'sudo', '-u', 'ubuntu',
        'ansible-playbook',
        '-i', inventory_path,
        playbook_path,
        '-vvv',
    ]
    
    try:
        print(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=600)
        
        # Add additional details to the result for better feedback
        monitoring_server = session.get('monitoring_server', {})
        monitored_servers = session.get('monitored_servers', [])
        
        # Add deployment summary
        summary = {
            'monitoring_server': {
                'id': monitoring_server.get('id', 'N/A'),
                'ip': monitoring_server.get('public_ip', 'N/A'),
                'tools': session.get('monitoring_tools', [])
            },
            'monitored_servers': [
                {
                    'id': server.get('id', 'N/A'),
                    'ip': server.get('public_ip', 'N/A')
                } for server in monitored_servers
            ],
            'client_tools': session.get('monitored_tools', []),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        output = {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None,
            'summary': summary
        }
        
        # Get Grafana access URL if Prometheus+Grafana was installed
        if 'prometheus+grafana' in session.get('monitoring_tools', []):
            output['grafana_url'] = f"http://{monitoring_server.get('public_ip', 'your-server-ip')}:3000"
            output['prometheus_url'] = f"http://{monitoring_server.get('public_ip', 'your-server-ip')}:9090"
        
        return output
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': 'Command timed out after 10 minutes',
            'error': 'Timeout error'
        }
    except Exception as e:
        return {
            'success': False,
            'output': f'Error executing Ansible playbook: {str(e)}',
            'error': traceback.format_exc()
        }
 
def create_prometheus_config():
    # Read template
    with open('/opt/observability/prometheus.yml.j2', 'r') as f:
        template_content = f.read()
    
    # Get monitoring server and monitored servers
    monitoring_server = session.get('monitoring_server')
    monitored_servers = session.get('monitored_servers', [])
    
    # Create a Jinja2 environment and template
    env = jinja2.Environment()
    template = env.from_string(template_content)
    
    # Create a mock context with the necessary variables
    context = {
        'groups': {
            'clients': [f'client_{i}' for i in range(len(monitored_servers))]
        },
        'hostvars': {}
    }
    
    # Add the host variables using private IPs
    for i, server in enumerate(monitored_servers):
        host_key = f'client_{i}'
        context['hostvars'][host_key] = {
            'ansible_host': server['private_ip']  # Use private IP for Prometheus scraping
        }
    
    # Render the template
    rendered_config = template.render(context)
    
    # Write the rendered config to a file
    config_path = '/opt/observability/ansible/prometheus.yml'
    with open(config_path, 'w') as f:
        f.write(rendered_config)

def create_playbook():
    monitoring_tools = session.get('monitoring_tools', [])
    monitored_tools = session.get('monitored_tools', [])
    
    # Create the playbook content
    playbook = [
        {
            'name': 'Deploy Monitoring Tools',
            'hosts': 'monitoring',
            'become': True,
            'tasks': []
        },
        {
            'name': 'Deploy Client Tools',
            'hosts': 'clients',
            'become': True,
            'tasks': []
        }
    ]
    
    # Add tasks for monitoring tools
    for tool in monitoring_tools:
        script_name = tool_to_script(tool)
        # Replace + with _ in register variable names
        register_var = tool.replace('+', '_').replace(' ', '_') + '_result'
        playbook[0]['tasks'].append({
            'name': f'Install {tool}',
            'script': f'/opt/observability/ansible/scripts/{script_name}',
            'register': register_var
        })
    
    # Add tasks for monitored tools
    for tool in monitored_tools:
        script_name = tool_to_script(tool)
        # Replace + with _ in register variable names
        register_var = tool.replace('+', '_').replace(' ', '_') + '_result'
        playbook[1]['tasks'].append({
            'name': f'Install {tool}',
            'script': f'/opt/observability/ansible/scripts/{script_name}',
            'register': register_var
        })
    
    # Add task to copy prometheus config
    if 'prometheus+grafana' in monitoring_tools:
        playbook[0]['tasks'].append({
            'name': 'Copy Prometheus Config',
            'copy': {
                'src': '/opt/observability/ansible/prometheus.yml',
                'dest': '/etc/prometheus/prometheus.yml'
            }
        })
        
        # Add task to restart prometheus
        playbook[0]['tasks'].append({
            'name': 'Restart Prometheus',
            'service': {
                'name': 'prometheus',
                'state': 'restarted'
            }
        })
    
    # Write playbook to file
    playbook_path = '/opt/observability/ansible/playbook.yaml'
    with open(playbook_path, 'w') as f:
        yaml.dump(playbook, f)

def tool_to_script(tool):
    script_map = {
        'prometheus+grafana': 'install_prometheus_grafana.sh',
        'node exporter': 'install_node_exporter.sh',
        'process exporter': 'install_process_exporter.sh',
        'blackbox exporter': 'install_blackbox_exporter.sh',
        'cloudwatch exporter': 'install_cloudwatch_exporter.sh',
        'alertmanager': 'install_alertmanager.sh'
    }
    
    return script_map.get(tool, '')
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)