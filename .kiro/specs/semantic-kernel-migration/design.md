# Design Document

## Overview

This design transforms the Claims Coverage Reasoner from an AWS-centric architecture to a portable, modular solution using Microsoft Semantic Kernel for multi-agent orchestration and FAISS for local vector storage. The system maintains its core multi-agent debate model while minimizing cloud dependencies to only AWS Bedrock Nova Pro for LLM inference.

### Key Design Principles

1. **Modularity**: Clear separation between agents, tools, storage, and orchestration
2. **Portability**: Runs locally with minimal cloud dependencies
3. **Extensibility**: Easy to add new agents, tools, or storage backends
4. **Transparency**: Full audit trail of agent conversations and decisions
5. **Testability**: Deterministic behavior for testing and validation

## Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit UI Layer                       │
│  (Evidence Intake | Agent Debate | Decision & Citations)    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Orchestration Layer (Supervisor)                │
│           Microsoft Semantic Kernel Multi-Agent              │
└─────┬──────────────────┬──────────────────┬─────────────────┘
      │                  │                  │
┌─────▼──────┐  ┌───────▼────────┐  ┌─────▼──────────┐
│  Evidence  │  │    Policy      │  │  Compliance &  │
│  Curator   │  │  Interpreter   │  │    Reviewer    │
│   Agent    │  │     Agent      │  │     Agent      │
└─────┬──────┘  └───────┬────────┘  └─────┬──────────┘
      │                  │                  │
┌─────▼──────────────────▼──────────────────▼─────────────────┐
│                    Tool/Plugin Layer                         │
│  (PDF Parser | Image Analyzer | Invoice Extractor |         │
│   Policy Retriever | EXIF Reader | Compliance Checker)      │
└─────┬──────────────────┬──────────────────┬─────────────────┘
      │                  │                  │
┌─────▼──────┐  ┌───────▼────────┐  ┌─────▼──────────┐
│   Local    │  │  FAISS Vector  │  │  AWS Bedrock   │
│   Files    │  │     Store      │  │   Nova Pro     │
└────────────┘  └────────────────┘  └────────────────┘
```


## Components and Interfaces

### 1. Agent Layer (Semantic Kernel Agents)

#### Base Agent Interface

All agents will implement a common interface using Semantic Kernel's agent abstractions:

```python
from semantic_kernel.agents import Agent
from semantic_kernel.contents import ChatMessageContent

class BaseClaimsAgent(Agent):
    """Base class for all claims processing agents"""
    
    def __init__(self, kernel, name: str, instructions: str, plugins: List[str]):
        self.kernel = kernel
        self.name = name
        self.instructions = instructions
        self.plugins = plugins
    
    async def invoke(self, context: Dict[str, Any]) -> ChatMessageContent:
        """Process agent turn with access to tools/plugins"""
        pass
