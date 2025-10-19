# Quick Start Guide - FAISS Index Setup

## Current Status

✓ Sample policy documents created  
✓ Build index script ready  
✓ .env file detected  
⚠ **Missing AWS_SESSION_TOKEN** (required for temporary credentials)

## What You Need to Do

### Step 1: Add Session Token to .env

Your AWS credentials are **temporary** (access key starts with `ASIA`), so you need to add the session token.

**Update your `.env` file to include all three values:**

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=ASIAQWPHOKTBKQU5GCIQ
AWS_SECRET_ACCESS_KEY=BbkWHQwEM4XYV1wOwsavAvs8Pk148ctGJ7gCJPs+
AWS_SESSION_TOKEN=your_session_token_here  # ← ADD THIS LINE
```

**Where to find your session token:**

1. **AWS Console** → Click your username (top right) → "Command line or programmatic access"
2. Copy the `AWS_SESSION_TOKEN` value
3. Paste it into your `.env` file

### Step 2: Test Your Credentials

Run the test script to verify everything is working:

```bash
python test_aws_credentials.py
```

You should see:
```
✓ AWS_ACCESS_KEY_ID: ASIAQWPH...
✓ AWS_SECRET_ACCESS_KEY: ********...
✓ AWS_SESSION_TOKEN: FwoGZXIv...
✓ Credentials valid!
✓ Bedrock access successful!
✓ All tests passed!
```

### Step 3: Build the Index

Once credentials are working, build the FAISS index:

```bash
python backend/storage/build_index.py
```

This will:
- Extract text from the 2 sample policy PDFs
- Generate embeddings using AWS Bedrock Titan
- Build FAISS index with 7 chunks
- Save to `data/policy_index.faiss` and `data/policy_metadata.json`

Expected output:
```
✓ FAISS index built successfully!
  - Total vectors: 7
  - Policy types: {'HO-3': 4, 'PAP': 3}
  - Index saved to: data/policy_index.faiss
```

## Alternative: Use Permanent Credentials

If you don't want to deal with session tokens (they expire), you can create permanent IAM user credentials:

1. Go to AWS IAM Console
2. Create new IAM user with `AmazonBedrockFullAccess` policy
3. Create access keys (will start with `AKIA`, not `ASIA`)
4. Update `.env`:

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...  # Permanent credentials
AWS_SECRET_ACCESS_KEY=...
# No AWS_SESSION_TOKEN needed
```

## Troubleshooting

### "The security token included in the request is invalid"

→ You're missing `AWS_SESSION_TOKEN` in your `.env` file (see Step 1 above)

### "Unable to locate credentials"

→ Make sure `.env` file is in the project root directory

### "Access Denied"

→ Your IAM user/role needs `AmazonBedrockFullAccess` policy

### Credentials expired

→ Temporary credentials expire after a few hours. Get fresh ones from AWS Console.

## Files Created

✓ `backend/storage/build_index.py` - Index builder script  
✓ `backend/storage/create_sample_policies.py` - Sample policy generator  
✓ `data/policies/HO3_specimen_policy.pdf` - Sample homeowners policy  
✓ `data/policies/PAP_specimen_policy.pdf` - Sample auto policy  
✓ `test_aws_credentials.py` - Credential testing script  
✓ `.env.example` - Example environment file  
✓ `AWS_CREDENTIALS_GUIDE.md` - Detailed credential setup guide  

## Next Steps

After building the index:

1. The application will automatically load it on startup
2. Agents can query policy clauses with semantic search
3. No need to rebuild unless you add/update policies

## Need More Help?

See `AWS_CREDENTIALS_GUIDE.md` for detailed troubleshooting and setup instructions.
