# GitHub Spark Prompt: OEWS Data Explorer Frontend

Copy and paste this prompt into GitHub Spark to build the frontend:

---

Build a professional React web application called "OEWS Data Explorer" that queries employment and wage data through an AI-powered backend API.

## Application Overview

Create a single-page search interface where users enter natural language questions about employment data and receive AI-generated summaries with interactive charts. Professional, corporate aesthetic similar to LinkedIn or business dashboards.

## Page Layout

### Header (Fixed)
- Height: 60px
- Background: Dark blue (#1e40af)
- Content:
  - Left side: "OEWS Data Explorer" (white text, 20px, semibold)
  - Right side: "Employment & Wage Statistics" (white text, 14px)
- Add subtle box shadow for depth

### Main Content (Centered, Max 1200px)
- White background
- Padding: 40px on desktop, 20px on mobile
- Use system fonts: Inter, SF Pro, or Segoe UI

## Search Interface

### Input Area (Centered at top)
Create a search box with these specs:
- Width: 600px (desktop), 100% (mobile)
- Height: 56px
- Placeholder: "Ask about salaries, occupations, or locations... (e.g., 'What are software developer salaries in Seattle?')"
- Border: 2px solid light gray (#d1d5db), changes to blue (#2563eb) on focus
- Add search icon on left side
- Add clear button (X) on right when text is entered

### Submit Button (Next to search box)
- Label: "Analyze"
- Styling: Blue background (#2563eb), white text
- Size: 120px wide, 56px height
- Loading state: Show spinner with text "Analyzing..."

### Example Queries (Below search box)
Show "Try these examples:" with 3 clickable chips:
1. "Median salary for nurses in California"
2. "Compare software developers in Seattle vs Portland"
3. "Top paying occupations in tech"

Clicking a chip fills the search box with that query.

## Results Display (Vertical Flow)

Show results in vertical sections after query completes:

### 1. Summary Section
- White card with rounded corners (8px), subtle shadow, 32px padding
- Heading: "Summary" (18px, semibold, gray)
- Display the answer text (16px, line height 1.6)
- Highlight numbers in blue

### 2. Charts Section (if charts exist)
- Heading: "Visualizations" (18px, semibold, gray)
- For each chart:
  - White card (same styling as summary)
  - Chart title from data (16px, semibold)
  - Render using Chart.js (install: `npm install chart.js react-chartjs-2`)
  - Charts are responsive, professional blue/gray color scheme
  - Support chart types: bar, line, scatter

### 3. Data Sources Section (Collapsible)
- Accordion/collapsible section (collapsed by default)
- Heading: "Data Sources" with arrow icon
- When expanded: Show list of data sources used

## API Integration

### Configuration
- API endpoint: `http://localhost:8000/api/v1/query`
- Method: POST
- Headers: `Content-Type: application/json`
- Request body:
```json
{
  "query": "user's question here",
  "enable_charts": true
}
```

### Response Format
```json
{
  "answer": "The median salary...",
  "charts": [
    {
      "id": "uuid",
      "type": "bar",
      "title": "Chart Title",
      "data": {
        "labels": ["Seattle", "Portland"],
        "datasets": [
          {
            "name": "Median Salary",
            "values": [125000, 115000]
          }
        ]
      },
      "options": {
        "xAxis": {"title": "City", "type": "category"},
        "yAxis": {"title": "Salary ($)", "type": "value"}
      }
    }
  ],
  "data_sources": [
    {
      "type": "sql",
      "query": "SELECT ...",
      "results_count": 2
    }
  ],
  "metadata": {
    "execution_time_ms": 25000,
    "models_used": {"planner": "deepseek-r1"}
  }
}
```

### State Management
Use React useState hooks:
- `query` - search input text
- `loading` - boolean for loading state
- `results` - API response data
- `error` - error message if any

### API Call Flow
1. User clicks "Analyze"
2. Set loading to true, disable input
3. Show loading message: "Analyzing data... (this may take 20-40 seconds)"
4. Make POST request to API
5. On success: Display results, scroll to summary section
6. On error: Show error message below search box in red

## Loading States

While API is processing:
- Disable search input and button
- Show spinner in button with "Analyzing..." text
- Display estimated time: "This may take 20-40 seconds"
- After 20 seconds: Add "Still working..."
- After 40 seconds: Add "Almost done..."

## Error Handling

Show error messages for these cases:
- Network error: "Unable to connect to the server. Make sure the API is running at localhost:8000"
- Timeout (>60s): "Query is taking longer than expected. Please try again."
- API error: Show the error message from backend
- Empty results: "No data found. Try rephrasing your question."

## Chart Rendering

For each chart in `results.charts`:
1. Extract chart data: type, title, labels, datasets
2. Convert to Chart.js format
3. Use professional color palette (blues: #2563eb, #3b82f6, grays: #6b7280)
4. Make charts responsive (fill container width)
5. Chart types to support: bar, line, scatter

Example Chart.js code structure:
```javascript
import { Bar, Line, Scatter } from 'react-chartjs-2';

const chartData = {
  labels: chart.data.labels,
  datasets: chart.data.datasets.map(ds => ({
    label: ds.name,
    data: ds.values,
    backgroundColor: '#2563eb',
    borderColor: '#1e40af'
  }))
};

const options = {
  responsive: true,
  plugins: {
    title: { display: true, text: chart.title }
  }
};

// Render based on chart.type
{chart.type === 'bar' && <Bar data={chartData} options={options} />}
```

## Styling Requirements

### Colors
- Primary blue: #2563eb
- Dark blue (header): #1e40af
- Light gray (borders): #d1d5db
- Dark gray (text): #374151
- White (background): #ffffff
- Red (errors): #dc2626

### Spacing
- Card padding: 32px
- Margin between sections: 40px
- Margin between charts: 24px
- Mobile: Reduce to 20px and 16px respectively

### Professional Look
- Cards have subtle shadows
- Rounded corners (8px)
- Clean, minimal design
- No unnecessary decorations

## Mobile Responsive

- Single column layout on all screen sizes
- Search box full width on mobile
- Reduce padding on mobile (20px instead of 40px)
- Charts stack vertically
- Text remains readable

## Additional Features

- Scroll to results automatically after query completes
- Clear button (X) in search box when text is entered
- Example queries clickable to fill search box
- Data sources section collapsible to save space

## Technical Stack

- React (use functional components with hooks)
- Chart.js + react-chartjs-2 for visualizations
- No router needed (single page)
- No complex state management needed (useState is sufficient)
- Modern ES6+ JavaScript

## Testing Locally

Users will test by:
1. Running backend API on `localhost:8000`
2. Running this frontend app
3. Entering queries like "What are software developer salaries in Seattle?"
4. Verifying results display correctly with charts

Build a clean, professional interface that prioritizes clarity and ease of use. Keep the design minimal and focused on the core search experience.
