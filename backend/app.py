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

# Updated AWS_SERVICES configuration in app.py

AWS_SERVICES = {
    'EC2': {
        'namespace': 'AWS/EC2',
        'dimension_key': 'InstanceId',
        'resource_type': 'instances',
        'list_function': 'describe_instances',
        'metrics': [
            {'name': 'CPUUtilization', 'namespace': 'AWS/EC2'},
            {
                'name': 'DiskSpaceUtilization',
                'namespace': 'CWAgent',
                'dimensions': [
                    {'Name': 'InstanceId', 'Value': '${aws:InstanceId}'},
                    {'Name': 'path', 'Value': '/'},
                    {'Name': 'device', 'Value': 'xvda1'},
                    {'Name': 'fstype', 'Value': 'ext4'}
                ]
            },
            {'name': 'MemoryUtilization', 'namespace': 'CWAgent'},
            {'name': 'NetworkIn', 'namespace': 'AWS/EC2'},
            {'name': 'NetworkOut', 'namespace': 'AWS/EC2'}
        ]
    },
    'RDS': {
        'namespace': 'AWS/RDS',
        'dimension_key': 'DBInstanceIdentifier',
        'resource_type': 'db_instances',
        'list_function': 'describe_db_instances',
        'metrics': [
            {'name': 'CPUUtilization', 'namespace': 'AWS/RDS'},
            {'name': 'FreeableMemory', 'namespace': 'AWS/RDS'},
            {'name': 'FreeStorageSpace', 'namespace': 'AWS/RDS'},
            {'name': 'DatabaseConnections', 'namespace': 'AWS/RDS'},
            {'name': 'ReadIOPS', 'namespace': 'AWS/RDS'},
            {'name': 'WriteIOPS', 'namespace': 'AWS/RDS'}
        ]
    },
    'Lambda': {
        'namespace': 'AWS/Lambda',
        'dimension_key': 'FunctionName',
        'resource_type': 'functions',
        'list_function': 'list_functions',
        'metrics': [
            {'name': 'Invocations', 'namespace': 'AWS/Lambda'},
            {'name': 'Errors', 'namespace': 'AWS/Lambda'},
            {'name': 'Duration', 'namespace': 'AWS/Lambda'},
            {'name': 'Throttles', 'namespace': 'AWS/Lambda'},
            {'name': 'ConcurrentExecutions', 'namespace': 'AWS/Lambda'},
            {'name': 'IteratorAge', 'namespace': 'AWS/Lambda'}
        ]
    },
    'DynamoDB': {
        'namespace': 'AWS/DynamoDB',
        'dimension_key': 'TableName',
        'resource_type': 'tables',
        'list_function': 'list_tables',
        'metrics': [
            {'name': 'ConsumedReadCapacityUnits', 'namespace': 'AWS/DynamoDB'},
            {'name': 'ConsumedWriteCapacityUnits', 'namespace': 'AWS/DynamoDB'},
            {'name': 'ReadThrottleEvents', 'namespace': 'AWS/DynamoDB'},
            {'name': 'WriteThrottleEvents', 'namespace': 'AWS/DynamoDB'},
            {'name': 'SuccessfulRequestLatency', 'namespace': 'AWS/DynamoDB'},
            {'name': 'SystemErrors', 'namespace': 'AWS/DynamoDB'}
        ]
    },
    'ECS': {
        'namespace': 'AWS/ECS',
        'dimension_key': 'ClusterName',
        'resource_type': 'clusters',
        'list_function': 'list_clusters',
        'metrics': [
            {'name': 'CPUUtilization', 'namespace': 'AWS/ECS'},
            {'name': 'MemoryUtilization', 'namespace': 'AWS/ECS'},
            {'name': 'RunningTaskCount', 'namespace': 'AWS/ECS'},
            {'name': 'PendingTaskCount', 'namespace': 'AWS/ECS'},
            {'name': 'StorageReadBytes', 'namespace': 'AWS/ECS'},
            {'name': 'StorageWriteBytes', 'namespace': 'AWS/ECS'}
        ]
    },
    'ElastiCache': {
        'namespace': 'AWS/ElastiCache',
        'dimension_key': 'CacheClusterId',
        'resource_type': 'cache_clusters',
        'list_function': 'describe_cache_clusters',
        'metrics': [
            {'name': 'CPUUtilization', 'namespace': 'AWS/ElastiCache'},
            {'name': 'FreeableMemory', 'namespace': 'AWS/ElastiCache'},
            {'name': 'NetworkBytesIn', 'namespace': 'AWS/ElastiCache'},
            {'name': 'NetworkBytesOut', 'namespace': 'AWS/ElastiCache'},
            {'name': 'CurrConnections', 'namespace': 'AWS/ElastiCache'},
            {'name': 'CacheHits', 'namespace': 'AWS/ElastiCache'},
            {'name': 'CacheMisses', 'namespace': 'AWS/ElastiCache'}
        ]
    },
    'ELB': {
        'namespace': 'AWS/ELB',
        'dimension_key': 'LoadBalancerName',
        'resource_type': 'load_balancers',
        'list_function': 'describe_load_balancers',
        'metrics': [
            {'name': 'RequestCount', 'namespace': 'AWS/ELB'},
            {'name': 'HealthyHostCount', 'namespace': 'AWS/ELB'},
            {'name': 'UnHealthyHostCount', 'namespace': 'AWS/ELB'},
            {'name': 'Latency', 'namespace': 'AWS/ELB'},
            {'name': 'HTTPCode_Backend_2XX', 'namespace': 'AWS/ELB'},
            {'name': 'HTTPCode_Backend_5XX', 'namespace': 'AWS/ELB'}
        ]
    },
    'SQS': {
        'namespace': 'AWS/SQS',
        'dimension_key': 'QueueName',
        'resource_type': 'queues',
        'list_function': 'list_queues',
        'metrics': [
            {'name': 'ApproximateNumberOfMessagesVisible', 'namespace': 'AWS/SQS'},
            {'name': 'ApproximateNumberOfMessagesNotVisible', 'namespace': 'AWS/SQS'},
            {'name': 'ApproximateAgeOfOldestMessage', 'namespace': 'AWS/SQS'},
            {'name': 'NumberOfMessagesReceived', 'namespace': 'AWS/SQS'},
            {'name': 'NumberOfMessagesSent', 'namespace': 'AWS/SQS'},
            {'name': 'NumberOfMessagesDeleted', 'namespace': 'AWS/SQS'}
        ]
    },
    'S3': {
        'namespace': 'AWS/S3',
        'dimension_key': 'BucketName',
        'resource_type': 'buckets',
        'list_function': 'list_buckets',
        'metrics': [
            {'name': 'BucketSizeBytes', 'namespace': 'AWS/S3'},
            {'name': 'NumberOfObjects', 'namespace': 'AWS/S3'},
            {'name': 'AllRequests', 'namespace': 'AWS/S3'},
            {'name': '4xxErrors', 'namespace': 'AWS/S3'},
            {'name': '5xxErrors', 'namespace': 'AWS/S3'},
            {'name': 'FirstByteLatency', 'namespace': 'AWS/S3'},
            {'name': 'TotalRequestLatency', 'namespace': 'AWS/S3'}
        ]
    }
}

