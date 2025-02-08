from flask import Flask, request, jsonify
import boto3
import json
import os
import subprocess
import shutil
from botocore.exceptions import ClientError
from flask_cors import CORS
from typing import Dict, List, Union
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Get the frontend directory path
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')

def setup_nginx() -> None:
    """Setup nginx, frontend files, and reverse proxy configuration"""
    try:
        # Create directories if they don't exist
        os.makedirs('/var/www/html/css', exist_ok=True)
        os.makedirs('/var/www/html/js', exist_ok=True)
        
        # Copy frontend files to web root
        shutil.copy(os.path.join(FRONTEND_DIR, 'index.html'), '/var/www/html/')
        shutil.copy(os.path.join(FRONTEND_DIR, 'css/styles.css'), '/var/www/html/css/')
        shutil.copy(os.path.join(FRONTEND_DIR, 'js/script.js'), '/var/www/html/js/')

        # Create Nginx configuration with proxy settings
        nginx_config = """
        server {
            listen 80;
            server_name _;

            location / {
                root /var/www/html;
                try_files $uri $uri/ /index.html;
            }

            location /api {
                proxy_pass http://localhost:5000;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Forwarded-Proto $scheme;
            }
        }
        """
        
        # Write configuration file
        temp_path = '/tmp/nginx_default'
        with open(temp_path, 'w') as f:
            f.write(nginx_config.strip())
        
        # Move config file and test
        subprocess.run(['sudo', 'mv', temp_path, '/etc/nginx/sites-available/default'], check=True)
        subprocess.run(['sudo', 'nginx', '-t'], check=True)
        
        # Set permissions
        subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', '/var/www/html'])
        subprocess.run(['sudo', 'chmod', '-R', '755', '/var/www/html'])
        
        # Restart nginx
        subprocess.run(['sudo', 'systemctl', 'restart', 'nginx'], check=True)
        logger.info("Nginx setup completed successfully")
    except Exception as e:
        logger.error(f"Error setting up nginx: {str(e)}")
        raise

def create_aws_client(service: str, region: str = None) -> boto3.client:
    """
    Create an AWS client with proper error handling
    
    Args:
        service (str): AWS service name (e.g., 'ec2', 'cloudwatch')
        region (str, optional): AWS region name
        
    Returns:
        boto3.client: AWS service client
    """
    try:
        if region:
            return boto3.client(service, region_name=region)
        return boto3.client(service)
    except Exception as e:
        logger.error(f"Error creating AWS {service} client: {str(e)}")
        raise

@app.route('/api/regions')
def get_regions() -> Dict:
    """Get all available AWS regions"""
    try:
        # Use a default region (e.g., us-east-1) to initialize the client
        ec2 = create_aws_client('ec2', region='us-east-1')
        response = ec2.describe_regions()
        regions = [region['RegionName'] for region in response['Regions']]
        return jsonify(regions)
    except Exception as e:
        logger.error(f"Error fetching regions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/instances/<region>')
def get_instances(region: str) -> Dict:
    """
    Get EC2 instances in the specified region
    
    Args:
        region (str): AWS region name
    """
    try:
        ec2 = create_aws_client('ec2', region)
        instances = ec2.describe_instances()['Reservations']
        instance_list = []
        
        for reservation in instances:
            for instance in reservation['Instances']:
                if instance['State']['Name'] == 'running':
                    instance_info = {
                        'InstanceId': instance['InstanceId'],
                        'Type': instance['InstanceType'],
                        'State': instance['State']['Name'],
                        'Name': 'Unnamed'
                    }
                    
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            instance_info['Name'] = tag['Value']
                            break
                    
                    instance_list.append(instance_info)
        
        return jsonify(instance_list)
    except Exception as e:
        logger.error(f"Error fetching instances for region {region}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/configure', methods=['POST'])
def configure_monitoring() -> Dict:
    """Configure CloudWatch monitoring and alerts for specified instances"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['region', 'instanceIds', 'metrics', 'alerts', 'thresholds']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        region = data['region']
        instance_ids = data['instanceIds']
        metrics = data['metrics']
        alerts = data['alerts']
        thresholds = data['thresholds']

        sns = create_aws_client('sns', region)
        cloudwatch = create_aws_client('cloudwatch', region)

        # Create SNS topic
        topic_name = f"EC2_Monitoring_Alerts_{'-'.join(instance_ids)}"
        try:
            topic_response = sns.create_topic(Name=topic_name)
            topic_arn = topic_response['TopicArn']
        except ClientError as e:
            logger.error(f"Error creating SNS topic: {str(e)}")
            return jsonify({'error': f'Failed to create SNS topic: {str(e)}'}), 500

        # Create CloudWatch alarms
        alarm_arns = []
        if alerts:
            for instance_id in instance_ids:
                for metric in metrics:
                    try:
                        alarm_name = f"{instance_id}-{metric}-Alarm"
                        cloudwatch.put_metric_alarm(
                            AlarmName=alarm_name,
                            MetricName=metric,
                            Namespace="AWS/EC2",
                            Statistic="Average",
                            Period=300,
                            EvaluationPeriods=2,
                            Threshold=float(thresholds[metric]),
                            ComparisonOperator="GreaterThanThreshold",
                            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                            AlarmActions=[topic_arn],
                            OKActions=[topic_arn]
                        )
                        alarm_arns.append(alarm_name)
                    except ClientError as e:
                        logger.error(f"Error creating alarm for {instance_id}: {str(e)}")
                        return jsonify({'error': f'Failed to create alarm for {instance_id}: {str(e)}'}), 500

        # Create CloudWatch dashboard
        dashboard_name = f"EC2-Monitor-{'-'.join(instance_ids)}"
        widgets = []
        x_pos = 0
        y_pos = 0
        
        for instance_id in instance_ids:
            for metric in metrics:
                widgets.append({
                    "type": "metric",
                    "x": x_pos,
                    "y": y_pos,
                    "width": 8,
                    "height": 6,
                    "properties": {
                        "metrics": [["AWS/EC2", metric, "InstanceId", instance_id]],
                        "period": 300,
                        "stat": "Average",
                        "region": region,
                        "title": f"{instance_id} - {metric}"
                    }
                })
                x_pos = (x_pos + 8) % 24
                if x_pos == 0:
                    y_pos += 6

        try:
            cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps({"widgets": widgets})
            )
        except ClientError as e:
            logger.error(f"Error creating dashboard: {str(e)}")
            return jsonify({'error': f'Failed to create dashboard: {str(e)}'}), 500

        return jsonify({
            'message': 'Monitoring configured successfully!',
            'snsTopicArn': topic_arn,
            'topicName': topic_name,
            'dashboardName': dashboard_name,
            'dashboardUrl': f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name={dashboard_name}",
            'alarms': alarm_arns
        })

    except Exception as e:
        logger.error(f"Unexpected error in configure_monitoring: {str(e)}")
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    try:
        # Verify AWS credentials
        sts = create_aws_client('sts')
        sts.get_caller_identity()
        logger.info("AWS credentials verified successfully")
        
        # Setup nginx
        setup_nginx()
        
        # Run Flask app
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise