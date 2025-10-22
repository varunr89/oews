"""LLM Factory for creating language model instances."""

import os
from typing import Optional, Any
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama

from .llm_config import (
    LLMRegistry,
    ModelConfig,
    ModelProvider,
    get_default_registry
)


class LLMFactory:
    """
    Factory for creating LLM instances from configuration.

    Supports multiple providers: OpenAI, Azure AI, Anthropic, Ollama, Together.
    """

    def __init__(self, registry: Optional[LLMRegistry] = None):
        """
        Initialize LLM factory with a model registry.

        Args:
            registry: Optional LLMRegistry. If None, loads default registry.
        """
        self.registry = registry or get_default_registry()

    def _create_llm(self, config: ModelConfig) -> Any:
        """
        Create an LLM instance from configuration.

        Args:
            config: ModelConfig with provider and settings

        Returns:
            LangChain chat model instance

        Raises:
            ValueError: If provider is not supported or API keys are missing
        """
        # Get API key from environment
        api_key = None
        if config.api_key_env:
            api_key = os.getenv(config.api_key_env)

        # Get endpoint from environment (for Azure/Ollama)
        endpoint = None
        if config.endpoint_env:
            endpoint = os.getenv(config.endpoint_env)

        # Common parameters
        common_params = {
            "temperature": config.temperature,
            "model_name": config.model_name
        }

        if config.max_tokens:
            common_params["max_tokens"] = config.max_tokens

        # Provider-specific instantiation
        if config.provider == ModelProvider.OPENAI:
            if not api_key:
                raise ValueError(f"API key not found in environment: {config.api_key_env}")

            params = {**common_params, "api_key": api_key}
            if config.response_format:
                params["model_kwargs"] = {"response_format": config.response_format}

            return ChatOpenAI(**params)

        elif config.provider == ModelProvider.AZURE_AI:
            if not api_key:
                raise ValueError(f"API key not found in environment: {config.api_key_env}")

            # Azure AI uses OpenAI-compatible endpoints
            params = {
                **common_params,
                "api_key": api_key,
                "model": config.model_name
            }

            if endpoint:
                params["base_url"] = endpoint

            if config.response_format:
                params["model_kwargs"] = {"response_format": config.response_format}

            return ChatOpenAI(**params)

        elif config.provider == ModelProvider.ANTHROPIC:
            if not api_key:
                raise ValueError(f"API key not found in environment: {config.api_key_env}")

            return ChatAnthropic(
                api_key=api_key,
                model=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens or 4096
            )

        elif config.provider == ModelProvider.OLLAMA:
            base_url = endpoint or "http://localhost:11434"

            return ChatOllama(
                model=config.model_name,
                base_url=base_url,
                temperature=config.temperature
            )

        elif config.provider == ModelProvider.TOGETHER:
            if not api_key:
                raise ValueError(f"API key not found in environment: {config.api_key_env}")

            # Together AI uses OpenAI-compatible API
            return ChatOpenAI(
                api_key=api_key,
                model_name=config.model_name,
                base_url="https://api.together.xyz/v1",
                temperature=config.temperature
            )

        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    def get_model(self, model_key: str) -> Any:
        """
        Get a specific model by key.

        Args:
            model_key: Model identifier from registry (e.g., 'deepseek-r1')

        Returns:
            LangChain chat model instance

        Raises:
            ValueError: If model key not found in registry
        """
        if model_key not in self.registry.models:
            available = list(self.registry.models.keys())
            raise ValueError(
                f"Model '{model_key}' not found in registry. "
                f"Available models: {available}"
            )

        config = self.registry.models[model_key]
        return self._create_llm(config)

    def get_reasoning(self, override_key: Optional[str] = None) -> Any:
        """
        Get the reasoning model (for planning, complex tasks).

        Args:
            override_key: Optional model key to override default

        Returns:
            LangChain chat model instance
        """
        model_key = override_key or self.registry.default_reasoning
        return self.get_model(model_key)

    def get_implementation(self, override_key: Optional[str] = None) -> Any:
        """
        Get the implementation model (for agent execution).

        Args:
            override_key: Optional model key to override default

        Returns:
            LangChain chat model instance
        """
        model_key = override_key or self.registry.default_implementation
        return self.get_model(model_key)

    def get_fast(self, override_key: Optional[str] = None) -> Any:
        """
        Get a fast model (for quick tasks).

        Args:
            override_key: Optional model key to override default

        Returns:
            LangChain chat model instance
        """
        model_key = override_key or self.registry.default_fast
        return self.get_model(model_key)


# Global singleton instance
llm_factory = LLMFactory()
