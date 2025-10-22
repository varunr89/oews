from src.config.llm_config import (
    ModelConfig,
    ModelRole,
    ModelProvider,
    LLMRegistry,
    load_registry_from_yaml
)

def test_load_registry_from_yaml():
    """Test loading model registry from YAML file."""
    registry = load_registry_from_yaml('config/llm_models.yaml')
    assert registry is not None
    assert 'deepseek-r1' in registry.models
    assert 'deepseek-v3' in registry.models

def test_model_config_creation():
    """Test creating a model configuration."""
    config = ModelConfig(
        provider=ModelProvider.AZURE_AI,
        model_name="DeepSeek-R1",
        role=ModelRole.REASONING,
        temperature=0.0
    )
    assert config.model_name == "DeepSeek-R1"
    assert config.role == ModelRole.REASONING

def test_registry_has_reasoning_and_implementation():
    """Test registry has both reasoning and implementation models."""
    registry = load_registry_from_yaml('config/llm_models.yaml')
    reasoning_models = [
        k for k, v in registry.models.items()
        if v.role == ModelRole.REASONING
    ]
    impl_models = [
        k for k, v in registry.models.items()
        if v.role == ModelRole.IMPLEMENTATION
    ]
    assert len(reasoning_models) > 0
    assert len(impl_models) > 0
