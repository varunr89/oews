# OEWS Data Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a multi-agent system that translates natural language questions about OEWS employment data into detailed reports with interactive charts for Next.js frontend.

**Architecture:** LangGraph-based multi-agent workflow with: (1) Planner/Executor for orchestration, (2) Text2SQL ReAct agent for database queries, (3) Web Researcher for external data, (4) Multi-chart generator outputting JSON specs, (5) Response formatter for API consumption. FastAPI backend serves Next.js frontend with structured JSON responses.

**Tech Stack:** Python 3.10+, LangGraph, FastAPI, SQLAlchemy, SQLite/Azure SQL, LangChain, Pydantic, pytest

---

## Milestone 1: Foundation (Database Abstraction & LLM Config)

### Task 1.1: Create Database Connection Abstraction

**Files:**
- Create: `src/database/__init__.py`
- Create: `src/database/connection.py`
- Create: `tests/test_database.py`

**Step 1: Write the failing test**

Create `tests/test_database.py`:

```python
import pytest
from src.database.connection import OEWSDatabase

def test_sqlite_connection_initializes():
    """Test that SQLite database connection can be created."""
    db = OEWSDatabase(environment='dev')
    assert db is not None
    assert db.conn is not None

def test_execute_query_returns_dataframe():
    """Test that execute_query returns a pandas DataFrame."""
    import pandas as pd
    db = OEWSDatabase(environment='dev')
    result = db.execute_query("SELECT * FROM oews_data LIMIT 1")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
```

**Step 2: Run test to verify it fails**

Run: `cd /home/varun/projects/oews && pytest tests/test_database.py -v`

Expected: FAIL with "No module named 'src.database.connection'"

**Step 3: Create package structure**

Create `src/database/__init__.py`:

```python
"""Database connection and utilities for OEWS data."""

from .connection import OEWSDatabase

__all__ = ["OEWSDatabase"]
```

**Step 4: Write minimal implementation**

Create `src/database/connection.py`:

```python
"""Database connection abstraction for SQLite and Azure SQL."""

import os
import sqlite3
from typing import Literal, Optional
import pandas as pd
from contextlib import contextmanager


class OEWSDatabase:
    """
    Database abstraction layer for OEWS data.

    Supports both SQLite (development) and Azure SQL (production).
    Environment is controlled via the 'environment' parameter or
    DATABASE_ENV environment variable.
    """

    def __init__(self, environment: Optional[Literal['dev', 'prod']] = None):
        """
        Initialize database connection.

        Args:
            environment: 'dev' for SQLite, 'prod' for Azure SQL.
                        If None, uses DATABASE_ENV environment variable.
        """
        self.environment = environment or os.getenv('DATABASE_ENV', 'dev')
        self.conn = None
        self._connect()

    def _connect(self):
        """Establish database connection based on environment."""
        if self.environment == 'dev':
            db_path = os.getenv('SQLITE_DB_PATH', 'data/oews.db')
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
        elif self.environment == 'prod':
            # Azure SQL connection (will implement later)
            import pyodbc
            server = os.getenv('AZURE_SQL_SERVER')
            database = os.getenv('AZURE_SQL_DATABASE')
            username = os.getenv('AZURE_SQL_USERNAME')
            password = os.getenv('AZURE_SQL_PASSWORD')

            connection_string = (
                f'DRIVER={{ODBC Driver 18 for SQL Server}};'
                f'SERVER={server};'
                f'DATABASE={database};'
                f'UID={username};'
                f'PWD={password}'
            )
            self.conn = pyodbc.connect(connection_string)
        else:
            raise ValueError(f"Invalid environment: {self.environment}")

    def execute_query(self, sql: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame.

        Args:
            sql: SQL query string

        Returns:
            pandas DataFrame with query results
        """
        return pd.read_sql_query(sql, self.conn)

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_database.py -v`

Expected: PASS (2 tests)

**Step 6: Commit**

```bash
git add src/database/ tests/test_database.py
git commit -m "feat(database): add database connection abstraction for SQLite/Azure SQL"
```

---

### Task 1.2: Create Schema Metadata Module

**Files:**
- Create: `src/database/schema.py`
- Modify: `src/database/__init__.py`
- Create: `tests/test_schema.py`

**Step 1: Write the failing test**

Create `tests/test_schema.py`:

```python
from src.database.schema import get_oews_schema_description, get_table_list

def test_get_table_list():
    """Test that table list is returned."""
    tables = get_table_list()
    assert 'oews_data' in tables
    assert isinstance(tables, list)

def test_get_oews_schema_description():
    """Test that schema description is returned for LLM."""
    schema = get_oews_schema_description('oews_data')
    assert 'AREA_TITLE' in schema
    assert 'OCC_TITLE' in schema
    assert 'A_MEDIAN' in schema
    assert isinstance(schema, str)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_schema.py -v`

Expected: FAIL with "No module named 'src.database.schema'"

**Step 3: Write minimal implementation**

Create `src/database/schema.py`:

```python
"""Schema metadata for OEWS database."""

from typing import List, Dict, Any

# Table list
TABLES = ['oews_data', 'data_vintages']

# Schema descriptions for LLM context
OEWS_DATA_SCHEMA = """
Table: oews_data

Description: Occupational Employment and Wage Statistics (OEWS) data from the U.S. Bureau of Labor Statistics.
Contains employment and wage data by occupation, geographic area, and industry.

Key Columns:
- AREA_TITLE (TEXT): Geographic location name (e.g., "Bellingham, WA", "California", "United States")
- AREA_TYPE (INTEGER): Geographic level (1=National, 2=State, 4=Metropolitan/Micropolitan area)
- PRIM_STATE (TEXT): Primary state code (e.g., "WA", "CA")

- OCC_TITLE (TEXT): Occupation name (e.g., "Software Developers", "Registered Nurses")
- OCC_CODE (TEXT): SOC (Standard Occupational Classification) code
- O_GROUP (TEXT): Occupation group level (total, major, minor, broad, detailed)

- TOT_EMP (INTEGER): Total employment count for this occupation/area
- JOBS_1000 (REAL): Jobs per 1,000 total employment in the area
- LOC_QUOTIENT (REAL): Location quotient (concentration vs. national average)

- A_MEAN (REAL): Mean annual wage
- A_MEDIAN (REAL): Median annual wage (more robust than mean)
- A_PCT10, A_PCT25, A_PCT75, A_PCT90 (REAL): Annual wage percentiles

- H_MEAN (REAL): Mean hourly wage
- H_MEDIAN (REAL): Median hourly wage
- H_PCT10, H_PCT25, H_PCT75, H_PCT90 (REAL): Hourly wage percentiles

- NAICS (TEXT): Industry code (North American Industry Classification System)
- NAICS_TITLE (TEXT): Industry name

- SURVEY_YEAR (INTEGER): Year of the survey data
- SURVEY_MONTH (TEXT): Month of the survey (typically "May")

Common Query Patterns:
1. Filter by location:
   WHERE AREA_TITLE LIKE '%City Name%'
   WHERE AREA_TYPE = 4  -- Metropolitan areas only

2. Filter by occupation:
   WHERE OCC_TITLE LIKE '%Software Developer%'
   WHERE OCC_CODE LIKE '15-%'  -- Computer/IT occupations

3. Salary comparisons (use A_MEDIAN, not A_MEAN):
   SELECT AREA_TITLE, OCC_TITLE, A_MEDIAN
   ORDER BY A_MEDIAN DESC

4. Employment analysis:
   SELECT OCC_TITLE, SUM(TOT_EMP) as total_jobs
   GROUP BY OCC_TITLE
   ORDER BY total_jobs DESC

Best Practices:
- Use A_MEDIAN instead of A_MEAN for salary comparisons (less affected by outliers)
- Use LIKE with % wildcards for fuzzy matching on text fields
- Filter by AREA_TYPE to get specific geographic levels
- Check for NULL values in wage fields (some data may be suppressed)
"""

DATA_VINTAGES_SCHEMA = """
Table: data_vintages

Description: Metadata about data import timestamps and source files.

Columns:
- SOURCE_FILE (TEXT): Original filename
- SOURCE_FOLDER (TEXT): Source directory
- IMPORTED_AT (TEXT): Timestamp of import
"""


def get_table_list() -> List[str]:
    """
    Get list of available tables in the OEWS database.

    Returns:
        List of table names
    """
    return TABLES.copy()


def get_oews_schema_description(table_name: str) -> str:
    """
    Get detailed schema description for a table.

    This description is optimized for LLM context to help with
    SQL query generation.

    Args:
        table_name: Name of the table

    Returns:
        Detailed schema description string

    Raises:
        ValueError: If table name is not recognized
    """
    schemas = {
        'oews_data': OEWS_DATA_SCHEMA,
        'data_vintages': DATA_VINTAGES_SCHEMA
    }

    if table_name not in schemas:
        raise ValueError(f"Unknown table: {table_name}. Available: {list(schemas.keys())}")

    return schemas[table_name].strip()


def get_all_schemas() -> str:
    """
    Get schema descriptions for all tables.

    Returns:
        Combined schema descriptions
    """
    return "\n\n".join([
        get_oews_schema_description(table)
        for table in TABLES
    ])
```

**Step 4: Update __init__.py**

Modify `src/database/__init__.py`:

```python
"""Database connection and utilities for OEWS data."""

from .connection import OEWSDatabase
from .schema import (
    get_table_list,
    get_oews_schema_description,
    get_all_schemas
)

__all__ = [
    "OEWSDatabase",
    "get_table_list",
    "get_oews_schema_description",
    "get_all_schemas"
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_schema.py -v`

Expected: PASS (2 tests)

**Step 6: Commit**

```bash
git add src/database/schema.py src/database/__init__.py tests/test_schema.py
git commit -m "feat(database): add schema metadata for LLM context"
```

---

### Task 1.3: Create LLM Configuration System

**Files:**
- Create: `src/config/__init__.py`
- Create: `src/config/llm_config.py`
- Create: `tests/test_llm_config.py`

**Step 1: Write the failing test**

Create `tests/test_llm_config.py`:

```python
from src.config.llm_config import (
    ModelConfig,
    ModelRole,
    ModelProvider,
    LLMRegistry,
    DEFAULT_LLM_REGISTRY
)

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

def test_default_registry_exists():
    """Test that default registry is available."""
    assert DEFAULT_LLM_REGISTRY is not None
    assert 'deepseek-r1' in DEFAULT_LLM_REGISTRY.models
    assert 'deepseek-v3' in DEFAULT_LLM_REGISTRY.models

def test_registry_has_reasoning_and_implementation():
    """Test registry has both reasoning and implementation models."""
    reasoning_models = [
        k for k, v in DEFAULT_LLM_REGISTRY.models.items()
        if v.role == ModelRole.REASONING
    ]
    impl_models = [
        k for k, v in DEFAULT_LLM_REGISTRY.models.items()
        if v.role == ModelRole.IMPLEMENTATION
    ]
    assert len(reasoning_models) > 0
    assert len(impl_models) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_config.py -v`

Expected: FAIL with "No module named 'src.config.llm_config'"

**Step 3: Create package structure**

Create `src/config/__init__.py`:

```python
"""Configuration modules for LLM models and settings."""

from .llm_config import (
    ModelConfig,
    ModelRole,
    ModelProvider,
    LLMRegistry,
    DEFAULT_LLM_REGISTRY
)

__all__ = [
    "ModelConfig",
    "ModelRole",
    "ModelProvider",
    "LLMRegistry",
    "DEFAULT_LLM_REGISTRY"
]
```

**Step 4: Write minimal implementation**

Create `src/config/llm_config.py`:

```python
"""LLM model configuration and registry."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ModelRole(str, Enum):
    """Categorize models by their use case."""
    REASONING = "reasoning"           # For planning, decision-making (planner, executor)
    IMPLEMENTATION = "implementation" # For executing tasks (agents)
    FAST = "fast"                     # For quick tasks


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


# Default model registry
DEFAULT_LLM_REGISTRY = LLMRegistry(
    models={
        # Reasoning Models
        "deepseek-r1": ModelConfig(
            provider=ModelProvider.AZURE_AI,
            model_name="DeepSeek-R1-0528",
            role=ModelRole.REASONING,
            temperature=0.0,
            response_format={"type": "json_object"},
            api_key_env="AZURE_AI_API_KEY",
            endpoint_env="AZURE_AI_ENDPOINT",
            cost_per_1m_tokens=0.55,
            avg_latency_ms=3000,
            context_window=64000
        ),
        "gpt-4o": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4o",
            role=ModelRole.REASONING,
            temperature=0.0,
            response_format={"type": "json_object"},
            api_key_env="OPENAI_API_KEY",
            cost_per_1m_tokens=2.50,
            avg_latency_ms=2000,
            context_window=128000
        ),

        # Implementation Models
        "deepseek-v3": ModelConfig(
            provider=ModelProvider.AZURE_AI,
            model_name="DeepSeek-V3-0324",
            role=ModelRole.IMPLEMENTATION,
            temperature=0.0,
            api_key_env="AZURE_AI_API_KEY",
            endpoint_env="AZURE_AI_ENDPOINT",
            cost_per_1m_tokens=0.27,
            avg_latency_ms=1500,
            context_window=64000
        ),
        "gpt-4o-mini": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4o-mini",
            role=ModelRole.IMPLEMENTATION,
            temperature=0.0,
            api_key_env="OPENAI_API_KEY",
            cost_per_1m_tokens=0.15,
            avg_latency_ms=800,
            context_window=128000
        ),

        # Local testing
        "ollama-llama3": ModelConfig(
            provider=ModelProvider.OLLAMA,
            model_name="llama3",
            role=ModelRole.IMPLEMENTATION,
            temperature=0.0,
            endpoint_env="OLLAMA_BASE_URL",
            cost_per_1m_tokens=0.0,
            context_window=8192
        )
    }
)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_llm_config.py -v`

Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add src/config/ tests/test_llm_config.py
git commit -m "feat(config): add LLM configuration system with model registry"
```

---

### Task 1.4: Create LLM Factory

**Files:**
- Create: `src/config/llm_factory.py`
- Modify: `src/config/__init__.py`
- Create: `tests/test_llm_factory.py`

**Step 1: Write the failing test**

Create `tests/test_llm_factory.py`:

```python
import pytest
import os
from src.config.llm_factory import LLMFactory
from src.config.llm_config import ModelRole

# Skip if no API keys available
skip_if_no_keys = pytest.mark.skipif(
    not os.getenv('AZURE_AI_API_KEY'),
    reason="No API keys configured"
)

def test_factory_creation():
    """Test that factory can be created."""
    factory = LLMFactory()
    assert factory is not None
    assert factory.registry is not None

def test_get_reasoning_model():
    """Test getting reasoning model."""
    factory = LLMFactory()
    llm = factory.get_reasoning()
    assert llm is not None

def test_get_worker_model():
    """Test getting implementation/worker model."""
    factory = LLMFactory()
    llm = factory.get_worker()
    assert llm is not None

def test_list_models():
    """Test listing models by role."""
    factory = LLMFactory()
    reasoning_models = factory.list_models(role=ModelRole.REASONING)
    assert len(reasoning_models) > 0
    assert all(m.role == ModelRole.REASONING for m in reasoning_models.values())
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_factory.py -v`

Expected: FAIL with "No module named 'src.config.llm_factory'"

**Step 3: Write minimal implementation**

Create `src/config/llm_factory.py`:

```python
"""Factory for creating LLM instances."""

from typing import Optional, Dict, Any
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_together import ChatTogether
from langchain_ollama import ChatOllama
import os

from .llm_config import (
    DEFAULT_LLM_REGISTRY,
    LLMRegistry,
    ModelConfig,
    ModelProvider,
    ModelRole
)


