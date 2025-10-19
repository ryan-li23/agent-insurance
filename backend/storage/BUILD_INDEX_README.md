# FAISS Index Builder

This directory contains scripts for building and managing the FAISS vector index for policy document retrieval.

## Scripts

### `build_index.py`

Standalone script that builds a FAISS index from policy PDF documents.

**What it does:**
1. Scans `data/policies/` for PDF files
2. Extracts text from each PDF using PyPDF2
3. Infers policy type from filename (HO-3, PAP, etc.)
4. Chunks documents with overlap (500 tokens, 50 token overlap)
5. Generates embeddings using AWS Bedrock Titan
6. Builds FAISS index with cosine similarity
7. Saves index and metadata to disk

**Usage:**

```bash
# From project root directory
python backend/storage/build_index.py
```

**Prerequisites:**
- AWS credentials configured (via environment variables or AWS CLI)
- Policy PDF files in `data/policies/` directory
- Required Python packages installed (see requirements.txt)

**Environment Variables:**
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
```

**Output:**
- `data/policy_index.faiss` - FAISS index file
- `data/policy_metadata.json` - Metadata for each chunk (policy type, section, text, etc.)

### `create_sample_policies.py`

Script to create sample policy documents for testing and development.

**What it does:**
1. Creates a sample HO-3 (Homeowners) policy PDF
2. Creates a sample PAP (Personal Auto Policy) PDF
3. Saves both to `data/policies/` directory

**Usage:**

```bash
# From project root directory
python backend/storage/create_sample_policies.py
```

**Output:**
- `data/policies/HO3_specimen_policy.pdf` - Sample homeowners policy
- `data/policies/PAP_specimen_policy.pdf` - Sample auto policy

**Note:** These are sample documents with realistic policy language for testing purposes. They are not actual insurance policies.

## Policy Document Requirements

### Filename Conventions

The index builder infers policy type from filenames:

- **HO-3 (Homeowners)**: Filename should contain `ho3`, `ho-3`, or `homeowner`
  - Examples: `HO3_specimen_policy.pdf`, `homeowner_policy.pdf`
  
- **PAP (Personal Auto)**: Filename should contain `pap`, `auto`, or `personal auto`
  - Examples: `PAP_specimen_policy.pdf`, `auto_policy.pdf`

- **Unknown**: Any other filename will be classified as "Unknown" policy type

### Supported Formats

- PDF files only (`.pdf` extension)
- Text-based PDFs (not scanned images)
- Any size, but larger documents will take longer to process

## Index Configuration

Configuration is loaded from `config.yaml`:

```yaml
vector_store:
  index_path: data/policy_index.faiss
  metadata_path: data/policy_metadata.json
  dimension: 1024  # Titan embedding dimension
  chunk_size: 500  # Tokens per chunk
  chunk_overlap: 50  # Overlapping tokens
```

## Troubleshooting

### "No policy documents found"

**Problem:** The script can't find any PDF files in `data/policies/`

**Solution:** 
1. Run `create_sample_policies.py` to create sample documents
2. Or add your own policy PDF files to `data/policies/`

### "Unable to locate credentials"

**Problem:** AWS credentials are not configured

**Solution:**
1. Set environment variables:
   ```bash
   export AWS_REGION=us-east-1
   export AWS_ACCESS_KEY_ID=<your-key>
   export AWS_SECRET_ACCESS_KEY=<your-secret>
   ```
2. Or configure AWS CLI: `aws configure`
3. Or use IAM role (if running on EC2/ECS)

### "Failed to extract text from PDF"

**Problem:** PDF is corrupted or contains only images

**Solution:**
1. Verify PDF is valid and text-based
2. Try opening PDF in a viewer to confirm it contains text
3. If PDF is scanned images, you'll need OCR preprocessing

### "Index building takes too long"

**Problem:** Large policy documents or many documents

**Solution:**
1. This is normal - embedding generation takes time
2. Progress is logged every 100 chunks
3. Consider reducing `chunk_size` in config to create fewer chunks
4. Or process documents in batches

## Development

### Adding New Policy Types

To add support for new policy types:

1. Update `infer_policy_type()` in `build_index.py`:
   ```python
   def infer_policy_type(filename: str) -> str:
       filename_lower = filename.lower()
       
       if 'ho3' in filename_lower:
           return "HO-3"
       elif 'pap' in filename_lower:
           return "PAP"
       elif 'commercial' in filename_lower:  # New type
           return "Commercial"
       else:
           return "Unknown"
   ```

2. Add sample policy creation in `create_sample_policies.py` if needed

### Testing

To test the index builder without AWS credentials:

1. Mock the `BedrockClient.generate_embedding()` method
2. Return dummy embeddings (random vectors of dimension 1024)
3. Verify index structure and metadata

Example:
```python
import numpy as np

async def mock_embedding_generator(text: str):
    return np.random.rand(1024).astype(np.float32)

await vector_store.build_index(policy_documents, mock_embedding_generator)
```

## Dependencies

Required packages:
- `faiss-cpu>=1.7.4`: FAISS vector search
- `numpy>=1.24.0`: Array operations
- `PyPDF2>=3.0.0`: PDF text extraction
- `boto3>=1.34.0`: AWS Bedrock for embeddings
- `reportlab>=4.0.0`: PDF creation (for sample policies)

## Performance

Typical performance metrics:

- **PDF extraction**: ~1-2 seconds per document
- **Chunking**: ~0.1 seconds per document
- **Embedding generation**: ~0.5-1 second per chunk (depends on Bedrock API)
- **Index building**: ~0.1 seconds for FAISS operations

For 2 sample policies (~16KB text):
- Total chunks: ~7
- Total time: ~5-10 seconds (mostly embedding generation)

For production with 10+ policies:
- Expect several minutes for initial index build
- Index loading from disk: <1 second
