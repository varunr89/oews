# OEWS Data Agent - Implementation Complete

Multi-agent system for querying OEWS employment data using natural language, built with LangGraph, LangChain, and FastAPI.

## Front End Application

The web interface for this application is available at: **https://govdatagent.projects.bhavanaai.com**

All feedback for the application and new feature requests should be submitted through the front end.

## Architecture

The system uses a **Planner-Executor pattern** with specialized sub-agents:

1. **Planner** - Creates execution plan from user query (DeepSeek-R1 reasoning model)
2. **Executor** - Routes to appropriate agents based on plan
3. **Cortex Researcher** (Text2SQL) - Queries OEWS database with secure parameterized queries
4. **Chart Generator** - Creates chart specifications for visualizations
5. **Synthesizer** - Creates text summaries of findings
6. **Response Formatter** - Formats final JSON response for API

## Features Implemented

### ✅ Milestone 1: Foundation
- **Task 1.2**: Schema metadata with LLM-optimized descriptions
- **Task 1.3**: YAML-based LLM configuration (DeepSeek, GPT-4o, Ollama support)
- **Task 1.4**: Multi-provider LLM factory (Azure AI, OpenAI, Anthropic, Ollama)

### ✅ Milestone 2: Secure Database Tools
- **Task 2.1**: Parameterized query tools with SQL injection protection
  - `get_schema_info`, `validate_sql`, `execute_sql_query`
  - `search_areas`, `search_occupations`

### ✅ Milestone 5-6: State Management & Workflow
- **Task 5.1**: LangGraph state management with MessagesState
- **Task 6.3**: Executor node with routing logic and replan handling
- **Task 6.4**: Complete workflow assembly with all agents

### ✅ Milestone 7: FastAPI Application
- **Task 7.1**: Pydantic models and REST endpoints
  - `/api/v1/query` - Process natural language queries
  - `/api/v1/models` - List available LLM models
  - `/health` - Health check endpoint
- **Task 7.2**: Server entry point and startup scripts

### ✅ Enhancement: Production Readiness
- **Task 8.1**: Large result set handling (>1000 rows auto-summarized)

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Set Environment Variables

```bash
# Required for Azure AI models (DeepSeek)
export AZURE_AI_API_KEY="your-key-here"
export AZURE_AI_ENDPOINT="https://your-endpoint.azure.com"

# Or use OpenAI
export OPENAI_API_KEY="your-key-here"

# Database configuration
export DATABASE_ENV="dev"  # or "prod" for Azure SQL
export SQLITE_DB_PATH="data/oews.db"
```

### 3. Start the API Server

```bash
# Using the startup script
./scripts/start_server.sh

# Or directly with Python
python -m src.main
```

The API will be available at `http://localhost:8000`

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Query example
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the median salaries for software developers in Seattle?",
    "enable_charts": false
  }'

# List available models
curl http://localhost:8000/api/v1/models
```

## API Documentation

Interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
src/
├── agents/           # LangGraph workflow nodes
│   ├── planner.py           # Plan creation
│   ├── executor.py          # Agent routing
│   ├── text2sql_agent.py    # Database queries
│   ├── chart_generator.py   # Visualization specs
│   ├── response_formatter.py # API output
│   └── state.py             # Workflow state
├── api/              # FastAPI application
│   ├── endpoints.py         # REST endpoints
│   └── models.py            # Pydantic models
├── config/           # Configuration
│   ├── llm_config.py        # Model registry
│   └── llm_factory.py       # LLM instantiation
├── database/         # Data layer
│   ├── connection.py        # DB abstraction
│   └── schema.py            # Schema metadata
├── prompts/          # Prompt templates
│   ├── planner_prompts.py
│   └── executor_prompts.py
├── tools/            # LangChain tools
│   └── database_tools.py    # Secure SQL tools
├── workflow/         # LangGraph assembly
│   └── graph.py             # Workflow graph
└── main.py           # Server entry point

config/
└── llm_models.yaml   # Model configuration

tests/                # Test suite
├── test_database.py
├── test_schema.py
├── test_llm_config.py
├── test_llm_factory.py
└── test_database_tools.py
```

## Security Features

1. **Parameterized Queries**: All SQL queries use `?` placeholders to prevent SQL injection
2. **SQL Validation**: Dangerous operations (DROP, DELETE, etc.) are rejected
3. **Connection Pooling**: Production-ready database connection management
4. **API Key Management**: Secure environment variable configuration

## Configuration

Edit `config/llm_models.yaml` to:
- Add/remove LLM models
- Change default reasoning/implementation models
- Configure cost tracking and model parameters

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_database_tools.py -v

# Run with coverage
pytest --cov=src --cov-report=html
```

## Git History

Recent commits implementing the plan:
- `aed862f` - FastAPI endpoints, server entry point, large result handling
- `abe032d` - Executor node, workflow assembly, agents
- `138568e` - Secure database tools with parameterized queries
- `44b934f` - LLM factory for multi-provider support
- `c4e790f` - YAML-based LLM configuration
- `ab16ba2` - Schema metadata with security notes
- `e817980` - Database connection with parameterized queries

## Next Steps

1. **Populate Database**: Import OEWS data using existing CLI tools
2. **Add Tests**: Write integration tests for workflow execution
3. **Web Research**: Implement Tavily integration for external data
4. **Frontend**: Build Next.js UI consuming the API
5. **Deployment**: Deploy to Azure with production SQL database

## Architecture Decisions

- **LangGraph** for workflow orchestration (vs. custom state machine)
- **Planner-Executor pattern** for flexible multi-agent routing
- **Parameterized queries** for security (vs. string formatting)
- **Large result summarization** for performance (>1000 rows)
- **YAML configuration** for model flexibility (vs. hardcoded)
- **ReAct agents** for tool-using agents (Text2SQL, Charts)

## Model Usage Tracking

The system tracks which models are used for each agent:
- Planner: reasoning model (default: DeepSeek-R1)
- Agents: implementation model (default: DeepSeek-V3)
- Can override per-request via API

Metadata includes:
- Models used per agent
- Execution time
- Plan structure
- Number of replans

## Performance Optimizations

1. **Workflow Graph Initialization**: Created once at startup (lifespan context)
2. **Connection Pooling**: Reuses database connections in production
3. **Large Result Handling**: Auto-summarizes queries returning >1000 rows
4. **Agent Caching**: Agent instances reused across requests

## Support

For issues or questions:
- Check API documentation at `/docs`
- Review test files for usage examples
- See plan analysis in `docs/plans/`
