# Claims Coverage Reasoner (A2A)

A multi-agent claims processing system powered by AWS Bedrock (Nova Pro, Titan) and FAISS vector search.

## Overview

This system uses three specialized AI agents to collaboratively process insurance claims:

- **Evidence Curator**: Extracts and normalizes claim evidence from documents and images
- **Policy Interpreter**: Maps claim facts to policy clauses using semantic search
- **Compliance Reviewer**: Adversarially challenges decisions and flags inconsistencies

## Architecture

- **Frontend**: Streamlit web interface for claim submission and review
- **Backend**: Multi-agent orchestration using AWS Bedrock Converse API (optional: Agents for Amazon Bedrock)
- **AI Models**: AWS Bedrock Nova Pro for reasoning, Titan for embeddings
- **Vector Store**: FAISS for semantic policy retrieval
- **Document Processing**: PDF extraction, image analysis, invoice parsing

## Quick Start

1. **Setup AWS Credentials**
   ```bash
   # Create .env file with your AWS credentials
   cp .env.example .env
   # Edit .env with your AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
   ```

2. **Install Dependencies**
   ```bash
   # Activate virtual environment
   .venv\Scripts\activate
   
   # Install requirements
   pip install -r requirements.txt
   ```

3. **Build Policy Index**
   ```bash
   # Build FAISS index from policy documents
   python backend/storage/build_index.py
   ```

4. **Run Application**
   ```bash
   # Start Streamlit UI
   streamlit run app.py
   ```

## Configuration

Edit `config.yaml` to customize:
- AWS Bedrock models and settings
- FAISS vector store parameters
- Agent behavior and instructions
- File storage locations

## Documentation

- [Quick Start Guide](QUICK_START.md) - Setup and first run
- [AWS Credentials Setup](AWS_CREDENTIALS_SETUP.md) - Detailed AWS configuration
- [Index Build Guide](INDEX_BUILD_SUCCESS.md) - FAISS index documentation

## Project Structure

```
├── app.py                      # Streamlit UI
├── config.yaml                 # Configuration
├── requirements.txt            # Dependencies
├── backend/
│   ├── reasoner.py            # Main orchestration
│   ├── agents/                # AI agents
│   ├── models/                # Data models
│   ├── orchestration/         # Multi-agent coordination
│   ├── plugins/               # Document processing tools
│   ├── storage/               # FAISS vector store
│   └── utils/                 # Utilities and configuration
├── data/                      # Policy documents and indexes
└── .kiro/                     # Development specs and guidelines
```

## Features

- ✅ Multi-agent collaboration with debate and consensus
- ✅ Semantic policy search with FAISS
- ✅ Document processing (PDF, images, invoices)
- ✅ AWS Bedrock integration (Nova Pro, Titan) with multi-round group chat orchestration
- ✅ Comprehensive error handling and logging
- ✅ Streamlit web interface
- ✅ Sample case scenarios for testing

## Requirements

- Python 3.8+
- AWS account with Bedrock access
- Nova Pro and Titan embedding models enabled
- Virtual environment recommended

## License

MIT
