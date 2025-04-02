import boto3
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_s3_bucket():
    # Initialize S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )
    
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    
    # Read CORS configuration
    with open('s3_cors_config.json', 'r') as f:
        cors_config = json.load(f)
    
    # Apply CORS configuration
    s3_client.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration=cors_config
    )
    print(f"Applied CORS configuration to bucket: {bucket_name}")
    
    # Create bucket policy for public access
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }
    
    # Apply bucket policy
    s3_client.put_bucket_policy(
        Bucket=bucket_name,
        Policy=json.dumps(bucket_policy)
    )
    print(f"Applied public access policy to bucket: {bucket_name}")
    
    # Configure bucket for public access
    s3_client.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': False,
            'IgnorePublicAcls': False,
            'BlockPublicPolicy': False,
            'RestrictPublicBuckets': False
        }
    )
    print(f"Enabled public access for bucket: {bucket_name}")

if __name__ == "__main__":
    setup_s3_bucket() 