# AWS Credentials Setup Guide

## Finding Your AWS Credentials

### Step 1: Get Your AWS Access Keys

1. **Log in to AWS Console**: https://console.aws.amazon.com/
2. **Click your username** in the top-right corner
3. **Select "Security credentials"** from the dropdown
4. **Scroll down to "Access keys"** section
5. **Click "Create access key"**
   - Choose use case: "Command Line Interface (CLI)"
   - Check the confirmation box
   - Click "Next" and then "Create access key"
6. **IMPORTANT**: Copy both:
   - **Access key ID** (looks like: `AKIAIOSFODNN7EXAMPLE`)
   - **Secret access key** (looks like: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)
   - ⚠️ **Save these immediately** - you can't view the secret key again!

### Step 2: Find Your AWS Region

Your Bedrock region is where you enabled Nova and Titan. Common regions:
- `us-east-1` (US East - N. Virginia) - Most common
- `us-west-2` (US West - Oregon)
- `eu-west-1` (Europe - Ireland)

To verify your region:
1. Go to AWS Bedrock Console: https://console.aws.amazon.com/bedrock/
2. Look at the region selector in the top-right corner
3. Note the region code (e.g., `us-east-1`)

## Configuration Methods

### Method 1: Environment Variables (Recommended for Development)

#### On Windows (PowerShell):

```powershell
# Set for current session
$env:AWS_REGION = "us-east-1"
$env:AWS_ACCESS_KEY_ID = "YOUR_ACCESS_KEY_ID"
$env:AWS_SECRET_ACCESS_KEY = "YOUR_SECRET_ACCESS_KEY"

# Verify they're set
echo $env:AWS_REGION
echo $env:AWS_ACCESS_KEY_ID
```

#### On Windows (Command Prompt):

```cmd
set AWS_REGION=us-east-1
set AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
set AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
```

#### On Linux/Mac:

```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
```

**Note**: These environment variables only last for the current terminal session.

### Method 2: Create .env File (Persistent for Project)

Create a `.env` file in your project root:

```bash
# .env file
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
```

**Important**: Add `.env` to your `.gitignore` to avoid committing credentials!

Then install python-dotenv:
```bash
.venv\Scripts\activate & pip install python-dotenv
```

And update `backend/storage/build_index.py` to load the .env file (I can help with this).

### Method 3: AWS CLI Configuration (Persistent System-Wide)

If you have AWS CLI installed:

```bash
aws configure
```

It will prompt you for:
- AWS Access Key ID: `[paste your access key]`
- AWS Secret Access Key: `[paste your secret key]`
- Default region name: `us-east-1`
- Default output format: `json`

This saves credentials to `~/.aws/credentials` (works system-wide).

### Method 4: Windows System Environment Variables (Permanent)

For permanent Windows environment variables:

1. Press `Win + X` and select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", click "New"
5. Add three variables:
   - Variable name: `AWS_REGION`, Value: `us-east-1`
   - Variable name: `AWS_ACCESS_KEY_ID`, Value: `[your access key]`
   - Variable name: `AWS_SECRET_ACCESS_KEY`, Value: `[your secret key]`
6. Click OK and restart your terminal

## Verification

After setting credentials, verify they work:

```bash
# Activate virtual environment
.venv\Scripts\activate

# Test AWS connection (if AWS CLI installed)
aws bedrock list-foundation-models --region us-east-1

# Or test with Python
python -c "import boto3; print(boto3.client('bedrock-runtime', region_name='us-east-1').meta.region_name)"
```

## Security Best Practices

1. **Never commit credentials to Git**
   - Add `.env` to `.gitignore`
   - Never hardcode credentials in code

2. **Use IAM roles when possible**
   - If running on EC2/ECS, use IAM roles instead of access keys

3. **Rotate access keys regularly**
   - Create new keys every 90 days
   - Delete old keys after rotation

4. **Use least privilege**
   - Only grant Bedrock permissions needed:
     - `bedrock:InvokeModel`
     - `bedrock:InvokeModelWithResponseStream`

5. **Monitor usage**
   - Check AWS CloudTrail for API calls
   - Set up billing alerts

## Required AWS Permissions

Your IAM user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0",
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"
      ]
    }
  ]
}
```

## Troubleshooting

### "Unable to locate credentials"

**Problem**: AWS credentials not found

**Solutions**:
1. Verify environment variables are set: `echo $env:AWS_ACCESS_KEY_ID`
2. Check AWS CLI config: `cat ~/.aws/credentials`
3. Restart terminal after setting environment variables
4. Make sure you're in the correct terminal session

### "Access Denied" or "UnauthorizedOperation"

**Problem**: Credentials don't have Bedrock permissions

**Solutions**:
1. Go to AWS IAM Console
2. Find your IAM user
3. Attach policy: `AmazonBedrockFullAccess` (or create custom policy above)
4. Wait a few minutes for permissions to propagate

### "Region not supported"

**Problem**: Bedrock not available in your region

**Solutions**:
1. Verify Bedrock is enabled in your region
2. Try `us-east-1` (most widely supported)
3. Check AWS Bedrock availability: https://aws.amazon.com/bedrock/

### "Model not found"

**Problem**: Nova Pro or Titan not enabled

**Solutions**:
1. Go to AWS Bedrock Console
2. Click "Model access" in left sidebar
3. Click "Manage model access"
4. Enable:
   - Amazon Nova Pro (`amazon.nova-pro-v1:0`)
   - Amazon Titan Embeddings G1 - Text (`amazon.titan-embed-text-v2:0`)
5. Wait for "Access granted" status (can take a few minutes)

## Next Steps

After configuring credentials:

1. **Test the connection**:
   ```bash
   .venv\Scripts\activate
   python test_build_index.py
   ```

2. **Build the real index**:
   ```bash
   .venv\Scripts\activate
   python backend/storage/build_index.py
   ```

3. **Verify index was created**:
   ```bash
   dir data\policy_index.faiss
   dir data\policy_metadata.json
   ```

## Quick Reference

**Minimum required information:**
- ✅ AWS Access Key ID
- ✅ AWS Secret Access Key  
- ✅ AWS Region (where Bedrock is enabled)

**Minimum required permissions:**
- ✅ `bedrock:InvokeModel` for Nova Pro
- ✅ `bedrock:InvokeModel` for Titan Embeddings

**Models that must be enabled:**
- ✅ `amazon.nova-pro-v1:0`
- ✅ `amazon.titan-embed-text-v2:0`