```

#### Evidence Curator Agent

**Responsibilities:**
- Extract structured data from uploaded documents (PDFs, images, text)
- Normalize evidence into consistent JSON schemas
- Maintain confidence scores for all extracted data
- Respond to requests for additional evidence clarification

**Tools/Plugins:**
- `pdf_text_extractor`: Extract text from PDFs using PyPDF2/pdfplumber
- `image_analyzer`: Analyze damage photos using Nova Pro vision
- `invoice_parser`: Extract line items from invoices using Nova Pro
- `exif_reader`: Extract metadata from images
- `evidence_validator`: Validate extracted data completeness

**Output Schema:**
```python
{
    "evidence": [
        {
            "image_name": str,
            "observations": [
                {
                    "label": str,  # damage type
                    "confidence": float,
                    "bbox": {"x": float, "y": float, "w": float, "h": float},
                    "location_text": str,
                    "novelty": "new" | "old" | "unclear",
                    "severity": "minor" | "moderate" | "severe",
                    "evidence_notes": List[str]
                }
            ],
            "global_assessment": {...},
            "chronology": {...}
        }
    ],
    "expense": {
        "vendor": str,
        "invoice_number": str,
        "line_items": [...],
        "total": float
    }
}
```


#### Policy Interpreter Agent

**Responsibilities:**
- Map claim facts to specific policy clauses
- Provide coverage recommendations with citations
- Explain what additional evidence would change decisions
- Handle both HO-3 (homeowners) and PAP (auto) policies

**Tools/Plugins:**
- `policy_retriever`: Query FAISS vector store for relevant policy sections
- `citation_formatter`: Format policy references with section/page numbers
- `coverage_analyzer`: Determine coverage applicability
- `exclusion_checker`: Identify applicable exclusions

**Output Schema:**
```python
{
    "coverage_position": "Pay" | "Partial" | "Deny",
    "rationale": str,
    "citations": [
        {
            "policy": str,  # "HO-3" or "PAP"
            "section": str,
            "page": int,
            "text_excerpt": str
        }
    ],
    "sensitivity": str  # what evidence would change decision
}
```

#### Compliance & Fairness Reviewer Agent

**Responsibilities:**
- Adversarially challenge Interpreter's reasoning
- Identify missing evidence or misapplied clauses
- Flag potential fraud indicators
- Ensure fair language and proper disclosures

**Tools/Plugins:**
- `objection_generator`: Identify logical inconsistencies
- `fraud_detector`: Check timestamp mismatches, scope creep
- `fairness_checker`: Ensure unbiased language
- `evidence_gap_finder`: Identify missing critical evidence

**Output Schema:**
```python
{
    "objections": [
        {
            "type": str,  # "Inconsistent Narrative", "Invoice Scope Mismatch", etc.
            "status": "Blocking" | "Resolved",
            "message": str,
            "evidence_reference": str
        }
    ],
    "approval": bool
}
```


### 2. Orchestration Layer (Supervisor)

The Supervisor uses Semantic Kernel's multi-agent collaboration features to coordinate the debate workflow.

**Architecture Pattern:**
- **Agent Group Chat**: Semantic Kernel's `AgentGroupChat` for turn-based collaboration
- **Selection Strategy**: Custom strategy that enforces debate rules
- **Termination Strategy**: Custom strategy based on consensus or max rounds

**Workflow:**
```python
class SupervisorOrchestrator:
    def __init__(self, kernel):
        self.kernel = kernel
        self.curator = EvidenceCuratorAgent(kernel)
        self.interpreter = PolicyInterpreterAgent(kernel)
        self.reviewer = ComplianceReviewerAgent(kernel)
        self.max_rounds = 3
    
    async def run_collaboration(self, claim_data: Dict) -> Dict:
        # 1. Initialize agent group chat
        chat = AgentGroupChat(
            agents=[self.curator, self.interpreter, self.reviewer],
            selection_strategy=DebateSelectionStrategy(),
            termination_strategy=ConsensusTerminationStrategy(max_rounds=3)
        )
        
        # 2. Start with Curator presenting evidence
        initial_message = await self.curator.invoke(claim_data)
        
        # 3. Run debate loop
        history = await chat.invoke(initial_message)
        
        # 4. Compile final decision
        return self.compile_decision(history)
```

**Selection Strategy:**
- Round 1: Curator → Interpreter → Reviewer
- Round 2+: Reviewer → Curator (if evidence needed) → Interpreter
- Enforces turn-taking and prevents infinite loops

**Termination Conditions:**
1. Reviewer approves with no blocking objections (consensus)
2. Maximum rounds reached (3 rounds)
3. Critical error in evidence processing


### 3. Tool/Plugin Layer (Semantic Kernel Plugins)

All tools are implemented as Semantic Kernel plugins with proper function decorators.

#### PDF Text Extractor Plugin

```python
from semantic_kernel.functions import kernel_function

