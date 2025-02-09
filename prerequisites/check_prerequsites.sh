#!/bin/bash

# Check Python 3
echo "Checking Python 3:"
if command -v python3 &>/dev/null; then
  python3 --version
else
  echo "Python 3 is NOT installed."
fi

echo ""  # Add a newline for better formatting

# Check pip3
echo "Checking pip3:"
if command -v pip3 &>/dev/null; then
  pip3 --version
else
  echo "pip3 is NOT installed."
fi

echo ""

# Check Flask
echo "Checking Flask:"
if python3 -c "import flask; print(flask.__version__)" 2>/dev/null; then
  python3 -c "import flask; print(flask.__version__)"
else
  echo "Flask is NOT installed."
fi

echo ""

# Check Flask-CORS
echo "Checking Flask-CORS:"
if python3 -c "import flask_cors; print('Flask-CORS is installed')" 2>/dev/null; then
  echo "Flask-CORS is installed."
else
  echo "Flask-CORS is NOT installed."
fi

echo ""

# Check boto3
echo "Checking boto3:"
if python3 -c "import boto3; print(boto3.__version__)" 2>/dev/null; then
  python3 -c "import boto3; print(boto3.__version__)"
else
  echo "boto3 is NOT installed."
fi

echo ""

# Check Terraform
echo "Checking Terraform:"
if command -v terraform &>/dev/null; then
  terraform --version
else
  echo "Terraform is NOT installed."
fi

echo ""

# Check AWS CLI
echo "Checking AWS CLI:"
if command -v aws &>/dev/null; then
  aws --version
else
  echo "AWS CLI is NOT installed."
fi

echo ""

# Check Nginx
echo "Checking Nginx:"
if command -v nginx &>/dev/null; then
  nginx -v
else
  echo "Nginx is NOT installed."
fi

echo ""

# Check if AWS credentials file exists
echo "Checking AWS Credentials file:"
if [ -f ~/.aws/credentials ]; then
  echo "AWS credentials file exists."
else
  echo "AWS credentials file DOES NOT exist."
fi

echo ""

echo "Prerequisite checks complete."
