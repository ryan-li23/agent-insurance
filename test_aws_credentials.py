"""Test script to verify AWS credentials and Bedrock access."""

import os
import sys
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

def test_credentials():
    """Test AWS credentials and Bedrock access."""
    print("=" * 60)
    print("AWS Credentials Test")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("1. Checking environment variables...")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    
    if not aws_access_key:
        print("   ✗ AWS_ACCESS_KEY_ID not found in .env")
        return False
    else:
        print(f"   ✓ AWS_ACCESS_KEY_ID: {aws_access_key[:8]}...")
    
    if not aws_secret_key:
        print("   ✗ AWS_SECRET_ACCESS_KEY not found in .env")
        return False
    else:
        print(f"   ✓ AWS_SECRET_ACCESS_KEY: {'*' * 8}...")
    
    print(f"   ✓ AWS_REGION: {aws_region}")
    
    # Check if temporary credentials
    if aws_access_key.startswith("ASIA"):
        print("   ℹ Using temporary credentials (ASIA...)")
        if not aws_session_token:
            print("   ✗ AWS_SESSION_TOKEN not found - REQUIRED for temporary credentials!")
            print()
            print("   Add AWS_SESSION_TOKEN to your .env file:")
            print("   AWS_SESSION_TOKEN=your_session_token_here")
            return False
        else:
            print(f"   ✓ AWS_SESSION_TOKEN: {aws_session_token[:8]}...")
    else:
        print("   ℹ Using permanent credentials (AKIA...)")
    
    print()
    
    # Test AWS STS (verify credentials work)
    print("2. Testing AWS credentials with STS...")
    try:
        sts = boto3.client('sts', region_name=aws_region)
        identity = sts.get_caller_identity()
        print(f"   ✓ Credentials valid!")
        print(f"   ✓ Account: {identity['Account']}")
        print(f"   ✓ User ARN: {identity['Arn']}")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"   ✗ Credentials invalid: {error_code}")
        print(f"   ✗ Error: {error_msg}")
        return False
    except Exception as e:
        print(f"   ✗ Unexpected error: {str(e)}")
        return False
    
    print()
    
    # Test Bedrock access
    print("3. Testing AWS Bedrock access...")
    try:
        bedrock = boto3.client('bedrock', region_name=aws_region)
        models = bedrock.list_foundation_models()
        print(f"   ✓ Bedrock access successful!")
        print(f"   ✓ Found {len(models.get('modelSummaries', []))} foundation models")
        
        # Check for specific models we need
        model_ids = [m['modelId'] for m in models.get('modelSummaries', [])]
        
        if 'amazon.nova-pro-v1:0' in model_ids:
            print("   ✓ Nova Pro model available")
        else:
            print("   ⚠ Nova Pro model not found (may not be available in this region)")
        
        if any('titan-embed' in m for m in model_ids):
            print("   ✓ Titan embedding model available")
        else:
            print("   ⚠ Titan embedding model not found")
            
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"   ✗ Bedrock access failed: {error_code}")
        print(f"   ✗ Error: {error_msg}")
        print()
        print("   Possible causes:")
        print("   - Bedrock not available in your region (try us-east-1)")
        print("   - IAM user/role lacks Bedrock permissions")
        print("   - Need to attach AmazonBedrockFullAccess policy")
        return False
    except Exception as e:
        print(f"   ✗ Unexpected error: {str(e)}")
        return False
    
    print()
    
    # Test Bedrock Runtime (for embeddings)
    print("4. Testing Bedrock Runtime (for embeddings)...")
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=aws_region)
        
        # Try to invoke the embedding model with a test string
        import json
        response = bedrock_runtime.invoke_model(
            modelId='amazon.titan-embed-text-v2:0',
            body=json.dumps({"inputText": "test"}),
            contentType='application/json',
            accept='application/json'
        )
        
        result = json.loads(response['body'].read())
        embedding = result.get('embedding', [])
        
        print(f"   ✓ Bedrock Runtime access successful!")
        print(f"   ✓ Generated test embedding (dimension: {len(embedding)})")
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        print(f"   ✗ Bedrock Runtime failed: {error_code}")
        print(f"   ✗ Error: {error_msg}")
        
        if error_code == 'UnrecognizedClientException':
            print()
            print("   This error usually means:")
            print("   - Missing AWS_SESSION_TOKEN (for temporary credentials)")
            print("   - Expired credentials")
            print("   - Invalid credentials")
        
        return False
    except Exception as e:
        print(f"   ✗ Unexpected error: {str(e)}")
        return False
    
    print()
    print("=" * 60)
    print("✓ All tests passed! Your AWS credentials are working.")
    print("=" * 60)
    print()
    print("You can now run the index builder:")
    print("  python backend/storage/build_index.py")
    print()
    
    return True


if __name__ == "__main__":
    success = test_credentials()
    sys.exit(0 if success else 1)
