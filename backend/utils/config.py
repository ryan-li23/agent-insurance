"""Configuration management for claims reasoner."""

import os
import yaml
from dataclasses import dataclass


@dataclass
class BedrockConfig:
    """AWS Bedrock configuration."""
    model_id: str
    embedding_model_id: str
    timeout: int
    max_retries: int


@dataclass
class BedrockAgentsConfig:
    """Optional Agents for Amazon Bedrock configuration per agent role."""
    enabled: bool = False
    curator_agent_id: str = ""
    curator_alias_id: str = ""
    interpreter_agent_id: str = ""
    interpreter_alias_id: str = ""
    reviewer_agent_id: str = ""
    reviewer_alias_id: str = ""


@dataclass
class VectorStoreConfig:
    """FAISS vector store configuration."""
    index_path: str
    metadata_path: str
    dimension: int
    chunk_size: int
    chunk_overlap: int


@dataclass
class AgentConfig:
    """Agent configuration."""
    name: str
    instructions: str


@dataclass
class StorageConfig:
    """Storage paths configuration."""
    policy_dir: str
    sample_cases_dir: str
    uploads_dir: str


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str
    format: str
    file: str


@dataclass
class Config:
    """Main configuration class."""
    aws_region: str
    bedrock: BedrockConfig
    vector_store: VectorStoreConfig
    max_agent_rounds: int
    curator: AgentConfig
    interpreter: AgentConfig
    reviewer: AgentConfig
    storage: StorageConfig
    logging: LoggingConfig
    bedrock_agents: BedrockAgentsConfig
    
    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        """
        Load configuration from file and environment variables.
        
        Environment variables override config file values:
        - AWS_REGION
        - BEDROCK_MODEL_ID
        - FAISS_INDEX_PATH
        - MAX_AGENT_ROUNDS
        - LOG_LEVEL
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Config instance with loaded settings
        """
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # AWS configuration with environment overrides
        aws_region = os.getenv("AWS_REGION", config_data["aws"]["region"])
        
        bedrock_config = BedrockConfig(
            model_id=os.getenv("BEDROCK_MODEL_ID", config_data["aws"]["bedrock"]["model_id"]),
            embedding_model_id=config_data["aws"]["bedrock"]["embedding_model_id"],
            timeout=config_data["aws"]["bedrock"]["timeout"],
            max_retries=config_data["aws"]["bedrock"]["max_retries"]
        )
        
        # Vector store configuration
        vector_store_config = VectorStoreConfig(
            index_path=os.getenv("FAISS_INDEX_PATH", config_data["vector_store"]["index_path"]),
            metadata_path=config_data["vector_store"]["metadata_path"],
            dimension=config_data["vector_store"]["dimension"],
            chunk_size=config_data["vector_store"]["chunk_size"],
            chunk_overlap=config_data["vector_store"]["chunk_overlap"]
        )
        
        # Agent configurations
        max_rounds = int(os.getenv("MAX_AGENT_ROUNDS", config_data["agents"]["max_rounds"]))
        
        curator_config = AgentConfig(
            name=config_data["agents"]["curator"]["name"],
            instructions=config_data["agents"]["curator"]["instructions"]
        )
        
        interpreter_config = AgentConfig(
            name=config_data["agents"]["interpreter"]["name"],
            instructions=config_data["agents"]["interpreter"]["instructions"]
        )
        
        reviewer_config = AgentConfig(
            name=config_data["agents"]["reviewer"]["name"],
            instructions=config_data["agents"]["reviewer"]["instructions"]
        )
        
        # Storage configuration
        storage_config = StorageConfig(
            policy_dir=config_data["storage"]["policy_dir"],
            sample_cases_dir=config_data["storage"]["sample_cases_dir"],
            uploads_dir=config_data["storage"]["uploads_dir"]
        )
        
        # Logging configuration
        logging_config = LoggingConfig(
            level=os.getenv("LOG_LEVEL", config_data["logging"]["level"]),
            format=config_data["logging"]["format"],
            file=config_data["logging"]["file"]
        )
        
        # Bedrock Agents configuration (optional)
        ba = config_data.get("bedrock_agents", {}) or {}
        bedrock_agents_config = BedrockAgentsConfig(
            enabled=bool(ba.get("enabled", False)),
            curator_agent_id=(ba.get("curator", {}) or {}).get("agent_id", ""),
            curator_alias_id=(ba.get("curator", {}) or {}).get("agent_alias_id", ""),
            interpreter_agent_id=(ba.get("interpreter", {}) or {}).get("agent_id", ""),
            interpreter_alias_id=(ba.get("interpreter", {}) or {}).get("agent_alias_id", ""),
            reviewer_agent_id=(ba.get("reviewer", {}) or {}).get("agent_id", ""),
            reviewer_alias_id=(ba.get("reviewer", {}) or {}).get("agent_alias_id", ""),
        )

        return cls(
            aws_region=aws_region,
            bedrock=bedrock_config,
            vector_store=vector_store_config,
            max_agent_rounds=max_rounds,
            curator=curator_config,
            interpreter=interpreter_config,
            reviewer=reviewer_config,
            storage=storage_config,
            logging=logging_config,
            bedrock_agents=bedrock_agents_config,
        )
