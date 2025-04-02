import boto3
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_cloudfront():
    # Initialize CloudFront client
    cloudfront_client = boto3.client(
        'cloudfront',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )
    
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    # Create CloudFront distribution
    distribution_config = {
        'Origins': {
            'Quantity': 1,
            'Items': [
                {
                    'Id': f'{bucket_name}-origin',
                    'DomainName': f'{bucket_name}.s3.{region}.amazonaws.com',
                    'S3OriginConfig': {
                        'OriginAccessIdentity': ''
                    }
                }
            ]
        },
        'DefaultCacheBehavior': {
            'TargetOriginId': f'{bucket_name}-origin',
            'ForwardedValues': {
                'QueryString': False,
                'Cookies': {
                    'Forward': 'none'
                }
            },
            'ViewerProtocolPolicy': 'redirect-to-https',
            'AllowedMethods': {
                'Quantity': 2,
                'Items': ['GET', 'HEAD'],
                'CachedMethods': {
                    'Quantity': 2,
                    'Items': ['GET', 'HEAD']
                }
            },
            'MinTTL': 0,
            'DefaultTTL': 86400,
            'MaxTTL': 31536000,
            'Compress': True
        },
        'Enabled': True,
        'Comment': f'Distribution for {bucket_name}',
        'DefaultRootObject': '',
        'PriceClass': 'PriceClass_100',
        'HttpVersion': 'http2',
        'CallerReference': str(int(time.time()))  # Add unique caller reference
    }
    
    try:
        # Create the distribution
        response = cloudfront_client.create_distribution(
            DistributionConfig=distribution_config
        )
        
        # Get the distribution domain name
        distribution_domain = response['Distribution']['DomainName']
        distribution_id = response['Distribution']['Id']
        distribution_arn = response['Distribution']['ARN']
        
        print(f"Created CloudFront distribution: {distribution_domain}")
        print(f"Distribution ID: {distribution_id}")
        print(f"Distribution ARN: {distribution_arn}")
        
        # Update .env file with CloudFront information
        env_file = '.env'
        with open(env_file, 'a') as f:
            f.write(f"\nCLOUDFRONT_DOMAIN={distribution_domain}")
            f.write(f"\nCLOUDFRONT_DISTRIBUTION_ID={distribution_id}")
            f.write(f"\nCLOUDFRONT_DISTRIBUTION_ARN={distribution_arn}")
        
        print(f"Updated {env_file} with CloudFront information")
        
    except Exception as e:
        print(f"Error creating CloudFront distribution: {str(e)}")
        raise

if __name__ == "__main__":
    setup_cloudfront() 