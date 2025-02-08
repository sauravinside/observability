terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0" # Or your preferred version
    }
  }
}

provider "aws" {
  region = "your_region"
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "EC2-CPU-High-i-xxxxxxxxxxxxxxxxx" # Example Instance ID
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "60"
  statistic           = "Average"
  threshold           = "80" # Example Threshold
  dimensions = {
    InstanceId = "i-xxxxxxxxxxxxxxxxx" # Example Instance ID
  }
  alarm_actions = [aws_sns_topic.alarm_topic.arn]
}

resource "aws_sns_topic" "alarm_topic" {
  name = "ec2_alarm_topic"
}

resource "aws_sns_topic_subscription" "email_subscription" {
  topic_arn = aws_sns_topic.alarm_topic.arn
  protocol  = "email"
  endpoint  = "your_email@example.com"
}