def setup_nginx() -> None:
    """Setup nginx, frontend files, and reverse proxy configuration"""
    try:
        os.makedirs('/var/www/html/css', exist_ok=True)
        os.makedirs('/var/www/html/js', exist_ok=True)
        
        shutil.copy(os.path.join(FRONTEND_DIR, 'index.html'), '/var/www/html/')
        shutil.copy(os.path.join(FRONTEND_DIR, 'css/styles.css'), '/var/www/html/css/')
        shutil.copy(os.path.join(FRONTEND_DIR, 'js/script.js'), '/var/www/html/js/')

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
        
        temp_path = '/tmp/nginx_default'
        with open(temp_path, 'w') as f:
            f.write(nginx_config.strip())
        
        subprocess.run(['sudo', 'mv', temp_path, '/etc/nginx/sites-available/default'], check=True)
        subprocess.run(['sudo', 'nginx', '-t'], check=True)
        subprocess.run(['sudo', 'chown', '-R', 'www-data:www-data', '/var/www/html'])
        subprocess.run(['sudo', 'chmod', '-R', '755', '/var/www/html'])
        subprocess.run(['sudo', 'systemctl', 'restart', 'nginx'], check=True)
        logger.info("Nginx setup completed successfully")
    except Exception as e:
        logger.error(f"Error setting up nginx: {str(e)}")
        raise