class PDFExtractorPlugin:
    @kernel_function(
        name="extract_pdf_text",
        description="Extract text content from PDF documents"
    )
    def extract_text(self, pdf_bytes: bytes) -> str:
        # Use PyPDF2 or pdfplumber
        pass
```

#### Image Analyzer Plugin

```python
class ImageAnalyzerPlugin:
    def __init__(self, bedrock_client):
        self.bedrock = bedrock_client
    
    @kernel_function(
        name="analyze_damage_image",
        description="Analyze damage photos for multi-label detection with bounding boxes"
    )
    async def analyze_image(
        self, 
        image_bytes: bytes, 
        allowed_labels: List[str]
    ) -> Dict:
        # Call Nova Pro with vision capabilities
        # Return structured observations with bboxes, severity, novelty
        pass
```

#### Invoice Parser Plugin

```python
class InvoiceParserPlugin:
    def __init__(self, bedrock_client):
        self.bedrock = bedrock_client
    
    @kernel_function(
        name="parse_invoice",
        description="Extract structured data from invoice PDFs"
    )
    async def parse_invoice(self, pdf_bytes: bytes) -> Dict:
        # Call Nova Pro with document content block
        # Return normalized expense JSON
        pass
```

#### Policy Retriever Plugin

```python
class PolicyRetrieverPlugin:
    def __init__(self, faiss_index, embedding_model):
        self.index = faiss_index
        self.embedder = embedding_model
    
    @kernel_function(
        name="retrieve_policy_clauses",
        description="Retrieve relevant policy clauses using semantic search"
    )
    async def retrieve(self, query: str, policy_type: str, top_k: int = 5) -> List[Dict]:
        # 1. Generate query embedding
        # 2. Search FAISS index
        # 3. Return policy text with citations
        pass
```


### 4. Storage Layer

#### FAISS Vector Store

**Purpose:** Local semantic search for policy documents without AWS Knowledge Bases

**Implementation:**
```python
import faiss
import numpy as np
from typing import List, Dict, Tuple

class PolicyVectorStore:
    def __init__(self, index_path: str, metadata_path: str):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.index = None
        self.metadata = []  # List of policy chunks with citations
        self.dimension = 1024  # Bedrock Titan embedding dimension
    
    def build_index(self, policy_documents: List[Dict]):
        """Build FAISS index from policy PDFs"""
        # 1. Chunk policy documents (500 tokens with 50 token overlap)
        # 2. Generate embeddings using Bedrock Titan
        # 3. Create FAISS index (IndexFlatIP for cosine similarity)
        # 4. Persist index and metadata to disk
        pass
    
    def load_index(self):
        """Load existing FAISS index from disk"""
        self.index = faiss.read_index(self.index_path)
        with open(self.metadata_path, 'r') as f:
            self.metadata = json.load(f)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Search for relevant policy clauses"""
        distances, indices = self.index.search(query_embedding, top_k)
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result['score'] = float(dist)
                results.append(result)
        return results
```

**Metadata Schema:**
```python
{
    "policy_type": "HO-3" | "PAP",
    "section": str,
    "page": int,
    "text": str,  # chunk text
    "chunk_id": str,
    "document_name": str
}
```

**Index Persistence:**
- Index file: `data/policy_index.faiss`
- Metadata file: `data/policy_metadata.json`
- Created on first run if not exists
- Loaded from disk on subsequent runs


#### Local File Storage

**Purpose:** Store policy documents, sample data, and temporary uploads

**Directory Structure:**
```
data/
├── policies/
│   ├── HO3_specimen.pdf
│   └── PAP_specimen.pdf
├── policy_index.faiss
├── policy_metadata.json
├── sample_cases/
│   ├── case_a/
│   │   ├── fnol.txt
│   │   ├── photos/
│   │   └── invoice.pdf
│   ├── case_b/
│   └── case_c/
└── uploads/
    └── {case_id}/
        ├── photos/
        ├── invoices/
        └── fnol/
```

### 5. AWS Bedrock Integration

**Services Used:**
- **Nova Pro (amazon.nova-pro-v1:0)**: LLM inference for agent reasoning and vision analysis
- **Titan Embeddings**: Generate embeddings for FAISS indexing

**Client Configuration:**
```python
import boto3
from botocore.config import Config

class BedrockClient:
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.runtime = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(
                connect_timeout=3600,
                read_timeout=3600,
                retries={"max_attempts": 3}
            )
        )
    
    async def invoke_nova_pro(
        self, 
        messages: List[Dict],
        tool_config: Optional[Dict] = None
    ) -> Dict:
        """Call Nova Pro via Converse API"""
        params = {
            "modelId": "amazon.nova-pro-v1:0",
            "messages": messages,
            "inferenceConfig": {"temperature": 0}
        }
        if tool_config:
            params["toolConfig"] = tool_config
        
        response = self.runtime.converse(**params)
        return self._parse_response(response)
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using Titan"""
        response = self.runtime.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=json.dumps({"inputText": text})
        )
        result = json.loads(response['body'].read())
        return np.array(result['embedding'])
