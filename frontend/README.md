# EngageIQ — HCP Engagement Intelligence

A minimal, responsive HTML/CSS/JavaScript frontend for the HCP Engagement Intelligence application.

## Design
- Poppins typography
- Clean healthcare/pharma enterprise layout
- Left navigation sidebar
- Minimal rounded cards and subtle borders
- Dashboard analytics and predictive recommendation styling
- Responsive tablet/mobile support

## Features
1. Overall HCP dashboard with Total HCPs, High, Medium, Low and Average Hybrid Engagement Score.
2. Overall Engagement donut chart.
3. Engagement Score Distribution bar chart.
4. Channel Effectiveness comparison.
5. Baseline vs Model-Driven Channel Allocation chart.
6. Debounced HCP ID/name search (400 ms).
7. Individual HCP profile and engagement summary.
8. Channel probability bars.
9. API-provided Next Best Channel and recommendation reason.
10. Loading and error handling.

## API
Set the API base URL before loading the pages:
```js
localStorage.setItem('HCP_API_BASE_URL', 'https://your-fastapi-url');
```
Or define `window.API_BASE_URL` before `script.js`/`hcp.js`.

Expected endpoints:
- GET /api/dashboard
- GET /api/hcps/{hcp_id}
- GET /api/hcps?query={query} (optional search endpoint format)

The frontend never connects directly to Amazon RDS and does not run ML logic. Aggregation, large dataset processing, predictions and recommendations remain in FastAPI/backend services.

## Run
Open `index.html` using a local static server such as VS Code Live Server. For production, host these static files on your preferred web server/CDN and configure the API URL.
