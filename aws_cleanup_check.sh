#!/bin/bash

# Script to identify potential "ghost" resources in AWS Free Tier
# Usage: ./aws_cleanup_check.sh

echo "Checking for Unused Resources..."

# 1. Check for Unattached EBS Volumes (Costly if not cleaned)
echo "---------------------------------------------------"
echo "Checking for Available (Unattached) EBS Volumes..."
aws ec2 describe-volumes --filters Name=status,Values=available --query "Volumes[*].{ID:VolumeId,Size:Size,Status:Status,Created:CreateTime}" --output table

# 2. Check for Unassociated Elastic IPs
echo "---------------------------------------------------"
echo "Checking for Unassociated Elastic IPs..."
aws ec2 describe-addresses --filters Name=association-id,Values=null --query "Addresses[*].{PublicIp:PublicIp,AllocationId:AllocationId}" --output table

# 3. Check for Stopped EC2 Instances (that might be forgotten)
echo "---------------------------------------------------"
echo "Checking for Stopped EC2 Instances..."
aws ec2 describe-instances --filters Name=instance-state-name,Values=stopped --query "Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,Type:InstanceType,Name:Tags[?Key=='Name']|[0].Value}" --output table

# 4. Check for Old Snapshots (owned by self)
echo "---------------------------------------------------"
echo "Checking for Snapshots..."
aws ec2 describe-snapshots --owner-ids self --query "Snapshots[*].{ID:SnapshotId,VolumeSize:VolumeSize,StartTime:StartTime}" --output table

# 5. Check for Load Balancers (often forgotten)
echo "---------------------------------------------------"
echo "Checking for Load Balancers..."
aws elbv2 describe-load-balancers --query "LoadBalancers[*].{ARN:LoadBalancerArn,DNS:DNSName,State:State.Code}" --output table

echo "---------------------------------------------------"
echo "Review the above resources. To delete a resource, use the AWS Console or CLI commands like:"
echo "  aws ec2 delete-volume --volume-id <vol-id>"
echo "  aws ec2 release-address --allocation-id <alloc-id>"
echo "  aws ec2 terminate-instances --instance-ids <inst-id>"
