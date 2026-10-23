WindInsights
A full-stack dashboard for evaluating Great Britain wind generation forecasts against actual output using historical hourly data.

Live dashboard: https://windinsights-dashboard.vercel.app
Backend API: https://windinsights-api.onrender.com
Repository: https://github.com/anupam1308/w8k3m2q9
Overview
WindInsights helps users inspect forecast performance over a selected date range. It presents forecast accuracy metrics alongside hourly actual-versus-forecast trends and forecast error visualisations.

The project uses a FastAPI backend to serve the historical evaluation dataset and a React dashboard to display metrics and charts.
Features
- Filter the evaluation period by start and end date.
- View key forecast accuracy metrics:
  - Mean Absolute Error (MAE)
  - Root Mean Square Error (RMSE)
  - Forecast bias
  - Median Absolute Error
  - 90th percentile absolute error (P90)
  - 95th percentile absolute error (P95)
- Compare hourly actual generation with forecast generation.
- Inspect forecast errors over the selected period.
- Display API connection, loading, error, and empty states.
- Responsive dashboard layout.
Evaluation snapshot
The available dataset contains 744 hourly intervals. For the full evaluation period represented in the project, the displayed metrics are:
Metric	Value
Mean Absolute Error (MAE)	2,142.12 MW
Root Mean Square Error (RMSE)	2,611.70 MW
Mean forecast bias	+1,851.90 MW
Median Absolute Error	1,787.75 MW
P90 absolute error	4,300.15 MW
P95 absolute error	5,307.25 MW


A positive bias indicates over-forecasting when bias is calculated as forecast minus actual. These values describe the supplied historical dataset, not a live forecast or a guarantee of future performance.
Tech stack
Frontend
- React
- TypeScript
- Vite
- Recharts
- Lucide React
Backend
- Python
- FastAPI
- Pandas
- Uvicorn
Deployment
- Vercel — frontend
- Render — backend API
Architecture
Browser
  |
  v
React + TypeScript dashboard (Vercel)
  |
  | HTTPS requests
  v
FastAPI service (Render)
  |
  v
Historical hourly evaluation CSV
The frontend uses the VITE_API_URL environment variable as the API base URL.
API endpoints
Base URL: https://windinsights-api.onrender.com
Method	Endpoint	Purpose
GET	/health	Health check
GET	/api/metrics	Aggregated evaluation metrics
GET	/api/forecasts	Hourly forecast and actual data


The metrics and forecasts endpoints accept optional start_date and end_date query parameters.

Example:
https://windinsights-api.onrender.com/api/metrics?start_date=2026-01-01&end_date=2026-01-31
Run locally
Prerequisites
- Python 3.10+ (use the version supported by the backend dependencies)
- Node.js and npm
- Git
1. Clone the repository
git clone https://github.com/anupam1308/w8k3m2q9.git
cd w8k3m2q9
2. Start the backend
From the repository root, create and activate a virtual environment:

Windows PowerShell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
The API should be available at http://127.0.0.1:8000.

If PowerShell blocks virtual-environment activation, run the environment's Python executable directly or follow your local Python execution-policy guidance.
3. Start the frontend
Open a second terminal:
cd frontend
npm install
Create frontend/.env.local with:
VITE_API_URL=http://127.0.0.1:8000
Then start Vite:
npm run dev
Open the local URL printed by Vite, usually http://localhost:5173.
Docker
If using the repository's Docker Compose configuration, run this from the repository root:
docker compose up --build
Configuration
Variable	Where	Description
VITE_API_URL	Frontend build environment	Base URL of the FastAPI backend


For local development, use http://127.0.0.1:8000. In the deployed Vercel project, set it to https://windinsights-api.onrender.com and redeploy after changing it.

The backend must allow the frontend origin through its CORS configuration. The deployed frontend origin is https://windinsights-dashboard.vercel.app.
Tests
Run frontend tests from the frontend directory:
npm test
Build the frontend:
npm run build
Run backend tests from the repository root using the project's virtual environment:
.\backend\.venv\Scripts\python.exe -m pytest
Deployment notes
- The frontend is deployed on Vercel from the frontend directory.
- The backend is deployed as a Docker web service on Render.
- Render's free instance may spin down after inactivity, so the first request after a period of inactivity can take longer.
- If the browser reports a fetch or CORS error, verify the Render service is live, the frontend VITE_API_URL points to the Render API, and the backend CORS origins include the deployed Vercel domain.
Limitations
- The dashboard evaluates the historical dataset included with the project; it is not a live wind-generation forecasting service.
- Results depend on the coverage and quality of the supplied data.
- The Render free service may have cold-start delays.
License
No license is specified here. Add a license file if you intend to grant others explicit permission to reuse or distribute this project.