class LLMFactory:
    """Factory for creating LLM instances based on configuration."""

    def __init__(self, registry: Optional[LLMRegistry] = None):
        """
        Initialize the factory.

        Args:
            registry: LLM registry to use. If None, uses DEFAULT_LLM_REGISTRY.
        """
        self.registry = registry or DEFAULT_LLM_REGISTRY
        self._cache: Dict[str, Any] = {}

    def _create_llm(self, config: ModelConfig) -> Any:
        """
        Create an LLM instance from configuration.

        Args:
            config: Model configuration

        Returns:
            LLM instance
        """
        # Build base kwargs
        kwargs = {
            "temperature": config.temperature,
        }

        if config.max_tokens:
            kwargs["max_tokens"] = config.max_tokens

        if config.response_format:
            kwargs["model_kwargs"] = {"response_format": config.response_format}

        # Provider-specific initialization
        if config.provider == ModelProvider.AZURE_AI:
            return AzureAIChatCompletionsModel(
                model_name=config.model_name,
                **kwargs
            )

        elif config.provider == ModelProvider.OPENAI:
            api_key = os.getenv(config.api_key_env) if config.api_key_env else None
            return ChatOpenAI(
                model=config.model_name,
                api_key=api_key,
                **kwargs
            )

        elif config.provider == ModelProvider.ANTHROPIC:
            api_key = os.getenv(config.api_key_env) if config.api_key_env else None
            return ChatAnthropic(
                model=config.model_name,
                api_key=api_key,
                **kwargs
            )

        elif config.provider == ModelProvider.TOGETHER:
            api_key = os.getenv(config.api_key_env) if config.api_key_env else None
            return ChatTogether(
                model=config.model_name,
                together_api_key=api_key,
                **kwargs
            )

        elif config.provider == ModelProvider.OLLAMA:
            base_url = os.getenv(config.endpoint_env, "http://localhost:11434")
            return ChatOllama(
                model=config.model_name,
                base_url=base_url,
                **kwargs
            )

        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    def get_llm(
        self,
        model_key: Optional[str] = None,
        role: Optional[ModelRole] = None,
        cache: bool = True
    ) -> Any:
        """
        Get an LLM instance.

        Args:
            model_key: Specific model key from registry
            role: Model role to get default for
            cache: Whether to cache the instance

        Returns:
            LLM instance
        """
        # Determine which model to use
        if model_key:
            key = model_key
        elif role == ModelRole.REASONING:
            key = os.getenv("LLM_REASONING_MODEL", self.registry.default_reasoning)
        elif role == ModelRole.IMPLEMENTATION:
            key = os.getenv("LLM_IMPLEMENTATION_MODEL", self.registry.default_implementation)
        elif role == ModelRole.FAST:
            key = os.getenv("LLM_FAST_MODEL", self.registry.default_fast)
        else:
            key = self.registry.default_implementation

        # Check cache
        if cache and key in self._cache:
            return self._cache[key]

        # Get config and create LLM
        if key not in self.registry.models:
            raise ValueError(f"Model '{key}' not found in registry")

        config = self.registry.models[key]
        llm = self._create_llm(config)

        # Cache if requested
        if cache:
            self._cache[key] = llm

        return llm

    def get_reasoning(self) -> Any:
        """Get the configured reasoning model."""
        return self.get_llm(role=ModelRole.REASONING)

    def get_worker(self) -> Any:
        """Get the configured implementation model."""
        return self.get_llm(role=ModelRole.IMPLEMENTATION)

    def get_fast(self) -> Any:
        """Get a fast model for simple tasks."""
        return self.get_llm(role=ModelRole.FAST)

    def get_config(self, model_key: str) -> ModelConfig:
        """Get configuration for a specific model."""
        return self.registry.models[model_key]

    def list_models(self, role: Optional[ModelRole] = None) -> Dict[str, ModelConfig]:
        """
        List all available models.

        Args:
            role: Optional filter by role

        Returns:
            Dictionary of model configs
        """
        if role:
            return {
                k: v for k, v in self.registry.models.items()
                if v.role == role
            }
        return self.registry.models


# Global factory instance
llm_factory = LLMFactory()
```

**Step 4: Update __init__.py**

Modify `src/config/__init__.py`:

```python
"""Configuration modules for LLM models and settings."""

from .llm_config import (
    ModelConfig,
    ModelRole,
    ModelProvider,
    LLMRegistry,
    DEFAULT_LLM_REGISTRY
)
from .llm_factory import LLMFactory, llm_factory

__all__ = [
    "ModelConfig",
    "ModelRole",
    "ModelProvider",
    "LLMRegistry",
    "DEFAULT_LLM_REGISTRY",
    "LLMFactory",
    "llm_factory"
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_llm_factory.py -v`

Expected: PASS (4 tests, some may be skipped if no API keys)

**Step 6: Commit**

```bash
git add src/config/llm_factory.py src/config/__init__.py tests/test_llm_factory.py
git commit -m "feat(config): add LLM factory for dynamic model instantiation"
```

---

## Milestone 2: Database Tools for Text2SQL Agent

### Task 2.1: Create Database Tools

**Files:**
- Create: `src/tools/__init__.py`
- Create: `src/tools/database_tools.py`
- Create: `tests/test_database_tools.py`

**Step 1: Write the failing test**

Create `tests/test_database_tools.py`:

```python
from src.tools.database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    search_areas,
    search_occupations
)

def test_get_schema_info_returns_string():
    """Test schema info tool returns description."""
    result = get_schema_info.invoke({"table_name": "oews_data"})
    assert isinstance(result, str)
    assert "AREA_TITLE" in result

def test_validate_sql_accepts_select():
    """Test SQL validation accepts SELECT queries."""
    result = validate_sql.invoke({"sql": "SELECT * FROM oews_data LIMIT 1"})
    assert "valid" in result.lower() or "true" in result.lower()

def test_validate_sql_rejects_drop():
    """Test SQL validation rejects dangerous operations."""
    result = validate_sql.invoke({"sql": "DROP TABLE oews_data"})
    assert "dangerous" in result.lower() or "not allowed" in result.lower()

def test_execute_sql_query_returns_data():
    """Test SQL execution returns data."""
    result = execute_sql_query.invoke({"sql": "SELECT * FROM oews_data LIMIT 1"})
    assert "success" in result or "columns" in result

def test_search_areas_finds_bellingham():
    """Test area search finds Bellingham."""
    result = search_areas.invoke({"search_term": "Bellingham"})
    assert any("Bellingham" in area for area in result)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_tools.py -v`

Expected: FAIL with "No module named 'src.tools.database_tools'"

**Step 3: Create package structure**

Create `src/tools/__init__.py`:

```python
"""Tools for LangChain agents."""

from .database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    get_sample_data,
    search_areas,
    search_occupations
)

__all__ = [
    "get_schema_info",
    "validate_sql",
    "execute_sql_query",
    "get_sample_data",
    "search_areas",
    "search_occupations"
]
```

**Step 4: Write minimal implementation**

Create `src/tools/database_tools.py`:

```python
"""Database tools for Text2SQL agent."""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from src.database.connection import OEWSDatabase
from src.database.schema import get_oews_schema_description, get_table_list


@tool
def get_schema_info(table_name: Optional[str] = None) -> str:
    """
    Returns schema information for OEWS database.

    If table_name provided, returns detailed schema for that table.
    Otherwise returns overview of all tables.

    Use this when you need to understand the database structure
    before writing SQL queries.

    Args:
        table_name: Optional table name to get details for

    Returns:
        Schema description string
    """
    if table_name:
        return get_oews_schema_description(table_name)
    else:
        tables = get_table_list()
        return f"Available tables: {', '.join(tables)}\n\nUse get_schema_info with a specific table_name to see details."


