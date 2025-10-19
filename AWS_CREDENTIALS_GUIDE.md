# AWS Credentials Setup Guide

## Current Issue

You're using **temporary AWS credentials** (your access key starts with `ASIA`), which require a session token. The error message confirms this:

```
The security token included in the request is invalid.
```

## Solution: Add AWS_SESSION_TOKEN

Your temporary credentials need three values, not just two. Update your `.env` file:

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=ASIAQWPHOKTBKQU5GCIQ
AWS_SECRET_ACCESS_KEY=BbkWHQwEM4XYV1wOwsavAvs8Pk148ctGJ7gCJPs+
AWS_SESSION_TOKEN=your_session_token_here
```

## How to Get Your Session Token

### Option 1: AWS Console (Temporary Credentials)

If you're using AWS SSO or temporary credentials from the AWS Console:

1. Go to AWS Console
2. Click on your username (top right)
3. Click "Command line or programmatic access"
4. Copy all three values:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - AWS_SESSION_TOKEN

### Option 2: AWS CLI

If you have AWS CLI configured with SSO:

```bash
aws configure export-credentials --profile your-profile-name
```

This will show you all three values including the session token.

### Option 3: Check AWS Credentials File

Look in `~/.aws/credentials`:

```bash
cat ~/.aws/credentials
```

If you see `aws_session_token`, copy that value to your `.env` file.

## Alternative: Use Permanent IAM User Credentials

If you want to avoid dealing with session tokens, create permanent IAM user credentials:

1. Go to AWS IAM Console
2. Create a new IAM user (or use existing)
3. Attach policy: `AmazonBedrockFullAccess`
4. Create access keys (these will start with `AKIA`, not `ASIA`)
5. Update your `.env` file:

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...  # Permanent credentials start with AKIA
AWS_SECRET_ACCESS_KEY=...
# No AWS_SESSION_TOKEN needed for permanent credentials
```

## Verify Your Setup

After updating your `.env` file, test the credentials:

```bash
python backend/storage/build_index.py
```

You should see:
```
✓ AWS credentials loaded successfully
✓ AWS Region: us-east-1
✓ AWS Access Key: ASIAQWPH... (or AKIAQWPH... for permanent)
```

If using temporary credentials, you should also see:
```
✓ AWS Session Token: Found (temporary credentials)
```

## Troubleshooting

### "The security token included in the request is invalid"

**Cause:** Missing or expired session token

**Solutions:**
1. Add `AWS_SESSION_TOKEN` to your `.env` file
2. Or get fresh temporary credentials (they expire after a few hours)
3. Or switch to permanent IAM user credentials

### "Unable to locate credentials"

**Cause:** `.env` file not found or not loaded

**Solutions:**
1. Make sure `.env` file is in the project root directory
2. Make sure you're running the script from the project root
3. Check that `python-dotenv` is installed: `pip install python-dotenv`

### "Access Denied" or "Not Authorized"

**Cause:** Your IAM user/role doesn't have Bedrock permissions

**Solutions:**
1. Attach `AmazonBedrockFullAccess` policy to your IAM user/role
2. Or create a custom policy with these permissions:
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
         "Resource": "*"
       }
     ]
   }
   ```

### Temporary Credentials Expired

**Cause:** Temporary credentials typically expire after 1-12 hours

**Solutions:**
1. Get fresh credentials from AWS Console
2. Update all three values in `.env` (access key, secret key, session token)
3. Or switch to permanent credentials

## Security Best Practices

1. **Never commit `.env` to git** - It's already in `.gitignore`
2. **Use temporary credentials when possible** - More secure than permanent keys
3. **Rotate credentials regularly** - Especially permanent keys
4. **Use least privilege** - Only grant necessary Bedrock permissions
5. **Use AWS SSO** - Best practice for enterprise environments

## Next Steps

Once your credentials are working:

1. Run the index builder:
   ```bash
   python backend/storage/build_index.py
   ```

2. This will create:
   - `data/policy_index.faiss` - Vector index
   - `data/policy_metadata.json` - Chunk metadata

3. The application will automatically load the index on startup

## Need Help?

If you're still having issues:

1. Check AWS region - Make sure Bedrock is available in your region (us-east-1 recommended)
2. Verify Bedrock access - Try the AWS CLI: `aws bedrock list-foundation-models --region us-east-1`
3. Check IAM permissions - Make sure your user/role has Bedrock access
