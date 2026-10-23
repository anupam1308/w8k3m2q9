import { useEffect, useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './App.css'

type Metrics = { intervals_evaluated: number; mae_mw: number; rmse_mw: number; bias_mw: number; median_absolute_error_mw: number; p90_absolute_error_mw: number; p95_absolute_error_mw: number }
type Forecast = { hour: string; actual_mw: number; forecast_mw: number; forecast_publish_time: string | null; cutoff_time: string | null }
type ForecastResponse = { count: number; data: Forecast[] }
type ApiState = 'loading' | 'ready' | 'error'
type ChartPoint = Forecast & { error_mw: number; label: string }
const initialStart = '2026-01-01'
const initialEnd = '2026-01-31'
const metricsConfig = [
  { key: 'mae_mw', label: 'Mean absolute error', short: 'MAE', note: 'Average absolute deviation' },
  { key: 'rmse_mw', label: 'Root mean square error', short: 'RMSE', note: 'Penalizes larger misses' },
  { key: 'bias_mw', label: 'Forecast bias', short: 'Bias', note: 'Forecast − actual' },
  { key: 'median_absolute_error_mw', label: 'Median absolute error', short: 'Median AE', note: 'Typical absolute deviation' },
  { key: 'p90_absolute_error_mw', label: '90th percentile error', short: 'P90 error', note: '90% of errors at or below' },
  { key: 'p95_absolute_error_mw', label: '95th percentile error', short: 'P95 error', note: '95% of errors at or below' },
] as const

function formatMw(value: number | null | undefined) { return value == null || !Number.isFinite(value) ? '—' : `${new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 }).format(value)} MW` }
function hourLabel(hour: string) { return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }).format(new Date(hour)) }
function fullTimestamp(hour: string) { return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }).format(new Date(hour)) }
class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) { super(message); this.status = status }
}
async function getJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try { const body = await response.json() as { detail?: string }; if (body.detail) message = body.detail } catch { /* use status text */ }
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}