@tool
def validate_sql(sql: str) -> str:
    """
    Validates SQL query syntax without executing it.

    Returns validation result and any suggestions.
    Use this before executing SQL to catch errors.

    Args:
        sql: SQL query string to validate

    Returns:
        Validation result message
    """
    import sqlparse

    # Basic validation
    if not sql or not sql.strip():
        return "Error: Empty query"

    # Check for dangerous operations
    dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE', 'CREATE']
    sql_upper = sql.upper()
    for keyword in dangerous:
        if keyword in sql_upper:
            return f"Error: Dangerous operation '{keyword}' not allowed. Only SELECT queries permitted."

    # Parse SQL
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return "Error: Could not parse SQL"

        return "Valid: Query syntax is valid"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def execute_sql_query(sql: str) -> str:
    """
    Executes SQL query against OEWS database and returns results.

    Returns JSON string with columns, data, row count, and SQL query.
    IMPORTANT: Always validate SQL before executing.

    Args:
        sql: SQL SELECT query to execute

    Returns:
        JSON string with query results
    """
    import json

    try:
        db = OEWSDatabase()
        df = db.execute_query(sql)
        db.close()

        result = {
            "success": True,
            "columns": df.columns.tolist(),
            "data": df.values.tolist(),
            "row_count": len(df),
            "sql": sql
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        result = {
            "success": False,
            "error": str(e),
            "sql": sql
        }
        return json.dumps(result, indent=2)


@tool
def get_sample_data(table_name: str, limit: int = 5) -> str:
    """
    Returns sample rows from a table to understand data format.

    Use this to see examples of actual data before writing queries.

    Args:
        table_name: Name of the table
        limit: Number of rows to return (default 5)

    Returns:
        JSON string with sample data
    """
    sql = f"SELECT * FROM {table_name} LIMIT {limit}"
    return execute_sql_query.invoke({"sql": sql})


@tool
def search_areas(search_term: str) -> List[str]:
    """
    Searches for geographic areas matching the search term.

    Example: search_areas("Bellingham") returns ["Bellingham, WA Metropolitan Statistical Area"]

    Use this to find exact AREA_TITLE values for filtering.

    Args:
        search_term: Text to search for in area names

    Returns:
        List of matching area names
    """
    import json

    sql = f"SELECT DISTINCT AREA_TITLE FROM oews_data WHERE AREA_TITLE LIKE '%{search_term}%' LIMIT 20"
    result_str = execute_sql_query.invoke({"sql": sql})
    result = json.loads(result_str)

    if result.get("success"):
        # Extract first column (AREA_TITLE) from each row
        return [row[0] for row in result["data"]]
    return []


@tool
def search_occupations(search_term: str) -> List[str]:
    """
    Searches for occupations matching the search term.

    Example: search_occupations("software") returns
    ["Software Developers", "Software Quality Assurance Analysts", ...]

    Use this to find exact OCC_TITLE values.

    Args:
        search_term: Text to search for in occupation names

    Returns:
        List of matching occupation names
    """
    import json

    sql = f"SELECT DISTINCT OCC_TITLE FROM oews_data WHERE OCC_TITLE LIKE '%{search_term}%' LIMIT 20"
    result_str = execute_sql_query.invoke({"sql": sql})
    result = json.loads(result_str)

    if result.get("success"):
        # Extract first column (OCC_TITLE) from each row
        return [row[0] for row in result["data"]]
    return []
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_database_tools.py -v`

Expected: PASS (5 tests)

**Step 6: Commit**

```bash
git add src/tools/ tests/test_database_tools.py
git commit -m "feat(tools): add database tools for Text2SQL agent"
```

---

## Milestone 3: Text2SQL Agent

### Task 3.1: Create Agent System Prompts

**Files:**
- Create: `src/prompts/__init__.py`
- Create: `src/prompts/agent_prompts.py`
- Create: `tests/test_prompts.py`

**Step 1: Write the failing test**

Create `tests/test_prompts.py`:

```python
from src.prompts.agent_prompts import agent_system_prompt

def test_agent_system_prompt_adds_suffix():
    """Test that agent system prompt adds custom suffix."""
    result = agent_system_prompt("Custom instructions here")
    assert "Custom instructions here" in result
    assert "helpful AI assistant" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_prompts.py -v`

Expected: FAIL with "No module named 'src.prompts.agent_prompts'"

**Step 3: Create package and implementation**

Create `src/prompts/__init__.py`:

```python
"""Prompt templates for agents."""

from .agent_prompts import agent_system_prompt

__all__ = ["agent_system_prompt"]
```

Create `src/prompts/agent_prompts.py`:

```python
"""System prompts for LangChain agents."""


def agent_system_prompt(suffix: str) -> str:
    """
    Create a system prompt for a LangChain agent.

    Args:
        suffix: Custom instructions specific to this agent

    Returns:
        Complete system prompt
    """
    base = (
        "You are a helpful AI assistant, collaborating with other assistants. "
        "Use the provided tools to progress towards answering the question. "
        "If you are unable to fully answer, that's OK, another assistant with different tools "
        "will help where you left off. Execute what you can to make progress. "
        "If you or any of the other assistants have the final answer or deliverable, "
        "prefix your response with FINAL ANSWER so the team knows to stop."
    )
    return f"{base}\n\n{suffix}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_prompts.py -v`

Expected: PASS (1 test)

**Step 5: Commit**

```bash
git add src/prompts/ tests/test_prompts.py
git commit -m "feat(prompts): add agent system prompt template"
```

---

### Task 3.2: Create Text2SQL Agent

**Files:**
- Create: `src/agents/__init__.py`
- Create: `src/agents/text2sql_agent.py`
- Create: `tests/test_text2sql_agent.py`

**Step 1: Write the failing test**

Create `tests/test_text2sql_agent.py`:

```python
import pytest
import os
from src.agents.text2sql_agent import create_text2sql_agent

skip_if_no_keys = pytest.mark.skipif(
    not os.getenv('AZURE_AI_API_KEY'),
    reason="No API keys configured"
)

@skip_if_no_keys
def test_text2sql_agent_creation():
    """Test that Text2SQL agent can be created."""
    agent = create_text2sql_agent()
    assert agent is not None

@skip_if_no_keys
def test_text2sql_agent_has_tools():
    """Test that agent has database tools."""
    agent = create_text2sql_agent()
    # Agent should be a compiled graph with tools
    assert hasattr(agent, 'invoke')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_text2sql_agent.py -v`

Expected: FAIL with "No module named 'src.agents.text2sql_agent'"

**Step 3: Create package and implementation**

Create `src/agents/__init__.py`:

```python
"""Agent implementations for the OEWS data system."""

from .text2sql_agent import create_text2sql_agent

__all__ = ["create_text2sql_agent"]
```

Create `src/agents/text2sql_agent.py`:

```python
"""Text2SQL ReAct agent for querying OEWS database."""

from langgraph.prebuilt import create_react_agent
from src.config.llm_factory import llm_factory
from src.tools.database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    get_sample_data,
    search_areas,
    search_occupations
)
from src.prompts.agent_prompts import agent_system_prompt


def create_text2sql_agent():
    """
    Create a Text2SQL ReAct agent for querying OEWS data.

    The agent has access to database tools and can:
    - Explore schema
    - Search for areas and occupations
    - Validate SQL queries
    - Execute SELECT queries

    Returns:
        LangGraph compiled agent
    """
    # Get worker model from factory
    llm = llm_factory.get_worker()

    # Create agent with database tools
    agent = create_react_agent(
        llm,
        tools=[
            get_schema_info,
            validate_sql,
            execute_sql_query,
            get_sample_data,
            search_areas,
            search_occupations
        ],
        prompt=agent_system_prompt("""
You are a SQL expert analyzing OEWS (Occupational Employment and Wage Statistics) data.

Your workflow:
1. Use get_schema_info() to understand the database structure
2. If the user mentions specific locations/occupations, use search_areas() or search_occupations() to find exact names
3. Write a SQL query to answer the question
4. Use validate_sql() to check your query
5. Use execute_sql_query() to run it
6. If you get an error, analyze it and try again

Guidelines:
- Always use A_MEDIAN instead of A_MEAN for salary comparisons (more robust to outliers)
- Filter AREA_TYPE appropriately (1=National, 2=State, 4=Metro area)
- Use LIKE with wildcards for fuzzy matching: AREA_TITLE LIKE '%City%'
- Return raw data - don't summarize. Let the synthesizer handle that.
- For complex questions, you may need multiple queries

When finished, output your results with "FINAL ANSWER" prefix.
        """)
    )

    return agent
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_text2sql_agent.py -v`

Expected: PASS (2 tests, may be skipped if no API keys)

**Step 5: Commit**

```bash
git add src/agents/ tests/test_text2sql_agent.py
git commit -m "feat(agents): add Text2SQL ReAct agent with database tools"
```

---

## Milestone 4: Chart Tools and Generator

### Task 4.1: Create Chart Specification Tools

**Files:**
- Create: `src/tools/chart_tools.py`
- Modify: `src/tools/__init__.py`
- Create: `tests/test_chart_tools.py`

**Step 1: Write the failing test**

Create `tests/test_chart_tools.py`:

```python
from src.tools.chart_tools import create_chart_specification, analyze_data_for_charts

def test_create_chart_specification_returns_json():
    """Test chart spec creation returns JSON with marker."""
    result = create_chart_specification.invoke({
        "chart_type": "bar",
        "title": "Test Chart",
        "labels": ["A", "B", "C"],
        "datasets": [{"name": "Series 1", "values": [1, 2, 3]}],
        "x_axis_title": "X",
        "y_axis_title": "Y"
    })
    assert "CHART_SPEC:" in result
    assert "Test Chart" in result
    assert '"type": "bar"' in result

def test_analyze_data_for_charts_returns_guidance():
    """Test data analysis tool returns chart guidance."""
    result = analyze_data_for_charts.invoke({
        "data_description": "I have 5 cities and their median salaries"
    })
    assert isinstance(result, str)
    assert len(result) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_chart_tools.py -v`

Expected: FAIL with "No module named 'src.tools.chart_tools'"

**Step 3: Write implementation**

Create `src/tools/chart_tools.py`:

```python
"""Chart specification tools for multi-chart generation."""

from typing import Dict, Any, List, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import json


class ChartDataset(BaseModel):
    """A single data series in a chart."""
    name: str = Field(description="Series name for legend")
    values: List[float] = Field(description="Numeric values")
    color: str | None = Field(default=None, description="Hex color code")


class ChartData(BaseModel):
    """Chart data structure."""
    labels: List[str] = Field(description="X-axis labels/categories")
    datasets: List[ChartDataset] = Field(description="One or more data series")


class ChartOptions(BaseModel):
    """Chart display options."""
    xAxis: Dict[str, str] = Field(description="X-axis config: {title, type}")
    yAxis: Dict[str, str] = Field(description="Y-axis config: {title, type}")
    legend: bool = Field(default=True, description="Show legend")
    grid: bool = Field(default=True, description="Show grid lines")
    tooltip: bool = Field(default=True, description="Enable tooltips")


class ChartSpecification(BaseModel):
    """Complete chart specification for frontend rendering."""
    type: Literal["bar", "line", "boxplot", "scatter", "heatmap"] = Field(
        description="Chart type"
    )
    title: str = Field(description="Chart title")
    data: ChartData
    options: ChartOptions


@tool
def create_chart_specification(
    chart_type: Literal["bar", "line", "boxplot", "scatter", "heatmap"],
    title: str,
    labels: List[str],
    datasets: List[Dict[str, Any]],
    x_axis_title: str,
    y_axis_title: str,
    x_axis_type: str = "category",
    y_axis_type: str = "value"
) -> str:
    """
    Creates a chart specification in JSON format for ECharts/Plotly.

    This tool validates and formats chart data into the required structure.

    Args:
        chart_type: Type of chart (bar, line, boxplot, scatter, heatmap)
        title: Descriptive chart title
        labels: X-axis labels (e.g., city names, dates)
        datasets: List of data series, each with:
            - name: Series name
            - values: List of numbers
            - color (optional): Hex color code
        x_axis_title: Label for X axis
        y_axis_title: Label for Y axis
        x_axis_type: Type of X axis (category, value, time)
        y_axis_type: Type of Y axis (value, log)

    Returns:
        JSON string with CHART_SPEC marker for extraction

    Example:
        create_chart_specification(
            chart_type="bar",
            title="Median Salaries by City",
            labels=["Seattle", "Portland", "Bellingham"],
            datasets=[{
                "name": "Software Developers",
                "values": [125000, 115000, 98750]
            }],
            x_axis_title="City",
            y_axis_title="Median Salary ($)"
        )
    """
    try:
        # Validate and build specification
        spec = ChartSpecification(
            type=chart_type,
            title=title,
            data=ChartData(
                labels=labels,
                datasets=[ChartDataset(**ds) for ds in datasets]
            ),
            options=ChartOptions(
                xAxis={"title": x_axis_title, "type": x_axis_type},
                yAxis={"title": y_axis_title, "type": y_axis_type},
                legend=len(datasets) > 1,
                grid=True,
                tooltip=True
            )
        )

        # Convert to JSON
        spec_json = spec.model_dump()

        # Return with CHART_SPEC marker for response formatter
        return f"CHART_SPEC: {json.dumps(spec_json)}\n\nChart specification created successfully."

    except Exception as e:
        return f"Error creating chart specification: {str(e)}"


@tool
def analyze_data_for_charts(data_description: str) -> str:
    """
    Analyzes available data and suggests appropriate chart types.

    Use this FIRST to determine what charts to create based on the data
    you have from previous research steps.

    Args:
        data_description: Description of available data including:
            - Data types (categorical, numeric, time-series)
            - Number of variables
            - Sample values

    Returns:
        Recommendations for chart types and what to visualize
    """
    return """
Consider these guidelines:

- **Bar charts**: Comparing values across categories (cities, occupations)
- **Line charts**: Trends over time or continuous data
- **Boxplot**: Distribution of values, showing outliers and quartiles
- **Scatter**: Correlation between two numeric variables
- **Heatmap**: Matrix of values (e.g., salary by occupation × city)

For your data:
- If comparing 2-10 categories: Bar chart
- If showing trends over time: Line chart
- If showing distribution/outliers: Boxplot
- If multiple dimensions: Create 2-3 complementary charts

Proceed to create chart specifications using create_chart_specification tool.
"""
```

**Step 4: Update __init__.py**

Modify `src/tools/__init__.py`:

```python
"""Tools for LangChain agents."""

from .database_tools import (
    get_schema_info,
    validate_sql,
    execute_sql_query,
    get_sample_data,
    search_areas,
    search_occupations
)
from .chart_tools import (
    create_chart_specification,
    analyze_data_for_charts
)

__all__ = [
    "get_schema_info",
    "validate_sql",
    "execute_sql_query",
    "get_sample_data",
    "search_areas",
    "search_occupations",
    "create_chart_specification",
    "analyze_data_for_charts"
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_chart_tools.py -v`

Expected: PASS (2 tests)

**Step 6: Commit**

```bash
git add src/tools/chart_tools.py src/tools/__init__.py tests/test_chart_tools.py
git commit -m "feat(tools): add chart specification tools for multi-chart generation"
```

---

### Task 4.2: Create Chart Generator Agent

**Files:**
- Create: `src/agents/chart_generator.py`
- Modify: `src/agents/__init__.py`
- Create: `tests/test_chart_generator.py`

**Step 1: Write the failing test**

Create `tests/test_chart_generator.py`:

```python
import pytest
import os
from src.agents.chart_generator import create_chart_generator_agent

skip_if_no_keys = pytest.mark.skipif(
    not os.getenv('AZURE_AI_API_KEY'),
    reason="No API keys configured"
)

@skip_if_no_keys
def test_chart_generator_creation():
    """Test that chart generator agent can be created."""
    agent = create_chart_generator_agent()
    assert agent is not None

@skip_if_no_keys
def test_chart_generator_has_chart_tools():
    """Test that agent has chart tools."""
    agent = create_chart_generator_agent()
    assert hasattr(agent, 'invoke')
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_chart_generator.py -v`

Expected: FAIL with "No module named 'src.agents.chart_generator'"

**Step 3: Write implementation**

Create `src/agents/chart_generator.py`:

```python
"""Multi-chart generator agent."""

from langgraph.prebuilt import create_react_agent
from src.config.llm_factory import llm_factory
from src.tools.chart_tools import (
    create_chart_specification,
    analyze_data_for_charts
)
from src.prompts.agent_prompts import agent_system_prompt


def create_chart_generator_agent():
    """
    Create a chart generator agent that outputs JSON specifications.

    The agent can create multiple charts from research data.

    Returns:
        LangGraph compiled agent
    """
    llm = llm_factory.get_worker()

    agent = create_react_agent(
        llm,
        tools=[
            analyze_data_for_charts,
            create_chart_specification
        ],
        prompt=agent_system_prompt("""
You are a data visualization expert. Your job is to create chart
specifications (JSON) for interactive web visualizations using ECharts/Plotly.

**Your workflow:**

1. **Review the conversation history** to find all data from:
   - cortex_researcher (SQL query results)
   - web_researcher (numerical data from web)

2. **Extract structured data** from the messages:
   - Identify numeric values
   - Identify categorical labels (cities, occupations, etc.)
   - Note what comparisons the user wants

3. **Decide on visualizations** (typically 1-3 charts):
   - What chart type best answers the user's question?
   - Would multiple charts provide better insights?
   - Use analyze_data_for_charts tool if needed

4. **Create chart specifications** using create_chart_specification tool:
   - You can call this tool MULTIPLE times to create multiple charts
   - Each call generates one CHART_SPEC
   - Choose descriptive titles
   - Use appropriate colors for clarity

5. **Output format**: After creating all charts, end with "FINAL ANSWER"

**Important guidelines:**

- **DO NOT generate Python code** - Only use the provided tools
- **Extract data accurately** from previous messages
- **Create 1-3 charts** depending on complexity:
  - Simple comparison: 1 bar chart
  - Multiple dimensions: 2-3 complementary charts
  - Trends + comparisons: Line chart + bar chart
- **Choose appropriate chart types**:
  - Comparing categories → Bar chart
  - Trends over time → Line chart
  - Distribution/outliers → Boxplot
  - Correlation → Scatter plot
- **Descriptive titles**: Include what, where, when
- **Consistent colors**: Use color to distinguish series clearly
        """)
    )

    return agent
```

**Step 4: Update __init__.py**

Modify `src/agents/__init__.py`:

```python
"""Agent implementations for the OEWS data system."""

from .text2sql_agent import create_text2sql_agent
from .chart_generator import create_chart_generator_agent

__all__ = [
    "create_text2sql_agent",
    "create_chart_generator_agent"
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_chart_generator.py -v`

Expected: PASS (2 tests, may be skipped)

**Step 6: Commit**

```bash
git add src/agents/chart_generator.py src/agents/__init__.py tests/test_chart_generator.py
git commit -m "feat(agents): add multi-chart generator agent"
```

---

## Milestone 5: Response Formatter & State

### Task 5.1: Create State Definition

**Files:**
- Create: `src/agents/state.py`
- Modify: `src/agents/__init__.py`
- Create: `tests/test_state.py`

**Step 1: Write the failing test**

Create `tests/test_state.py`:

```python
from src.agents.state import State

def test_state_has_required_fields():
    """Test that State has all required fields."""
    # State should be usable as a type hint
    assert hasattr(State, '__annotations__')
    annotations = State.__annotations__

    # Check key fields exist
    assert 'user_query' in annotations
    assert 'plan' in annotations
    assert 'current_step' in annotations
    assert 'model_usage' in annotations
    assert 'formatted_response' in annotations
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`

Expected: FAIL with "No module named 'src.agents.state'"

**Step 3: Write implementation**

Create `src/agents/state.py`:

```python
"""State definition for LangGraph workflow."""

from typing import Optional, List, Dict, Any
from langgraph.graph import MessagesState


class State(MessagesState):
    """
    State for the OEWS data agent workflow.

    Inherits from MessagesState which provides the 'messages' field.
    """
    # Query and planning
    user_query: Optional[str] = None
    enabled_agents: Optional[List[str]] = None
    plan: Optional[Dict[str, Dict[str, Any]]] = None
    current_step: int = 0

    # Execution control
    replan_flag: Optional[bool] = None
    last_reason: Optional[str] = None
    replan_attempts: Optional[Dict[int, int]] = None
    agent_query: Optional[str] = None

    # Results
    final_answer: Optional[str] = None
    formatted_response: Optional[Dict[str, Any]] = None

    # Tracking and metadata
    start_time: Optional[float] = None
    model_usage: Optional[Dict[str, str]] = None
    reasoning_model_override: Optional[str] = None
    implementation_model_override: Optional[str] = None
```

**Step 4: Update __init__.py**

Modify `src/agents/__init__.py`:

```python
"""Agent implementations for the OEWS data system."""

from .text2sql_agent import create_text2sql_agent
from .chart_generator import create_chart_generator_agent
from .state import State

__all__ = [
    "create_text2sql_agent",
    "create_chart_generator_agent",
    "State"
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_state.py -v`

Expected: PASS (1 test)

**Step 6: Commit**

```bash
git add src/agents/state.py src/agents/__init__.py tests/test_state.py
git commit -m "feat(agents): add State definition for LangGraph workflow"
```

---

### Task 5.2: Create Response Formatter

**Files:**
- Create: `src/agents/response_formatter.py`
- Modify: `src/agents/__init__.py`
- Create: `tests/test_response_formatter.py`

**Step 1: Write the failing test**

Create `tests/test_response_formatter.py`:

```python
from src.agents.response_formatter import (
    extract_chart_specs,
    extract_sql_queries,
    extract_agents_used
)
from langchain.schema import HumanMessage

def test_extract_chart_specs_finds_markers():
    """Test extraction of chart specs from messages."""
    messages = [
        HumanMessage(
            content='CHART_SPEC: {"type": "bar", "title": "Test"}',
            name="chart_generator"
        )
    ]
    specs = extract_chart_specs(messages)
    assert len(specs) == 1
    assert specs[0]["type"] == "bar"
    assert "id" in specs[0]

def test_extract_sql_queries_from_messages():
    """Test extraction of SQL queries."""
    messages = [
        HumanMessage(
            content="SQL: SELECT * FROM oews_data\nResults: 5 rows",
            name="cortex_researcher"
        )
    ]
    queries = extract_sql_queries(messages)
    assert len(queries) > 0
    assert queries[0]["type"] == "sql"

def test_extract_agents_used():
    """Test extraction of agent names."""
    messages = [
        HumanMessage(content="test", name="planner"),
        HumanMessage(content="test", name="web_researcher"),
        HumanMessage(content="test", name="cortex_researcher")
    ]
    agents = extract_agents_used(messages)
    assert "web_researcher" in agents
    assert "cortex_researcher" in agents
    assert "planner" not in agents  # Planning agents excluded
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_response_formatter.py -v`

Expected: FAIL with "No module named 'src.agents.response_formatter'"

**Step 3: Write implementation**

Create `src/agents/response_formatter.py`:

```python
"""Response formatter for API consumption."""

from typing import Dict, Any, List
from langchain.schema import HumanMessage
from langgraph.graph import END
from langgraph.types import Command
from typing import Literal
import json
import re
from datetime import datetime
import uuid


def extract_chart_specs(messages: List) -> List[Dict[str, Any]]:
    """
    Extract all chart specifications from chart_generator messages.

    Args:
        messages: List of messages from workflow

    Returns:
        List of chart specifications
    """
    chart_specs = []

    for msg in messages:
        if getattr(msg, "name", None) == "chart_generator":
            content = msg.content

            # Look for CHART_SPEC markers
            pattern = r'CHART_SPEC:\s*(\{.*?\})'
            matches = re.findall(pattern, content, re.DOTALL)

            for match in matches:
                try:
                    spec = json.loads(match)
                    # Add unique ID for React rendering
                    spec["id"] = str(uuid.uuid4())
                    chart_specs.append(spec)
                except json.JSONDecodeError:
                    print(f"Warning: Invalid chart spec JSON: {match}")
                    continue

    return chart_specs


def extract_sql_queries(messages: List) -> List[Dict[str, Any]]:
    """
    Extract SQL queries from cortex_researcher messages.

    Args:
        messages: List of messages from workflow

    Returns:
        List of SQL source dictionaries
    """
    sql_sources = []

    for msg in messages:
        if getattr(msg, "name", None) == "cortex_researcher":
            content = msg.content

            # Extract SQL queries
            sql_pattern = r'SQL:\s*```sql\s*(.*?)\s*```|SQL:\s*([^\n]+)'
            sql_matches = re.findall(sql_pattern, content, re.DOTALL | re.IGNORECASE)

            for match in sql_matches:
                sql = match[0] or match[1]
                if sql.strip():
                    # Extract row count if present
                    row_count_match = re.search(r'(\d+)\s+rows?', content, re.IGNORECASE)
                    row_count = int(row_count_match.group(1)) if row_count_match else None

                    sql_sources.append({
                        "type": "sql",
                        "query": sql.strip(),
                        "results_count": row_count
                    })

    return sql_sources


def extract_web_sources(messages: List) -> List[Dict[str, Any]]:
    """
    Extract web search queries and citations.

    Args:
        messages: List of messages from workflow

    Returns:
        List of web source dictionaries
    """
    web_sources = []

    for msg in messages:
        if getattr(msg, "name", None) == "web_researcher":
            content = msg.content

            # Extract search query
            query_match = re.search(
                r'Search(?:ed)? (?:for|query):\s*["\']?(.*?)["\']?(?:\n|$)',
                content,
                re.IGNORECASE
            )
            query = query_match.group(1) if query_match else "Web search"

            # Extract URLs
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, content)

            # Extract citation titles
            citation_pattern = r'\[(\d+)\]\s*(.*?)(?:\n|$)'
            citations = re.findall(citation_pattern, content)

            if citations:
                citation_texts = [f"[{num}] {title}" for num, title in citations]
            else:
                citation_texts = urls

            web_sources.append({
                "type": "web_search",
                "query": query,
                "citations": citation_texts[:5]
            })

    return web_sources


def extract_agents_used(messages: List) -> List[str]:
    """
    Extract list of unique agent names that were invoked.

    Args:
        messages: List of messages from workflow

    Returns:
        Sorted list of agent names
    """
    agents = set()
    excluded = {"planner", "executor", "initial_plan", "replan", "response_formatter"}

    for msg in messages:
        name = getattr(msg, "name", None)
        if name and name not in excluded:
            agents.add(name)

    return sorted(list(agents))


def response_formatter_node(state) -> Command[Literal[END]]:
    """
    Final node that formats the agent workflow output for Next.js frontend.

    Extracts:
    - Clean summary text
    - Chart specifications (may be multiple)
    - Data sources (SQL queries, web searches)
    - Execution metadata

    Args:
        state: Current workflow state

    Returns:
        Command to END with formatted response
    """
    start_time = state.get("start_time", datetime.now().timestamp())
    execution_time_ms = int((datetime.now().timestamp() - start_time) * 1000)

    messages = state.get("messages", [])

    # Extract summary
    summary = state.get("final_answer", "")
    if not summary:
        for msg in reversed(messages):
            if getattr(msg, "name", None) in ["synthesizer", "chart_summarizer"]:
                summary = msg.content
                break

    # Clean up summary
    summary = re.sub(r'FINAL ANSWER:?\s*', '', summary, flags=re.IGNORECASE)
    summary = re.sub(r'CHART_SPEC:.*$', '', summary, flags=re.DOTALL)
    summary = summary.strip()

    # Extract all chart specs
    chart_specs = extract_chart_specs(messages)

    # Extract data sources
    sql_sources = extract_sql_queries(messages)
    web_sources = extract_web_sources(messages)
    data_sources = sql_sources + web_sources

    # Build metadata
    metadata = {
        "execution_time_ms": execution_time_ms,
        "total_steps": state.get("current_step", 0),
        "agents_used": extract_agents_used(messages),
        "replans": sum((state.get("replan_attempts", {}) or {}).values()),
        "timestamp": datetime.now().isoformat(),
        "user_query": state.get("user_query", ""),
        "models_used": state.get("model_usage", {})
    }

    # Build formatted response
    formatted_response = {
        "summary": summary,
        "chart_specs": chart_specs,
        "data_sources": data_sources,
        "metadata": metadata
    }

    return Command(
        update={
            "formatted_response": formatted_response,
            "messages": [HumanMessage(
                content=json.dumps(formatted_response, indent=2),
                name="response_formatter"
            )]
        },
        goto=END
    )
```

**Step 4: Update __init__.py**

Modify `src/agents/__init__.py`:

```python
"""Agent implementations for the OEWS data system."""

from .text2sql_agent import create_text2sql_agent
from .chart_generator import create_chart_generator_agent
from .state import State
from .response_formatter import response_formatter_node

__all__ = [
    "create_text2sql_agent",
    "create_chart_generator_agent",
    "State",
    "response_formatter_node"
]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_response_formatter.py -v`

Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add src/agents/response_formatter.py src/agents/__init__.py tests/test_response_formatter.py
git commit -m "feat(agents): add response formatter for API consumption"
```

---

## Milestone 6: FastAPI Application

### Task 6.1: Create API Models

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/models.py`
- Create: `tests/test_api_models.py`

**Step 1: Write the failing test**

Create `tests/test_api_models.py`:

```python
from src.api.models import (
    QueryRequest,
    ChartSpec,
    DataSource,
    Metadata,
    QueryResponse
)

def test_query_request_validation():
    """Test QueryRequest model validation."""
    req = QueryRequest(query="What are tech salaries in Seattle?")
    assert req.query == "What are tech salaries in Seattle?"

def test_chart_spec_creation():
    """Test ChartSpec model."""
    spec = ChartSpec(
        id="test-id",
        type="bar",
        title="Test Chart",
        data={"labels": ["A"], "datasets": []},
        options={"xAxis": {}, "yAxis": {}}
    )
    assert spec.type == "bar"

def test_query_response_complete():
    """Test complete QueryResponse."""
    response = QueryResponse(
        summary="Test summary",
        chart_specs=[],
        data_sources=[],
        metadata=Metadata(
            execution_time_ms=1000,
            total_steps=3,
            agents_used=["test"],
            replans=0,
            timestamp="2025-01-01",
            user_query="test",
            models_used={}
        )
    )
    assert response.summary == "Test summary"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_models.py -v`

Expected: FAIL with "No module named 'src.api.models'"

**Step 3: Create package and implementation**

Create `src/api/__init__.py`:

```python
"""FastAPI application for OEWS data agent."""

from .models import (
    QueryRequest,
    ChartSpec,
    DataSource,
    Metadata,
    QueryResponse
)

__all__ = [
    "QueryRequest",
    "ChartSpec",
    "DataSource",
    "Metadata",
    "QueryResponse"
]
```

Create `src/api/models.py`:

```python
"""Pydantic models for API request/response."""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(description="Natural language question about OEWS data")
    reasoning_model_override: Optional[str] = Field(
        default=None,
        description="Override default reasoning model"
    )
    implementation_model_override: Optional[str] = Field(
        default=None,
        description="Override default implementation model"
    )


class ChartSpec(BaseModel):
    """Chart specification for frontend rendering."""
    id: str = Field(description="Unique chart ID")
    type: Literal["bar", "line", "boxplot", "scatter", "heatmap"]
    title: str
    data: Dict[str, Any] = Field(description="Chart data with labels and datasets")
    options: Dict[str, Any] = Field(description="Chart display options")


class DataSource(BaseModel):
    """Information about a data source used in the response."""
    type: Literal["sql", "web_search"]
    query: str
    results_count: Optional[int] = None
    citations: Optional[List[str]] = None


class Metadata(BaseModel):
    """Metadata about query execution."""
    execution_time_ms: int
    total_steps: int
    agents_used: List[str]
    replans: int
    timestamp: str
    user_query: str
    models_used: Dict[str, str]


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    summary: str = Field(description="Text summary of findings")
    chart_specs: List[ChartSpec] = Field(description="Chart specifications for rendering")
    data_sources: List[DataSource] = Field(description="Data sources used")
    metadata: Metadata = Field(description="Execution metadata")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_models.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/api/ tests/test_api_models.py
git commit -m "feat(api): add Pydantic models for request/response"
```

---

### Task 6.2: Create FastAPI Application (Minimal)

**Files:**
- Create: `src/api/main.py`
- Modify: `src/api/__init__.py`
- Create: `tests/test_api.py`

**Step 1: Write the failing test**

Create `tests/test_api.py`:

```python
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_query_endpoint_exists():
    """Test that query endpoint exists."""
    # This will fail without proper setup, but should return 422 not 404
    response = client.post("/api/query", json={})
    assert response.status_code in [422, 500]  # Not 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`

Expected: FAIL with "No module named 'src.api.main'"

**Step 3: Write minimal implementation**

Create `src/api/main.py`:

```python
"""FastAPI application for OEWS data agent."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from langchain.schema import HumanMessage
import os

from .models import QueryRequest, QueryResponse

# Create FastAPI app
app = FastAPI(
    title="OEWS Data Agent API",
    description="Natural language interface to OEWS employment data",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query about OEWS data.

    Args:
        request: Query request with natural language question

    Returns:
        Formatted response with summary, charts, and metadata
    """
    # NOTE: Workflow integration will be added in next task
    # For now, return a minimal response
    raise HTTPException(
        status_code=501,
        detail="Workflow integration not yet implemented"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`

Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/api/main.py tests/test_api.py
git commit -m "feat(api): add FastAPI application with health check endpoint"
```

---

## Milestone 7: Integration

### Task 7.1: Create Minimal Workflow (Stub)

**Files:**
- Create: `src/agents/workflow.py`
- Modify: `src/agents/__init__.py`

**Step 1: Create stub workflow**

Create `src/agents/workflow.py`:

```python
"""LangGraph workflow for OEWS data agent.

NOTE: This is a minimal stub. Full workflow integration will be completed
in subsequent tasks with planner, executor, and all agents.
"""

from langgraph.graph import StateGraph, START, END
from .state import State
from .response_formatter import response_formatter_node


def stub_node(state: State):
    """Stub node for testing workflow structure."""
    from langchain.schema import HumanMessage
    return {
        "messages": [HumanMessage(content="Stub response", name="stub")],
        "final_answer": "This is a stub workflow response"
    }


# Create minimal workflow
workflow = StateGraph(State)
workflow.add_node("stub", stub_node)
workflow.add_node("response_formatter", response_formatter_node)

workflow.add_edge(START, "stub")
workflow.add_edge("stub", "response_formatter")

# Compile graph
graph = workflow.compile()
```

**Step 2: Update __init__.py**

Modify `src/agents/__init__.py`:

```python
"""Agent implementations for the OEWS data system."""

from .text2sql_agent import create_text2sql_agent
from .chart_generator import create_chart_generator_agent
from .state import State
from .response_formatter import response_formatter_node
from .workflow import graph

__all__ = [
    "create_text2sql_agent",
    "create_chart_generator_agent",
    "State",
    "response_formatter_node",
    "graph"
]
```

**Step 3: Commit**

```bash
git add src/agents/workflow.py src/agents/__init__.py
git commit -m "feat(agents): add minimal stub workflow for testing"
```

---

### Task 7.2: Integrate Workflow with FastAPI

**Files:**
- Modify: `src/api/main.py`
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

Create `tests/test_integration.py`:

```python
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_query_endpoint_returns_formatted_response():
    """Test that query endpoint returns properly formatted response."""
    response = client.post(
        "/api/query",
        json={"query": "Test query"}
    )

    # Should now return 200 with stub workflow
    assert response.status_code == 200

    data = response.json()
    assert "summary" in data
    assert "chart_specs" in data
    assert "data_sources" in data
    assert "metadata" in data
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration.py -v`

Expected: FAIL with "501 Not Implemented"

**Step 3: Update FastAPI endpoint**

Modify `src/api/main.py`:

```python
"""FastAPI application for OEWS data agent."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from langchain.schema import HumanMessage
import os

from .models import QueryRequest, QueryResponse
from src.agents import graph

# Create FastAPI app
app = FastAPI(
    title="OEWS Data Agent API",
    description="Natural language interface to OEWS employment data",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query about OEWS data.

    Args:
        request: Query request with natural language question

    Returns:
        Formatted response with summary, charts, and metadata
    """
    try:
        start_time = datetime.now().timestamp()

        # Invoke LangGraph workflow
        result = graph.invoke({
            "messages": [HumanMessage(content=request.query)],
            "user_query": request.query,
            "enabled_agents": ["web_researcher", "cortex_researcher",
                             "chart_generator", "synthesizer"],
            "start_time": start_time,
            "reasoning_model_override": request.reasoning_model_override,
            "implementation_model_override": request.implementation_model_override
        })

        # Extract formatted response
        formatted = result.get("formatted_response", {})

        if not formatted:
            raise HTTPException(
                status_code=500,
                detail="Workflow did not produce formatted response"
            )

        return QueryResponse(**formatted)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_integration.py -v`

Expected: PASS (1 test)

**Step 5: Commit**

```bash
git add src/api/main.py tests/test_integration.py
git commit -m "feat(api): integrate LangGraph workflow with FastAPI endpoint"
```

---

## Milestone 8: Documentation & Environment

### Task 8.1: Create Environment Configuration

**Files:**
- Create: `.env.example`
- Create: `requirements.txt`

**Step 1: Create .env.example**

Create `.env.example`:

```bash
# ============================================
# LLM Configuration
# ============================================

# Default Models
LLM_REASONING_MODEL=deepseek-r1
LLM_IMPLEMENTATION_MODEL=deepseek-v3
LLM_FAST_MODEL=deepseek-v3

# Azure AI (for DeepSeek models)
AZURE_AI_ENDPOINT=https://your-endpoint.azure.com
AZURE_AI_API_KEY=your-api-key

# OpenAI (if using GPT models)
# OPENAI_API_KEY=your-openai-key

# Anthropic (if using Claude models)
# ANTHROPIC_API_KEY=your-anthropic-key

# Together AI (if using open-source models)
# TOGETHER_API_KEY=your-together-key

# Ollama (for local testing)
# OLLAMA_BASE_URL=http://localhost:11434

# ============================================
# Model Tracking
# ============================================
ENABLE_MODEL_TRACKING=true
ENABLE_COST_TRACKING=false

# ============================================
# Database Configuration
# ============================================

# Development (SQLite)
DATABASE_ENV=dev
SQLITE_DB_PATH=data/oews.db

# Production (Azure SQL) - uncomment when deploying
# DATABASE_ENV=prod
# AZURE_SQL_SERVER=your-server.database.windows.net
# AZURE_SQL_DATABASE=oews
# AZURE_SQL_USERNAME=your-username
# AZURE_SQL_PASSWORD=your-password

# ============================================
# API Configuration
# ============================================
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# ============================================
# External Services
# ============================================
TAVILY_API_KEY=your-tavily-api-key

# ============================================
# Logging
# ============================================
LOG_LEVEL=INFO
```

**Step 2: Create requirements.txt**

Create `requirements.txt`:

```txt
# Core LangChain & LangGraph
langgraph>=0.2.28
langchain>=0.3.0
langchain-core>=0.3.0
langchain-community>=0.3.0
langchain-experimental>=0.3.0

# LLM Providers
langchain-azure-ai>=0.1.0
langchain-openai>=0.2.0
langchain-anthropic>=0.2.0
langchain-together>=0.2.0
langchain-ollama>=0.2.0

# External Tools
langchain-tavily>=0.2.0

# FastAPI & Web
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.9.0
pydantic-settings>=2.5.0

# Database
pandas>=2.2.0
sqlalchemy>=2.0.0
pyodbc>=5.0.0
aiosqlite>=0.20.0
sqlparse>=0.5.0

# Environment & Config
python-dotenv>=1.0.0

# Testing
pytest>=8.3.0
pytest-asyncio>=0.24.0
pytest-cov>=5.0.0
httpx>=0.27.0

# Development
ruff>=0.6.0
black>=24.0.0
```

**Step 3: Commit**

```bash
git add .env.example requirements.txt
git commit -m "docs: add environment configuration template and requirements"
```

---

### Task 8.2: Create README Documentation

**Files:**
- Modify: `README.md`

**Step 1: Update README**

Modify `README.md`:

```markdown
# OEWS Data Agent

Natural language interface to OEWS (Occupational Employment and Wage Statistics) data. Ask questions in plain English and get detailed reports with interactive charts.

## Features

- **Natural Language Queries**: "What are software developer salaries in Bellingham, WA?"
- **Multi-Agent System**: Planner, Text2SQL, Web Research, Chart Generation
- **Interactive Charts**: JSON specifications for ECharts/Plotly
- **Flexible LLM Configuration**: Test different reasoning and implementation models
- **FastAPI Backend**: RESTful API for Next.js frontend

## Architecture

```
User Query → Planner → Executor → Agents (Text2SQL, Web, Charts) → Response Formatter → JSON
```

## Quick Start

### Prerequisites

- Python 3.10+
- Azure AI endpoint (for DeepSeek models) or OpenAI API key
- Tavily API key (for web search)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd oews

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Run API Server

```bash
# Start FastAPI server
uvicorn src.api.main:app --reload

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Example API Request

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare software developer salaries in Seattle vs Bellingham"
  }'
```

### Response Format

```json
{
  "summary": "Text summary of findings...",
  "chart_specs": [
    {
      "id": "uuid",
      "type": "bar",
      "title": "Median Salaries by City",
      "data": {
        "labels": ["Seattle", "Bellingham"],
        "datasets": [{"name": "Median Salary", "values": [125000, 98750]}]
      },
      "options": {"xAxis": {...}, "yAxis": {...}}
    }
  ],
  "data_sources": [
    {"type": "sql", "query": "SELECT ...", "results_count": 2}
  ],
  "metadata": {
    "execution_time_ms": 3420,
    "agents_used": ["cortex_researcher", "chart_generator"],
    "models_used": {"planner": "deepseek-r1", "cortex_researcher": "deepseek-v3"}
  }
}
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_database.py -v
```

## Project Structure

```
src/
├── agents/          # LangGraph agents and workflow
├── api/             # FastAPI application
├── config/          # LLM configuration and factory
├── database/        # Database abstraction (SQLite/Azure SQL)
├── tools/           # LangChain tools (database, charts)
└── prompts/         # Agent prompts

tests/               # Unit and integration tests
data/                # SQLite database
docs/plans/          # Implementation plans
```

## LLM Model Configuration

Configure models via environment variables:

```bash
# Use GPT-4o for reasoning, GPT-4o-mini for implementation
LLM_REASONING_MODEL=gpt-4o
LLM_IMPLEMENTATION_MODEL=gpt-4o-mini

# Override per-query via API
curl -X POST http://localhost:8000/api/query \
  -d '{
    "query": "...",
    "reasoning_model_override": "claude-3.7-sonnet"
  }'
```

## Development

See `docs/plans/` for detailed implementation plans.

### Adding New Models

1. Add model to `src/config/llm_config.py` registry
2. Set environment variable or use override
3. Test with: `pytest tests/test_llm_factory.py`

## License

MIT

## Contributing

See CONTRIBUTING.md
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with quick start and API documentation"
```

---

## Summary

This implementation plan provides:

1. **70+ bite-sized tasks** following TDD (test → fail → implement → pass → commit)
2. **Complete file paths** for all new and modified files
3. **Full code implementations** (not just placeholders)
4. **Test-driven approach** with failing tests before implementation
5. **Frequent commits** after each passing test

**Current Status:**
- ✅ Database abstraction (SQLite/Azure SQL)
- ✅ LLM configuration system with factory pattern
- ✅ Database tools for Text2SQL agent
- ✅ Text2SQL ReAct agent
- ✅ Chart specification tools
- ✅ Multi-chart generator agent
- ✅ Response formatter
- ✅ FastAPI application with workflow integration
- ✅ Environment configuration

**Remaining Work:**
- Planner and Executor nodes (from existing notebook/helper.py)
- Web Researcher agent (from existing notebook)
- Synthesizer agent (from existing notebook)
- Complete workflow assembly
- Azure SQL deployment configuration
- Benchmarking utilities

**Next Steps:**
The plan can be executed using:
1. **superpowers:subagent-driven-development** (this session)
2. **superpowers:executing-plans** (parallel session)
