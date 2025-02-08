from flask import Flask, request, jsonify
import boto3
import subprocess
import os

app = Flask(__name__)

# Replace with your actual values (for demonstration only - NOT for production)
AWS_ACCESS_KEY_ID = "AKIAS4T6KVMBEEX7O26P"
AWS_SECRET_ACCESS_KEY = "HvGtLSIHrXCKOftfnW46riCd8OawQoQ3AuSdTCfv"

REGION = "ap-south-1"  # e.g., "us-east-1"
ROLE_NAME = "MonitoringToolRole"
POLICY_NAME = "MonitoringToolPolicy"

if __name__ == '__main__':
    # Copy HTML file (adjust paths if needed)
    try:
        subprocess.run(['sudo', 'cp', '/home/ubuntu/aws-monitoring-tool/frontend/index.html', '/var/www/html/'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error copying HTML file: {e}")

    # Restart Nginx
    try:
        subprocess.run(['sudo', 'systemctl', 'restart', 'nginx'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error restarting Nginx: {e}")

    app.run(debug=True)  # debug=True for development only
    
@app.route('/api/configure', methods=['POST'])
def configure_monitoring():
    try:
        data = request.get_json()
        instance_id = data['instanceId']
        threshold = data['threshold']

        # Set environment variables for AWS credentials (less secure, but for demonstration)
        os.environ['AWS_ACCESS_KEY_ID'] = AWS_ACCESS_KEY_ID
        os.environ['AWS_SECRET_ACCESS_KEY'] = AWS_SECRET_ACCESS_KEY

        # 1. Create/Check IAM Role and Policy (Automated)
        iam = boto3.client('iam')

        # Check if the role exists
        try:
            iam.get_role(RoleName=ROLE_NAME)
        except iam.NoSuchEntityException:
            # Create the role if it doesn't exist
            role = iam.create_role(
                RoleName=ROLE_NAME,
                AssumeRolePolicyDocument= """{
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "ec2.amazonaws.com"  # Or lambda.amazonaws.com if you deploy to Lambda
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                }"""
            )

        # Create the policy if it doesn't exist (or update it if you want dynamic permissions)
        try:
           iam.get_policy(PolicyArn=f'arn:aws:iam::your_account_id:policy/MonitoringToolPolicy')
        except iam.NoSuchEntityException:
            policy = iam.create_policy(
                PolicyName=POLICY_NAME,
                PolicyDocument=f"""{{
                    "Version": "2012-10-17",
                    "Statement": [
                        {{
                            "Effect": "Allow",
                            "Action": [
                                "cloudwatch:*",
                                "sns:*"
                            ],
                            "Resource": "*"
                        }}
                    ]
                }}"""
            )
        # Attach the policy to the Role
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn=f'arn:aws:iam::your_account_id:policy/MonitoringToolPolicy'
        )



        # 2. Generate and Execute Terraform (as before)
        # ... (rest of the code for Terraform execution is the same)

        return jsonify({'message': 'Monitoring configured successfully!'})

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)