```


## Data Models

### Claim Input Model

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class ClaimInput:
    case_id: str
    date_of_loss: datetime
    fnol_text: str
    fnol_files: List[Tuple[str, bytes]]  # (filename, content)
    photos: List[Tuple[str, bytes]]
    invoices: List[Tuple[str, bytes]]
    scenario_hint: Optional[str] = None  # for demo purposes
```

### Evidence Model

```python
@dataclass
class Observation:
    label: str
    confidence: float
    bbox: Dict[str, float]  # {x, y, w, h} in relative coords
    location_text: str
    novelty: str  # "new" | "old" | "unclear"
    severity: str  # "minor" | "moderate" | "severe"
    evidence_notes: List[str]

@dataclass
class ImageEvidence:
    image_name: str
    observations: List[Observation]
    global_assessment: Dict[str, Any]
    chronology: Dict[str, Any]

@dataclass
class ExpenseData:
    vendor: str
    invoice_number: str
    invoice_date: str
    currency: str
    subtotal: float
    tax: float
    total: float
    line_items: List[Dict[str, Any]]
```

### Decision Model

```python
@dataclass
class Objection:
    type: str
    status: str  # "Blocking" | "Resolved"
    message: str
    evidence_reference: Optional[str] = None

@dataclass
class Citation:
    policy: str
    section: str
    page: int
    text_excerpt: str

@dataclass
class Decision:
    outcome: str  # "Pay" | "Partial" | "Deny"
    rationale: str
    citations: List[Citation]
    objections: List[Objection]
    sensitivity: str  # what would change the decision

@dataclass
class AgentTurn:
    role: str  # "curator" | "interpreter" | "reviewer" | "supervisor"
    content: str
    timestamp: datetime
```


## Error Handling

### Error Categories

1. **Document Processing Errors**
   - PDF extraction failures → fallback to text extraction only
   - Image analysis failures → log error, continue with available evidence
   - Invoice parsing failures → request manual review

2. **Bedrock API Errors**
   - Rate limiting → exponential backoff with max 3 retries
   - Timeout → increase timeout, retry once
   - Authentication errors → fail fast with clear message

3. **FAISS Index Errors**
   - Index not found → rebuild from policy documents
   - Corrupted index → rebuild from scratch
   - Search failures → return empty results, log error

4. **Agent Collaboration Errors**
   - Max rounds exceeded → force decision with disclaimer
   - Agent plugin failure → skip tool, continue with available data
   - Consensus not reached → Supervisor makes final call

### Error Response Pattern

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class ErrorContext:
    error_type: str
    message: str
    recoverable: bool
    fallback_action: Optional[str] = None

class ClaimsProcessingError(Exception):
    def __init__(self, context: ErrorContext):
        self.context = context
        super().__init__(context.message)

