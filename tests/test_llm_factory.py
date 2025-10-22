import pytest
import os
from src.config.llm_factory import LLMFactory, llm_factory

skip_if_no_keys = pytest.mark.skipif(
    not os.getenv('AZURE_AI_API_KEY') and not os.getenv('OPENAI_API_KEY'),
    reason="No API keys configured"
)

def test_llm_factory_singleton():
    """Test that llm_factory is a singleton instance."""
    assert llm_factory is not None
    assert isinstance(llm_factory, LLMFactory)

def test_get_reasoning_model_requires_api_key():
    """Test getting reasoning model requires API key."""
    # Without API key, should raise ValueError
    if not os.getenv('AZURE_AI_API_KEY'):
        with pytest.raises(ValueError, match="API key not found"):
            llm_factory.get_reasoning()
    else:
        model = llm_factory.get_reasoning()
        assert model is not None

def test_get_implementation_model_requires_api_key():
    """Test getting implementation model requires API key."""
    # Without API key, should raise ValueError
    if not os.getenv('AZURE_AI_API_KEY'):
        with pytest.raises(ValueError, match="API key not found"):
            llm_factory.get_implementation()
    else:
        model = llm_factory.get_implementation()
        assert model is not None

def test_get_model_by_name_requires_api_key():
    """Test getting specific model by name requires API key."""
    # Without API key, should raise ValueError
    if not os.getenv('AZURE_AI_API_KEY'):
        with pytest.raises(ValueError, match="API key not found"):
            llm_factory.get_model("deepseek-v3")
    else:
        model = llm_factory.get_model("deepseek-v3")
        assert model is not None

@skip_if_no_keys
def test_model_can_invoke():
    """Test that model can be invoked with a message."""
    from langchain.schema import HumanMessage

    model = llm_factory.get_implementation()
    response = model.invoke([HumanMessage(content="Say 'test' and nothing else.")])

    assert response is not None
    assert hasattr(response, 'content')
