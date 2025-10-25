# OEWS Data Agent - Frontend API Integration

Simple guide for connecting GitHub Spark (or any frontend) to the OEWS Data Agent API.

## Quick Start

### API Endpoint
```
POST http://localhost:8000/api/v1/query
```

### Request Format
```json
{
  "query": "What is the median salary for software developers in Seattle?",
  "enable_charts": true
}
```

### Response Format
```json
{
  "answer": "The median annual salary for software developers in Seattle...",
  "charts": [],
  "data_sources": [],
  "metadata": {
    "models_used": {...},
    "execution_time_ms": 25000,
    "plan": {...}
  }
}
```

---

## JavaScript Example (for GitHub Spark)

### Simple Fetch Call

```javascript
async function queryOEWS(question) {
  const response = await fetch('http://localhost:8000/api/v1/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query: question,
      enable_charts: true
    })
  });

  const data = await response.json();
  return data;
}

// Usage
const result = await queryOEWS("What are software developer salaries in Seattle?");
console.log(result.answer);
```

### With Loading State

```javascript
async function askOEWS(question, onUpdate) {
  try {
    onUpdate({ loading: true, error: null });

    const response = await fetch('http://localhost:8000/api/v1/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: question,
        enable_charts: true
      })
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    const data = await response.json();
    onUpdate({ loading: false, data: data, error: null });
    return data;

  } catch (error) {
    onUpdate({ loading: false, error: error.message });
    throw error;
  }
}

// Usage in React/GitHub Spark
function handleSubmit() {
  askOEWS(userQuestion, (state) => {
    if (state.loading) {
      setStatus("Analyzing OEWS data...");
    } else if (state.error) {
      setError(state.error);
    } else {
      setAnswer(state.data.answer);
    }
  });
}
```

---

## Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Natural language question about employment data |
| `enable_charts` | boolean | No | `false` | Whether to generate visualizations |
| `reasoning_model` | string | No | `"deepseek-r1"` | Model for planning |
| `implementation_model` | string | No | `"deepseek-v3"` | Model for execution |

---

## Response Fields

### Success Response

```typescript
{
  answer: string;              // Natural language answer
  charts: Chart[];            // Array of chart specifications
  data_sources: DataSource[]; // Sources used (OEWS DB, web)
  metadata: {
    models_used: Record<string, string>;  // Which models were used
    execution_time_ms: number;            // How long it took
    plan: Record<string, Step>;           // Execution plan
    replans: number;                      // Times replanned
  }
}
```

### Error Response

```typescript
{
  detail: string;  // Error message
}
```

---

## Example Queries

### Simple Salary Query
```json
{
  "query": "What is the median salary for nurses in California?"
}
```

### Comparison Query
```json
{
  "query": "Compare software developer salaries in Seattle vs San Francisco",
  "enable_charts": true
}
```

### Trend Query
```json
{
  "query": "How have data scientist salaries changed in New York over the past 5 years?",
  "enable_charts": true
}
```

---

## For GitHub Spark

### 1. **Create a State Variable**
```javascript
const [answer, setAnswer] = useState("");
const [loading, setLoading] = useState(false);
```

### 2. **Add Form Handler**
```javascript
async function handleQuery(e) {
  e.preventDefault();
  setLoading(true);

  try {
    const response = await fetch('http://localhost:8000/api/v1/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: userInput,
        enable_charts: true
      })
    });

    const data = await response.json();
    setAnswer(data.answer || "No answer received");
  } catch (error) {
    setAnswer("Error: " + error.message);
  } finally {
    setLoading(false);
  }
}
```

### 3. **Display in UI**
```jsx
<form onSubmit={handleQuery}>
  <input
    value={userInput}
    onChange={(e) => setUserInput(e.target.value)}
    placeholder="Ask about employment data..."
  />
  <button disabled={loading}>
    {loading ? "Analyzing..." : "Ask"}
  </button>
</form>

{answer && (
  <div className="answer">
    {answer}
  </div>
)}
```

---

## Testing the API

### Using curl
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the median salary for software developers in Seattle?", "enable_charts": false}'
```

### Using Browser Console
```javascript
fetch('http://localhost:8000/api/v1/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "What are nurse salaries in Texas?",
    enable_charts: false
  })
})
.then(r => r.json())
.then(data => console.log(data.answer));
```

---

## Health Check

Check if the API is running:
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "workflow_loaded": true
}
```

---

## Notes

- **Response Time**: Queries typically take 20-40 seconds
- **CORS**: Already configured to allow GitHub Spark domains
- **Rate Limiting**: None currently (add if deploying to production)
- **Authentication**: None currently (add if deploying to production)

---

## Troubleshooting

### CORS Error
Make sure the API server is running and CORS is configured (already done).

### Long Response Time
Normal! The AI agents need 20-40 seconds to:
1. Plan the query
2. Search the OEWS database
3. Generate visualizations (if requested)
4. Synthesize the answer

### Connection Refused
Make sure the server is running:
```bash
python -m src.main
```

Then check health:
```bash
curl http://localhost:8000/health
```
