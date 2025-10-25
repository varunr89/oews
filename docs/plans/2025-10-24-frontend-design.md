# OEWS Data Explorer - Frontend Design

**Date:** 2025-10-24
**Purpose:** Design specification for GitHub Spark frontend that integrates with OEWS Data Agent API

## Overview

A professional, search-engine style web interface for querying OEWS employment and wage data using natural language. Users enter questions, get AI-generated summaries with interactive charts.

**Design Principles:**
- Quick single queries (not research sessions)
- Professional/corporate aesthetic
- Vertical flow layout (like Google search results)
- Chart.js for visualizations
- Mobile-responsive

---

## Page Structure

### Header
- **Layout:** Fixed header, 60px height, dark blue background (#1e40af)
- **Content:**
  - Left: "OEWS Data Explorer" title (white text, 20px semibold)
  - Right: "Employment & Wage Statistics" subtitle (white text, 14px)
  - Optional: Small bar chart icon or BLS logo
- **Styling:** Box shadow for depth, professional typography (Inter, SF Pro, Segoe UI fallback)

### Main Content Area
- **Max width:** 1200px, centered
- **Padding:** 40px desktop, 20px mobile
- **Background:** White (#ffffff)
- **Responsive:** Single column on all screen sizes

---

## Search Input Area

### Search Box
- **Width:** 600px desktop, 100% mobile
- **Height:** 56px
- **Placeholder:** "Ask about salaries, occupations, or locations... (e.g., 'What are software developer salaries in Seattle?')"
- **Border:** 2px solid light gray (#d1d5db), becomes blue (#2563eb) on focus
- **Icons:**
  - Search icon on left
  - Clear button (X) on right when text is entered

### Submit Button
- **Label:** "Analyze" (emphasizes AI processing)
- **Styling:** Primary blue (#2563eb), white text, 120px wide, 56px height
- **Position:** Right of search box
- **Loading state:** Spinner with text "Analyzing..."

### Example Queries
- **Position:** Below search box
- **Label:** "Try these examples:" (gray text, 14px)
- **Examples:** 3 clickable chips/pills:
  1. "Median salary for nurses in California"
  2. "Compare software developers in Seattle vs Portland"
  3. "Top paying occupations in tech"
- **Behavior:** Clicking fills search box with query

### States
- **Empty:** Show examples
- **Typing:** Hide examples, show clear button
- **Loading:** Disable input, show spinner in button
- **Error:** Red border, error message below in red

---

## Results Display (Vertical Flow)

### Summary Section
- **Container:** White card, subtle shadow, 8px rounded corners, 32px padding
- **Margin:** 40px from search box
- **Heading:** "Summary" (18px semibold, dark gray)
- **Icon:** Small info or lightbulb icon top-left
- **Text:** 16px, line height 1.6, comfortable reading
- **Formatting:** Preserve markdown bold/italic if backend sends it
- **Highlights:** Numbers highlighted in blue

### Charts Section
- **Condition:** Only appears if `chart_specs` array has items
- **Heading:** "Visualizations" (18px semibold, dark gray)
- **Layout:** Each chart in white card (same styling as summary), 24px margin between
- **Chart Title:** From `chart_spec.title` (16px semibold)
- **Chart.js Config:**
  - Responsive: true
  - Maintain aspect ratio: true
  - Color palette: Professional blues/grays matching header
  - Types supported: bar, line, boxplot, scatter, heatmap

### Data Sources Section
- **UI:** Collapsible accordion (collapsed by default)
- **Heading:** "Data Sources" with expand/collapse arrow
- **Content:** List of SQL queries or web searches
- **Styling:** Small cards, monospace font for SQL, show execution time if available

---

## API Integration

### Configuration
- **Endpoint:** `http://localhost:8000/api/v1/query`
- **Method:** POST
- **Headers:** `Content-Type: application/json`
- **Request:**
  ```json
  {
    "query": "user's question",
    "enable_charts": true
  }
  ```
- **Expected response time:** 20-40 seconds (communicate to users)

### State Management (React)
```javascript
const [query, setQuery] = useState("");
const [loading, setLoading] = useState(false);
const [results, setResults] = useState(null);
const [error, setError] = useState(null);
```

### API Call Flow
1. User clicks "Analyze" → `setLoading(true)`, `setError(null)`
2. Show loading: "Analyzing data... (this may take 20-40 seconds)"
3. Fetch request to backend
4. Success: `setResults(data)`, `setLoading(false)`, scroll to results
5. Error: `setError(message)`, `setLoading(false)`, show error banner

### Chart Data Conversion
- Backend sends: `{type, title, data: {labels, datasets}, options}`
- Convert to Chart.js format:
  - Map `datasets` array to Chart.js dataset structure
  - Apply color palette
  - Configure responsive options

### Environment Configuration
- Use `.env.local`: `REACT_APP_API_URL=http://localhost:8000`
- For deployment: Update to cloud URL

---

## Error Handling & Edge Cases

### Error Messages
- **Network error:** "Unable to connect to the server. Make sure the API is running at localhost:8000"
- **Timeout (>60s):** "Query is taking longer than expected. The backend may be processing a complex request."
- **API error (500):** Show backend's `detail` field
- **Empty results:** "No data found for this query. Try rephrasing or ask about a different occupation/location."
- **No charts:** Don't show empty charts section

### Loading States
- **Progress indicator:** "Analyzing data... (20-40 seconds)"
- **After 20s:** Add "Still working..."
- **After 40s:** Add "Almost done..."
- **UI:** Disable search input/button, pulse animation on button

### Edge Cases
- **Long answers:** Limit summary to 400px height with "Show more" button
- **Multiple charts (3+):** Stack vertically with spacing
- **Mobile:** Responsive charts, reduce padding to 16px
- **No JavaScript:** Show message "This application requires JavaScript"

### Footer (Optional)
- **Content:** "Execution time: {metadata.execution_time_ms}ms | Models used: {metadata.models_used}"
- **Styling:** Gray text, small font, bottom of page

---

## Technical Requirements

### Dependencies
- React (via GitHub Spark)
- Chart.js + react-chartjs-2
- No additional state management libraries needed
- No routing needed (single page)

### Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile browsers (iOS Safari, Chrome Mobile)

### Performance
- Charts render on client side (Chart.js handles this)
- No pagination needed (single query results)
- Lazy load charts if 3+ returned

---

## Design System

### Colors
- **Primary blue:** #2563eb
- **Dark blue (header):** #1e40af
- **Light gray (borders):** #d1d5db
- **Dark gray (text):** #374151
- **White (background):** #ffffff
- **Red (errors):** #dc2626

### Typography
- **Font family:** System fonts (Inter, SF Pro, Segoe UI, fallback to system sans-serif)
- **Heading sizes:** 20px (title), 18px (section headers), 16px (chart titles)
- **Body text:** 16px, line height 1.6
- **Small text:** 14px (examples, footer)

### Spacing
- **Card padding:** 32px
- **Section margins:** 40px
- **Card margins:** 24px between charts
- **Mobile padding:** 20px (replace 40px), 16px (replace 32px)

### Shadows
- **Card shadow:** `0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)`
- **Header shadow:** `0 2px 4px rgba(0,0,0,0.1)`

### Border Radius
- **Cards:** 8px
- **Input/buttons:** 6px
- **Pills/chips:** 16px

---

## Success Criteria

1. **Functional:** Successfully calls backend API and displays results
2. **Professional:** Clean, corporate aesthetic matching design system
3. **Responsive:** Works on mobile and desktop
4. **Fast:** Renders charts quickly once data received
5. **Clear:** Loading states and error messages guide users
6. **Simple:** No unnecessary features, focused on single query workflow