# Usage in agents
try:
    result = await plugin.analyze_image(image_bytes)
except Exception as e:
    error_ctx = ErrorContext(
        error_type="IMAGE_ANALYSIS_FAILED",
        message=f"Failed to analyze {filename}: {str(e)}",
        recoverable=True,
        fallback_action="Continue with available evidence"
    )
    logger.error(error_ctx)
    # Continue processing with partial evidence
```


## Testing Strategy

### Unit Testing

**Agent Tests:**
- Test each agent in isolation with mocked plugins
- Verify correct tool invocation patterns
- Validate output schema compliance

**Plugin Tests:**
- Test each plugin with sample inputs
- Mock Bedrock calls for deterministic results
- Verify error handling and fallbacks

**Storage Tests:**
- Test FAISS index creation and loading
- Verify search result ranking
- Test index persistence and recovery

### Integration Testing

**Multi-Agent Collaboration:**
- Test full debate workflow with sample cases
- Verify turn-taking and termination conditions
- Validate decision compilation

**End-to-End Tests:**
- Run all three sample scenarios (A, B, C)
- Verify expected outcomes and citations
- Check objection handling and resolution

### Test Data

**Sample Cases:**
- Case A: Burst pipe (clear coverage, 1 round)
- Case B: Seepage suspicion (multi-round debate, partial coverage)
- Case C: Auto collision with scope dispute (fraud detection, partial coverage)

**Mock Responses:**
- Deterministic Nova Pro responses for reproducibility
- Pre-built FAISS index with known policy chunks
- Sample PDFs and images with known characteristics

### Testing Tools

```python
# pytest fixtures for common test setup
@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client with deterministic responses"""
    pass

@pytest.fixture
def sample_claim_data():
    """Sample claim input for testing"""
    pass

@pytest.fixture
def faiss_test_index():
    """Pre-built FAISS index for testing"""
    pass
```


## Configuration Management

### Configuration File Structure

**config.yaml:**
```yaml
# AWS Configuration
aws:
  region: us-east-1
  bedrock:
    model_id: amazon.nova-pro-v1:0
    embedding_model_id: amazon.titan-embed-text-v2:0
    timeout: 3600
    max_retries: 3

# FAISS Configuration
vector_store:
  index_path: data/policy_index.faiss
  metadata_path: data/policy_metadata.json
  dimension: 1024
  chunk_size: 500
  chunk_overlap: 50

# Agent Configuration
agents:
  max_rounds: 3
  curator:
    name: Evidence Curator
    instructions: |
      Extract and normalize all claim evidence from uploaded documents.
      Provide structured observations with confidence scores.
  interpreter:
    name: Policy Interpreter
    instructions: |
      Map claim facts to policy clauses and provide coverage recommendations.
      Cite specific policy sections with page numbers.
  reviewer:
    name: Compliance Reviewer
    instructions: |
      Adversarially challenge coverage decisions.
      Flag inconsistencies, fraud indicators, and missing evidence.

# Storage Configuration
storage:
  policy_dir: data/policies
  sample_cases_dir: data/sample_cases
  uploads_dir: data/uploads

# Logging Configuration
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/claims_reasoner.log
```

### Environment Variables

```bash
# Required
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>

# Optional (override config.yaml)
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
FAISS_INDEX_PATH=data/policy_index.faiss
MAX_AGENT_ROUNDS=3
LOG_LEVEL=INFO
```

### Configuration Loader

```python
import os
import yaml
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    aws_region: str
    bedrock_model_id: str
    embedding_model_id: str
    faiss_index_path: str
    faiss_metadata_path: str
    max_agent_rounds: int
    
    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        """Load configuration from file and environment variables"""
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls(
            aws_region=os.getenv("AWS_REGION", config_data["aws"]["region"]),
            bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", config_data["aws"]["bedrock"]["model_id"]),
            embedding_model_id=config_data["aws"]["bedrock"]["embedding_model_id"],
            faiss_index_path=os.getenv("FAISS_INDEX_PATH", config_data["vector_store"]["index_path"]),
            faiss_metadata_path=config_data["vector_store"]["metadata_path"],
            max_agent_rounds=int(os.getenv("MAX_AGENT_ROUNDS", config_data["agents"]["max_rounds"]))
        )
```


## Module Structure

### Project Directory Layout

```
claims-reasoner/
├── app.py                          # Streamlit UI (existing)
├── config.yaml                     # Configuration file
├── requirements.txt                # Python dependencies
├── README.md                       # Setup and usage instructions
│
├── backend/
│   ├── __init__.py
│   ├── reasoner.py                 # Main orchestration entry point
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base agent class
│   │   ├── curator.py              # Evidence Curator agent
│   │   ├── interpreter.py          # Policy Interpreter agent
│   │   └── reviewer.py             # Compliance Reviewer agent
│   │
│   ├── plugins/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py       # PDF text extraction
│   │   ├── image_analyzer.py      # Image analysis with Nova Pro
│   │   ├── invoice_parser.py      # Invoice parsing with Nova Pro
│   │   ├── policy_retriever.py    # FAISS-based policy search
│   │   ├── exif_reader.py         # Image metadata extraction
│   │   └── compliance_checker.py  # Fraud and compliance checks
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── vector_store.py        # FAISS vector store wrapper
│   │   └── file_storage.py        # Local file management
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── claim.py               # Claim input models
│   │   ├── evidence.py            # Evidence models
│   │   └── decision.py            # Decision models
│   │
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── supervisor.py          # Supervisor orchestrator
│   │   ├── strategies.py          # Selection and termination strategies
│   │   └── conversation.py        # Conversation history management
│   │
│   └── utils/
│       ├── __init__.py
│       ├── bedrock_client.py      # AWS Bedrock client wrapper
│       ├── config.py              # Configuration loader
│       ├── logging.py             # Logging setup
│       └── errors.py              # Error handling utilities
│
├── data/
│   ├── policies/                  # Policy PDF documents
│   ├── sample_cases/              # Sample test cases
│   ├── uploads/                   # Temporary uploads
│   ├── policy_index.faiss         # FAISS index (generated)
│   └── policy_metadata.json       # Index metadata (generated)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures
│   ├── test_agents.py             # Agent unit tests
│   ├── test_plugins.py            # Plugin unit tests
│   ├── test_storage.py            # Storage unit tests
│   ├── test_orchestration.py     # Orchestration tests
│   └── test_e2e.py                # End-to-end tests
│
└── logs/
    └── claims_reasoner.log        # Application logs
```

### Key Module Responsibilities

**backend/reasoner.py:**
- Main entry point called by Streamlit UI
- Initializes Semantic Kernel and agents
- Delegates to Supervisor for orchestration
- Returns compiled decision to UI

**backend/agents/:**
- Each agent implements Semantic Kernel Agent interface
- Agents have access to specific plugins
- Agents maintain their own instructions/prompts

**backend/plugins/:**
- Semantic Kernel plugins with @kernel_function decorators
- Each plugin is self-contained and testable
- Plugins handle external service calls (Bedrock, FAISS)

**backend/orchestration/:**
- Supervisor manages agent group chat
- Custom selection and termination strategies
- Conversation history tracking

**backend/storage/:**
- FAISS vector store for policy retrieval
- Local file management for uploads and policy docs

**backend/utils/:**
- Shared utilities (Bedrock client, config, logging, errors)
- No business logic, only infrastructure concerns


## Design Decisions and Rationales

### 1. Why Microsoft Semantic Kernel?

**Decision:** Use Semantic Kernel instead of AWS AgentCore

**Rationale:**
- **Portability**: Not locked into AWS ecosystem
- **Maturity**: Well-documented multi-agent patterns
- **Plugin System**: Clean abstraction for tools
- **Python Support**: Native Python SDK with async support
- **Community**: Active development and examples

**Trade-offs:**
- Need to implement custom orchestration logic
- Less integrated with AWS services
- More boilerplate for agent setup

### 2. Why FAISS for Vector Storage?

**Decision:** Use FAISS instead of AWS Knowledge Bases

**Rationale:**
- **Local Development**: No cloud dependencies for RAG
- **Performance**: Fast in-memory search
- **Simplicity**: Single file persistence
- **Cost**: No ongoing cloud costs
- **Control**: Full control over indexing and search

**Trade-offs:**
- Manual index management
- No automatic updates
- Limited to single machine
- Need to implement chunking logic

### 3. Why Keep AWS Bedrock Nova Pro?

**Decision:** Continue using Nova Pro for LLM inference

**Rationale:**
- **Vision Capabilities**: Multimodal analysis for images and PDFs
- **Quality**: High-quality reasoning for complex claims
- **Tool Use**: Native support for structured outputs
- **Cost-Effective**: Pay-per-use pricing
- **Compliance**: AWS security and compliance features

**Trade-offs:**
- Still requires AWS credentials
- Network latency for API calls
- Potential rate limiting

### 4. Why Modular Architecture?

**Decision:** Strict separation of agents, plugins, storage, and orchestration

**Rationale:**
- **Testability**: Each component can be tested in isolation
- **Maintainability**: Clear boundaries and responsibilities
- **Extensibility**: Easy to add new agents or plugins
- **Reusability**: Plugins can be shared across agents
- **Debugging**: Easier to trace issues

**Trade-offs:**
- More files and boilerplate
- Steeper learning curve for new developers
- Potential over-engineering for POC

### 5. Why Async/Await Pattern?

**Decision:** Use async/await throughout the codebase

**Rationale:**
- **Performance**: Concurrent API calls to Bedrock
- **Semantic Kernel**: Native async support
- **Scalability**: Better resource utilization
- **Modern Python**: Aligns with Python 3.7+ best practices

**Trade-offs:**
- More complex error handling
- Requires understanding of async patterns
- Debugging can be harder


## Deployment and Setup

### Prerequisites

**System Requirements:**
- Python 3.9+
- 8GB RAM minimum (for FAISS index)
- 2GB disk space for policy documents and indices

**Required Accounts:**
- AWS account with Bedrock access
- IAM credentials with permissions for:
  - bedrock-runtime:InvokeModel
  - bedrock-runtime:Converse

### Installation Steps

1. **Clone Repository and Install Dependencies:**
```bash
git clone <repo-url>
cd claims-reasoner
pip install -r requirements.txt
```

2. **Configure AWS Credentials:**
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
```

3. **Initialize Policy Index:**
```bash
python -m backend.storage.vector_store --build-index
```

4. **Run Application:**
```bash
streamlit run app.py
```

### Dependencies (requirements.txt)

```
# Core Framework
semantic-kernel>=1.0.0
streamlit>=1.30.0

# AWS Integration
boto3>=1.34.0
botocore>=1.34.0

# Vector Storage
faiss-cpu>=1.7.4
numpy>=1.24.0

# Document Processing
PyPDF2>=3.0.0
pdfplumber>=0.10.0
Pillow>=10.0.0
python-dateutil>=2.8.0

# Utilities
pyyaml>=6.0
python-dotenv>=1.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.12.0
```

## Performance Considerations

### Latency Optimization

**Bedrock API Calls:**
- Batch image analysis when possible
- Use async/await for concurrent calls
- Implement request caching for repeated queries

**FAISS Search:**
- Keep index in memory after first load
- Use IndexFlatIP for best accuracy (acceptable for <100K vectors)
- Consider IndexIVFFlat for larger policy sets

**Agent Orchestration:**
- Limit max rounds to 3 to prevent long debates
- Implement early termination on clear consensus
- Cache policy retrievals within a session

### Memory Management

**FAISS Index:**
- ~1GB for 10K policy chunks with 1024-dim embeddings
- Load index once at startup, keep in memory
- Implement lazy loading if memory constrained

**Image Processing:**
- Stream images to Bedrock, don't keep in memory
- Process images sequentially to limit memory usage
- Clear image buffers after analysis

## Security Considerations

### Data Privacy

**Uploaded Documents:**
- Store temporarily in local filesystem
- Clear uploads after processing (configurable retention)
- No data sent to third parties except AWS Bedrock

**AWS Credentials:**
- Use IAM roles when possible
- Never commit credentials to version control
- Support AWS credential chain (env vars, profiles, IAM roles)

**Policy Documents:**
- Store locally, not in cloud
- Use specimen policies only (no proprietary data)
- Implement access controls if deployed to shared environment

### Input Validation

**File Uploads:**
- Validate file types and sizes
- Scan for malicious content
- Limit upload sizes (10MB per file)

**User Input:**
- Sanitize FNOL text input
- Validate date/time inputs
- Prevent injection attacks in queries

## Monitoring and Observability

### Logging Strategy

**Log Levels:**
- DEBUG: Detailed agent conversations, plugin calls
- INFO: Agent turns, decisions, citations
- WARNING: Recoverable errors, fallbacks
- ERROR: Unrecoverable errors, API failures

**Log Structure:**
```python
{
    "timestamp": "2025-01-15T10:30:00Z",
    "level": "INFO",
    "component": "PolicyInterpreterAgent",
    "case_id": "CASE-ABC123",
    "message": "Retrieved 5 policy clauses for query",
    "metadata": {
        "query": "sudden discharge",
        "policy_type": "HO-3",
        "top_score": 0.92
    }
}
```

### Metrics to Track

**Performance Metrics:**
- End-to-end processing time per claim
- Bedrock API latency and token usage
- FAISS search latency
- Agent round count distribution

**Quality Metrics:**
- Decision accuracy (manual validation)
- Citation relevance scores
- Objection resolution rate
- Consensus achievement rate

**Error Metrics:**
- API failure rate
- Document processing failure rate
- Agent plugin failure rate

## Migration Path from Current Implementation

### Phase 1: Setup Infrastructure
1. Install Semantic Kernel and dependencies
2. Create modular directory structure
3. Set up configuration management
4. Initialize FAISS index with policy documents

### Phase 2: Implement Plugins
1. Port PDF extractor (PyPDF2/pdfplumber)
2. Port image analyzer (Nova Pro vision)
3. Port invoice parser (Nova Pro document)
4. Implement policy retriever (FAISS)
5. Add EXIF reader and compliance checker

### Phase 3: Implement Agents
1. Create base agent class
2. Implement Evidence Curator agent
3. Implement Policy Interpreter agent
4. Implement Compliance Reviewer agent
5. Wire agents to plugins

### Phase 4: Implement Orchestration
1. Create Supervisor orchestrator
2. Implement selection strategy
3. Implement termination strategy
4. Add conversation history tracking

### Phase 5: Update UI Integration
1. Update backend/reasoner.py entry point
2. Ensure backward compatibility with app.py
3. Test all three sample scenarios
4. Update error handling in UI

### Phase 6: Testing and Validation
1. Write unit tests for all components
2. Write integration tests for agent collaboration
3. Run end-to-end tests with sample cases
4. Performance testing and optimization

## Future Enhancements

### Short-term (Post-POC)
- Add more policy types (commercial, specialty)
- Improve fraud detection algorithms
- Add support for more document formats
- Implement conversation export/import

### Medium-term
- Multi-language support
- Advanced analytics dashboard
- Integration with claims management systems
- Mobile-responsive UI

### Long-term
- Fine-tuned models for claims domain
- Automated reserve recommendations
- Subrogation opportunity detection
- Real-time policy updates