function App() {
  const [startDate, setStartDate] = useState(initialStart)
  const [endDate, setEndDate] = useState(initialEnd)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [forecasts, setForecasts] = useState<Forecast[]>([])
  const [apiState, setApiState] = useState<ApiState>('loading')
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const query = new URLSearchParams({ start_date: startDate, end_date: endDate }).toString()
    if (startDate > endDate) return () => controller.abort()
    Promise.resolve().then(() => {
      if (controller.signal.aborted) return null
      setApiState('loading'); setError('')
      return Promise.all([
        getJson<ForecastResponse>(`/api/forecasts?${query}`, controller.signal),
        getJson<{ status: string }>('/health', controller.signal),
        getJson<Metrics>(`/api/metrics?${query}`, controller.signal).catch((reason: unknown) => {
          if (reason instanceof ApiError && reason.status === 404) return null
          throw reason
        }),
      ])
    }).then((result) => {
      if (!result) return
      const [forecastData, healthData, metricData] = result
      if (healthData.status !== 'ok') throw new Error('The API health check did not return an OK status.')
      if (!Array.isArray(forecastData.data)) throw new Error('The forecasts API returned an invalid response.')
      setMetrics(metricData); setForecasts(forecastData.data); setApiState('ready')
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return
      setApiState('error'); setError(reason instanceof Error ? reason.message : 'Unable to load dashboard data.')
      setMetrics(null); setForecasts([])
    })
    return () => controller.abort()
  }, [startDate, endDate, refreshKey])

  const chartData = useMemo<ChartPoint[]>(() => forecasts.map((item) => ({ ...item, error_mw: item.forecast_mw - item.actual_mw, label: hourLabel(item.hour) })), [forecasts])
  const validRange = startDate <= endDate
  const biasValue = metrics?.bias_mw

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#main" aria-label="Wind Insights home"><span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M16 4v12M16 16 6 11M16 16l10-5M16 16l-2 12M16 16l10 8"/><circle cx="16" cy="16" r="2.5"/></svg></span><span>Wind<span className="brand-light">Insights</span></span></a><div className="topbar-meta">Historical evaluation dataset <span className="topbar-divider"/> GB system</div></header>
    <main id="main" className="dashboard">
      <div className="page-heading"><div><div className="eyebrow">RENEWABLES / PERFORMANCE</div><h1>Forecast accuracy</h1><p className="subtitle">A clear view of how wind generation forecasts tracked against actual output across Great Britain.</p></div><div className={`api-status status-${apiState}`} role="status"><span className="status-indicator"/><span>{apiState === 'loading' ? 'Connecting to API' : apiState === 'ready' ? 'API connected' : 'API unavailable'}</span></div></div>
      <section className="filter-bar" aria-label="Date range filters"><div className="filter-intro"><span className="filter-icon" aria-hidden="true">▦</span><div><strong>Evaluation period</strong><small>Choose a date range</small></div></div><div className="date-fields"><label>From<input type="date" min="2026-01-01" max="2026-01-31" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label><span className="date-separator" aria-hidden="true">→</span><label>To<input type="date" min="2026-01-01" max="2026-01-31" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label></div><div className="filter-note">January 2026</div></section>
      {!validRange && <div className="inline-alert" role="alert">The start date must be before the end date.</div>}
      {apiState === 'error' && <section className="state-panel error-panel" role="alert"><div className="state-icon">!</div><div><h2>We couldn’t load the forecast data</h2><p>{error}</p><button className="retry-button" onClick={() => setRefreshKey((key) => key + 1)}>Try again <span aria-hidden="true">↗</span></button></div></section>}
      {apiState === 'loading' && <section className="loading-wrap" aria-label="Loading dashboard"><div className="loading-heading"/><div className="loading-kpis">{metricsConfig.map((metric) => <div className="loading-card" key={metric.key}/>)}</div><div className="loading-chart"/></section>}
      {apiState === 'ready' && !validRange && null}
      {apiState === 'ready' && validRange && <>
        <section className="section-block" aria-labelledby="metrics-heading"><div className="section-heading"><div><div className="section-kicker">AT A GLANCE</div><h2 id="metrics-heading">Accuracy metrics</h2></div><span className="sample-count">{metrics?.intervals_evaluated.toLocaleString('en-GB') ?? '—'} hourly intervals</span></div><div className="kpi-grid">{metricsConfig.map((item) => { const value = metrics?.[item.key]; const isBias = item.key === 'bias_mw'; return <article className={`kpi-card ${isBias ? 'bias-card' : ''}`} key={item.key}><div className="kpi-top"><span className="kpi-label">{item.label}</span><span className="kpi-code">{item.short}</span></div><div className="kpi-value">{isBias && typeof value === 'number' ? <span className={value > 0 ? 'positive' : value < 0 ? 'negative' : ''}>{value > 0 ? '+' : ''}{formatMw(value)}</span> : formatMw(value)}</div><div className="kpi-note">{isBias && typeof biasValue === 'number' ? <><span className={biasValue > 0 ? 'positive' : biasValue < 0 ? 'negative' : ''}>{biasValue > 0 ? 'Over-forecasting' : biasValue < 0 ? 'Under-forecasting' : 'No average bias'}</span><span className="note-dot"> · </span>{item.note}</> : item.note}</div><span className="kpi-accent"/></article> })}</div></section>
        {forecasts.length === 0 ? <section className="state-panel empty-panel"><div className="state-icon">↗</div><div><h2>No forecast data for this range</h2><p>Try another date within January 2026.</p></div></section> : <>
          <section className="chart-card main-chart-card"><div className="chart-header"><div><div className="section-kicker">HOURLY GENERATION</div><h2>Actual vs forecast</h2><p>Hourly wind generation output across the selected period.</p></div><div className="chart-legend"><span><i className="legend-dot actual-dot"/>Actual</span><span><i className="legend-dot forecast-dot"/>Forecast</span></div></div><div className="chart-area"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 14, right: 12, bottom: 0, left: 0 }}><CartesianGrid stroke="#edf0ee" vertical={false}/><XAxis dataKey="label" tick={{ fill: '#89928d', fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={48}/><YAxis tick={{ fill: '#89928d', fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(value: number) => `${Math.round(value / 1000)}k`} width={44}/><Tooltip content={<ForecastTooltip/>}/><Line type="monotone" dataKey="actual_mw" name="Actual" stroke="#197a55" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: '#197a55', stroke: '#fff', strokeWidth: 2 }} connectNulls/><Line type="monotone" dataKey="forecast_mw" name="Forecast" stroke="#9bc8b1" strokeWidth={2} strokeDasharray="5 4" dot={false} activeDot={{ r: 4, fill: '#9bc8b1', stroke: '#fff', strokeWidth: 2 }} connectNulls/></LineChart></ResponsiveContainer></div><div className="chart-footnote"><span>All times UTC</span><span>Values shown in MW</span></div></section>
          <section className="chart-card error-chart-card"><div className="chart-header"><div><div className="section-kicker">DEVIATION FROM ACTUAL</div><h2>Forecast error</h2><p>Positive values indicate over-forecasting; negative values indicate under-forecasting.</p></div><span className="unit-pill">MW</span></div><div className="error-chart-area"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 16, right: 12, bottom: 0, left: 0 }}><CartesianGrid stroke="#edf0ee" vertical={false}/><XAxis dataKey="label" tick={{ fill: '#89928d', fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={48}/><YAxis tick={{ fill: '#89928d', fontSize: 11 }} tickLine={false} axisLine={false} width={54}/><ReferenceLine y={0} stroke="#aab2ad" strokeDasharray="3 3"/><Tooltip content={<ForecastTooltip/>}/><Line type="monotone" dataKey="error_mw" name="Error" stroke="#527e68" strokeWidth={1.7} dot={false} activeDot={{ r: 4, fill: '#527e68', stroke: '#fff', strokeWidth: 2 }} connectNulls/></LineChart></ResponsiveContainer></div></section>
        </>}
      </>}
      <footer className="page-footer"><span>Wind generation forecast evaluation · Historical data</span><span>Great Britain <i/> {startDate} – {endDate}</span></footer>
    </main>
  </div>
}

function ForecastTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload?: ChartPoint }> }) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null
  return <div className="chart-tooltip"><span className="tooltip-label">{fullTimestamp(point.hour)} UTC</span><div className="tooltip-row"><i className="actual-dot"/><span>Actual</span><b>{formatMw(point.actual_mw)}</b></div><div className="tooltip-row"><i className="forecast-dot"/><span>Forecast</span><b>{formatMw(point.forecast_mw)}</b></div><div className="tooltip-row tooltip-error"><i/><span>Forecast error</span><b className={point.error_mw > 0 ? 'positive' : point.error_mw < 0 ? 'negative' : ''}>{point.error_mw > 0 ? '+' : ''}{formatMw(point.error_mw)}</b></div></div>
}

export default App