def create_aws_client(service: str, region: str = None) -> boto3.client:
    try:
        if region:
            return boto3.client(service, region_name=region)
        return boto3.client(service)
    except Exception as e:
        logger.error(f"Error creating AWS {service} client: {str(e)}")
        raise

@app.route('/api/services')
def get_services() -> Dict:
    """Get available AWS services for monitoring"""
    try:
        services = list(AWS_SERVICES.keys())
        return jsonify(services)
    except Exception as e:
        logger.error(f"Error fetching services: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/regions')
def get_regions() -> Dict:
    try:
        ec2 = create_aws_client('ec2', region='us-east-1')
        response = ec2.describe_regions()
        regions = [region['RegionName'] for region in response['Regions']]
        return jsonify(regions)
    except Exception as e:
        logger.error(f"Error fetching regions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/resources/<service>/<region>')
def get_resources(service: str, region: str) -> Dict:
    """Get resources for specified service and region"""
    try:
        service_config = AWS_SERVICES.get(service.upper())
        if not service_config:
            return jsonify({'error': 'Invalid service'}), 400

        client = create_aws_client(service.lower(), region)
        resources = []

        if service.upper() == 'EC2':
            instances = client.describe_instances()['Reservations']
            for reservation in instances:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] == 'running':
                        resources.append({
                            'Id': instance['InstanceId'],
                            'Type': instance['InstanceType'],
                            'State': instance['State']['Name'],
                            'Name': next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'Unnamed')
                        })

        elif service.upper() == 'RDS':
            instances = client.describe_db_instances()['DBInstances']
            resources = [{
                'Id': instance['DBInstanceIdentifier'],
                'Type': instance['DBInstanceClass'],
                'State': instance['DBInstanceStatus'],
                'Name': instance.get('DBName', instance['DBInstanceIdentifier'])
            } for instance in instances]

        elif service.upper() == 'LAMBDA':
            functions = client.list_functions()['Functions']
            resources = [{
                'Id': function['FunctionName'],
                'Type': function['Runtime'],
                'State': function['State'] if 'State' in function else 'Active',
                'Name': function['FunctionName']
            } for function in functions]

        elif service.upper() == 'DYNAMODB':
            tables = client.list_tables()['TableNames']
            resources = [{
                'Id': table,
                'Type': 'DynamoDB Table',
                'State': 'Active',
                'Name': table
            } for table in tables]

        elif service.upper() == 'ECS':
            clusters = client.list_clusters()['clusterArns']
            for cluster_arn in clusters:
                cluster_name = cluster_arn.split('/')[-1]
                resources.append({
                    'Id': cluster_name,
                    'Type': 'ECS Cluster',
                    'State': 'Active',
                    'Name': cluster_name
                })

        elif service.upper() == 'ELASTICACHE':
            clusters = client.describe_cache_clusters()['CacheClusters']
            resources = [{
                'Id': cluster['CacheClusterId'],
                'Type': cluster['Engine'],
                'State': cluster['CacheClusterStatus'],
                'Name': cluster['CacheClusterId']
            } for cluster in clusters]

        elif service.upper() == 'ELB':
            lbs = client.describe_load_balancers()['LoadBalancerDescriptions']
            resources = [{
                'Id': lb['LoadBalancerName'],
                'Type': 'Classic Load Balancer',
                'State': 'Active',
                'Name': lb['LoadBalancerName']
            } for lb in lbs]

        elif service.upper() == 'SQS':
            queues = client.list_queues()['QueueUrls']
            resources = [{
                'Id': queue.split('/')[-1],
                'Type': 'SQS Queue',
                'State': 'Active',
                'Name': queue.split('/')[-1]
            } for queue in queues]

        elif service.upper() == 'S3':
            buckets = client.list_buckets()['Buckets']
            resources = [{
                'Id': bucket['Name'],
                'Type': 'S3 Bucket',
                'State': 'Active',
                'Name': bucket['Name']
            } for bucket in buckets]

        return jsonify(resources)
    except Exception as e:
        logger.error(f"Error fetching resources for {service} in {region}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/metrics/<service>')
def get_metrics(service: str) -> Dict:
    """Get available metrics for specified service"""
    try:
        service_config = AWS_SERVICES.get(service.upper())
        if not service_config:
            return jsonify({'error': 'Invalid service'}), 400
            
        return jsonify(service_config['metrics'])
    except Exception as e:
        logger.error(f"Error fetching metrics for {service}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/configure', methods=['POST'])
def configure_monitoring() -> Dict:
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['region', 'service', 'resources', 'metrics', 'alerts', 'thresholds']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        region = data['region']
        service = data['service'].upper()
        resources = data['resources']
        metrics = data['metrics']
        alerts = data['alerts']
        thresholds = data['thresholds']

        service_config = AWS_SERVICES.get(service)
        if not service_config:
            return jsonify({'error': 'Invalid service'}), 400

        sns = create_aws_client('sns', region)
        cloudwatch = create_aws_client('cloudwatch', region)

        # Create SNS topic
        topic_name = f"{service}_Monitoring_Alerts_{'-'.join(resources)}"
        try:
            topic_response = sns.create_topic(Name=topic_name)
            topic_arn = topic_response['TopicArn']
        except ClientError as e:
            logger.error(f"Error creating SNS topic: {str(e)}")
            return jsonify({'error': f'Failed to create SNS topic: {str(e)}'}), 500

        # Create CloudWatch alarms
        alarm_arns = []
        if alerts:
            for resource_id in resources:
                for metric in metrics:
                    try:
                        alarm_name = f"{resource_id}-{metric['name']}-Alarm"
                        alarm_config = {
                            'AlarmName': alarm_name,
                            'MetricName': metric['name'],
                            'Namespace': metric['namespace'],
                            'Statistic': 'Average',
                            'Period': 300,
                            'EvaluationPeriods': 2,
                            'Threshold': float(thresholds[metric['name']]),
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'AlarmActions': [topic_arn],
                            'OKActions': [topic_arn]
                        }

                        # Add dimensions based on service and metric
                        dimensions = [{'Name': service_config['dimension_key'], 'Value': resource_id}]
                        if 'dimension' in metric:
                            dimensions.append(metric['dimension'])
                        alarm_config['Dimensions'] = dimensions

                        cloudwatch.put_metric_alarm(**alarm_config)
                        alarm_arns.append(alarm_name)
                    except ClientError as e:
                        logger.error(f"Error creating alarm for {resource_id}: {str(e)}")
                        return jsonify({'error': f'Failed to create alarm for {resource_id}: {str(e)}'}), 500

        # Create CloudWatch dashboard
        dashboard_name = f"{service}-Monitor-{'-'.join(resources)}"
        widgets = []
        x_pos = 0
        y_pos = 0

        widgets = []
        for metric in metrics:
            metric_data = [
                [metric['namespace'], metric['name']]  # First row: Namespace & Metric Name
            ]
            for resource_id in resources:
                dimensions = [[service_config['dimension_key'], resource_id]]

                if metric['namespace'] == 'CWAgent':
                    dimensions = [['InstanceId', resource_id]]
                    if metric['name'] == 'DiskSpaceUtilization':
                        dimensions.append(['path', '/'])  # Adjust as needed
                        dimensions.append(['device', 'xvda1'])
                        dimensions.append(['fstype', 'ext4'])
                metric_data.append([
                    metric['namespace'], metric['name'],
                    *[item for dim in dimensions for item in [dim[0], dim[1]]]
                ])
            widgets.append({
                "type": "metric",
                "x": 0,
                "y": len(widgets) * 6,  # Stack widgets vertically
                "width": 24,
                "height": 6,
                "properties": {
                    "metrics": metric_data,
                    "period": 300,
                    "stat": "Average",
                    "region": region,
                    "title": f"{metric['name']} across {len(resources)} instances"
                }
            })

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
        sts = create_aws_client('sts')
        sts.get_caller_identity()
        logger.info("AWS credentials verified successfully")
        
        setup_nginx()
        
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise