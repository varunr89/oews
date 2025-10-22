"""LLM model configuration and registry loaded from external YAML."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import yaml
import os


class ModelRole(str, Enum):
    """Categorize models by their use case."""
    REASONING = "reasoning"
    IMPLEMENTATION = "implementation"
    FAST = "fast"


class ModelProvider(str, Enum):
    """Supported LLM providers."""
    AZURE_AI = "azure_ai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    TOGETHER = "together"
    OLLAMA = "ollama"


class ModelConfig(BaseModel):
    """Configuration for a single LLM."""
    provider: ModelProvider
    model_name: str
    role: ModelRole
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, Any]] = None
    api_key_env: Optional[str] = None
    endpoint_env: Optional[str] = None

    # Performance characteristics
    cost_per_1m_tokens: Optional[float] = None
    avg_latency_ms: Optional[int] = None
    context_window: Optional[int] = None


class LLMRegistry(BaseModel):
    """Registry of all available models."""
    models: Dict[str, ModelConfig]
    default_reasoning: str = "deepseek-r1"
    default_implementation: str = "deepseek-v3"
    default_fast: str = "deepseek-v3"

    # Feature flags
    enable_model_tracking: bool = True
    enable_cost_tracking: bool = False


def load_registry_from_yaml(config_path: str) -> LLMRegistry:
    """
    Load LLM registry from YAML configuration file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        LLMRegistry instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    # Parse models
    models = {}
    for model_key, model_data in config_data.get('models', {}).items():
        models[model_key] = ModelConfig(**model_data)

    # Parse defaults
    defaults = config_data.get('defaults', {})
    features = config_data.get('features', {})

    return LLMRegistry(
        models=models,
        default_reasoning=defaults.get('reasoning', 'deepseek-r1'),
        default_implementation=defaults.get('implementation', 'deepseek-v3'),
        default_fast=defaults.get('fast', 'deepseek-v3'),
        enable_model_tracking=features.get('enable_model_tracking', True),
        enable_cost_tracking=features.get('enable_cost_tracking', False)
    )


def get_default_registry() -> LLMRegistry:
    """
    Get the default LLM registry.

    Tries to load from config/llm_models.yaml, falls back to hardcoded defaults.

    Returns:
        LLMRegistry instance
    """
    config_path = os.getenv('LLM_CONFIG_PATH', 'config/llm_models.yaml')

    try:
        return load_registry_from_yaml(config_path)
    except FileNotFoundError:
        # Fallback to minimal hardcoded config
        return LLMRegistry(
            models={
                "deepseek-r1": ModelConfig(
                    provider=ModelProvider.AZURE_AI,
                    model_name="DeepSeek-R1-0528",
                    role=ModelRole.REASONING,
                    temperature=0.0,
                    api_key_env="AZURE_AI_API_KEY"
                ),
                "deepseek-v3": ModelConfig(
                    provider=ModelProvider.AZURE_AI,
                    model_name="DeepSeek-V3-0324",
                    role=ModelRole.IMPLEMENTATION,
                    temperature=0.0,
                    api_key_env="AZURE_AI_API_KEY"
                )
            }
        )
