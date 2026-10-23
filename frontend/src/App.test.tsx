import { cloneElement, createContext, createElement, isValidElement, useContext } from 'react'
import type { ReactElement, ReactNode } from 'react'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

type ForecastRow = {
  hour: string
  actual_mw: number
  forecast_mw: number
  forecast_publish_time: string
  cutoff_time: string
}
type ChartPoint = ForecastRow & { error_mw: number; label: string }

vi.mock('recharts', async () => {
  const ChartDataContext = createContext<ChartPoint[]>([])

  function ResponsiveContainer({ children }: { children: ReactNode }) {
    return createElement('div', { 'data-testid': 'responsive-chart' }, children)
  }
  function LineChart({ data, children }: { data: ChartPoint[]; children: ReactNode }) {
    return createElement(
      ChartDataContext.Provider,
      { value: data },
      createElement('div', { 'data-testid': 'chart-data', 'data-points': JSON.stringify(data) }, children),
    )
  }
  function Tooltip({ content }: { content: ReactNode }) {
    const data = useContext(ChartDataContext)
    if (!data.length || !isValidElement(content)) return null
    const tooltip = cloneElement(
      content as ReactElement<{ active?: boolean; payload?: Array<{ payload: ChartPoint }> }>,
      { active: true, payload: [{ payload: data[0] }] },
    )
    return createElement('div', { 'data-testid': 'tooltip-preview' }, tooltip)
  }
  function Line({ dataKey }: { dataKey: string }) {
    return createElement('i', { 'data-testid': `series-${dataKey}` })
  }
  function EmptyChartPart() { return null }

  return {
    CartesianGrid: EmptyChartPart,
    Line,
    LineChart,
    ReferenceLine: EmptyChartPart,
    ResponsiveContainer,
    Tooltip,
    XAxis: EmptyChartPart,
    YAxis: EmptyChartPart,
  }
})

const records: ForecastRow[] = [
  { hour: '2026-01-01T00:00:00Z', actual_mw: 12345, forecast_mw: 13345, forecast_publish_time: '2025-12-31T07:30:00Z', cutoff_time: '2025-12-31T09:00:00Z' },
  { hour: '2026-01-01T01:00:00Z', actual_mw: 10000, forecast_mw: 8000, forecast_publish_time: '2025-12-31T07:30:00Z', cutoff_time: '2025-12-31T09:00:00Z' },
  { hour: '2026-01-02T00:00:00Z', actual_mw: 5000, forecast_mw: 6500, forecast_publish_time: '2026-01-01T07:30:00Z', cutoff_time: '2026-01-01T09:00:00Z' },
  { hour: '2026-01-02T23:00:00Z', actual_mw: 8000, forecast_mw: 7000, forecast_publish_time: '2026-01-01T07:30:00Z', cutoff_time: '2026-01-01T09:00:00Z' },
]

type FakeResponse = { ok: boolean; status: number; json: () => Promise<unknown> }
function response(body: unknown, status = 200): FakeResponse {
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}

function getMetrics(rows: ForecastRow[]) {
  if (!rows.length) return null
  const errors = rows.map((row) => row.forecast_mw - row.actual_mw)
  const absolute = errors.map(Math.abs).sort((a, b) => a - b)
  const quantile = (q: number) => {
    const index = (absolute.length - 1) * q
    const lower = Math.floor(index)
    const fraction = index - lower
    return absolute[lower] + (absolute[Math.min(lower + 1, absolute.length - 1)] - absolute[lower]) * fraction
  }
  return {
    intervals_evaluated: rows.length,
    mae_mw: Number((absolute.reduce((sum, value) => sum + value, 0) / rows.length).toFixed(2)),
    rmse_mw: Number(Math.sqrt(errors.reduce((sum, value) => sum + value ** 2, 0) / rows.length).toFixed(2)),
    bias_mw: Number((errors.reduce((sum, value) => sum + value, 0) / rows.length).toFixed(2)),
    median_absolute_error_mw: Number((absolute.length % 2 ? absolute[Math.floor(absolute.length / 2)] : (absolute[absolute.length / 2 - 1] + absolute[absolute.length / 2]) / 2).toFixed(2)),
    p90_absolute_error_mw: Number(quantile(0.9).toFixed(2)),
    p95_absolute_error_mw: Number(quantile(0.95).toFixed(2)),
  }
}

function createApiMock(options: { healthStatus?: string; failMetrics?: boolean } = {}) {
  const requests: string[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    requests.push(`${url.pathname}${url.search}`)
    if (url.pathname === '/health') return response({ status: options.healthStatus ?? 'ok', service: 'wind-forecast-api' })

    const startDate = url.searchParams.get('start_date')
    const endDate = url.searchParams.get('end_date')
    const selected = records.filter((row) => {
      const hour = row.hour.slice(0, 10)
      return (!startDate || hour >= startDate) && (!endDate || hour <= endDate)
    })

    if (url.pathname === '/api/metrics') {
      if (options.failMetrics) return response({ detail: 'Metrics service unavailable' }, 503)
      const metrics = getMetrics(selected)
      return metrics ? response(metrics) : response({ detail: 'No forecast and actual data found for the selected dates.' }, 404)
    }
    return response({ count: selected.length, data: selected })
  })
  vi.stubGlobal('fetch', fetchMock)
  return { fetchMock, requests }
}

describe('WindInsights dashboard API behavior', () => {
  it('shows the loading state while the API requests begin', async () => {
    createApiMock()
    render(<App />)

    expect(screen.getByRole('status')).toHaveTextContent('Connecting to API')
    expect(screen.getByLabelText('Loading dashboard')).toBeInTheDocument()
    expect(await screen.findByText('API connected')).toBeInTheDocument()
  })

  it('renders KPI values returned from the metrics API', async () => {
    createApiMock()
    render(<App />)

    const metrics = await screen.findByRole('region', { name: 'Accuracy metrics' })
    expect(within(metrics).getByText('1,375 MW')).toBeInTheDocument()
    expect(within(metrics).getByText('1,436 MW')).toBeInTheDocument()
    expect(within(metrics).getByText('-125 MW')).toBeInTheDocument()
    expect(within(metrics).getByText('1,250 MW')).toBeInTheDocument()
    expect(within(metrics).getByText('1,850 MW')).toBeInTheDocument()
    expect(within(metrics).getByText('1,925 MW')).toBeInTheDocument()
  })

  it('passes API forecast values into both charts and derives forecast error', async () => {
    createApiMock()
    render(<App />)

    await screen.findByText('API connected')
    const charts = screen.getAllByTestId('chart-data')
    expect(charts).toHaveLength(2)
    for (const chart of charts) {
      const chartPoints = JSON.parse(chart.getAttribute('data-points') ?? '[]') as ChartPoint[]
      expect(chartPoints[0]).toMatchObject({
        hour: '2026-01-01T00:00:00Z',
        actual_mw: 12345,
        forecast_mw: 13345,
        error_mw: 1000,
      })
    }
    expect(screen.getByTestId('series-actual_mw')).toBeInTheDocument()
    expect(screen.getByTestId('series-forecast_mw')).toBeInTheDocument()
    expect(screen.getByTestId('series-error_mw')).toBeInTheDocument()
  })

  it('reloads metrics and both charts when the start date changes', async () => {
    const { requests } = createApiMock()
    render(<App />)
    await screen.findByText('API connected')

    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-01-02' } })

    await waitFor(() => expect(screen.getByText('2 hourly intervals')).toBeInTheDocument())
    expect(requests.some((url) => url.startsWith('/api/metrics?') && url.includes('start_date=2026-01-02'))).toBe(true)
    expect(requests.some((url) => url.startsWith('/api/forecasts?') && url.includes('start_date=2026-01-02'))).toBe(true)
    const charts = screen.getAllByTestId('chart-data')
    expect(charts).toHaveLength(2)
    for (const chart of charts) {
      const chartPoints = JSON.parse(chart.getAttribute('data-points') ?? '[]') as ChartPoint[]
      expect(chartPoints).toHaveLength(2)
      expect(chartPoints.every((point) => point.hour.startsWith('2026-01-02'))).toBe(true)
    }
    const metrics = screen.getByRole('region', { name: 'Accuracy metrics' })
    expect(within(metrics).getAllByText('1,250 MW')).toHaveLength(2)
    expect(within(metrics).getByText('+250 MW')).toBeInTheDocument()
  })

  it('renders API failure state and marks API unavailable', async () => {
    createApiMock({ failMetrics: true })
    render(<App />)

    expect(await screen.findByText('API unavailable')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Metrics service unavailable')
    expect(screen.getByRole('button', { name: /Try again/ })).toBeInTheDocument()
  })

  it('renders the empty data state for an empty date range', async () => {
    createApiMock()
    render(<App />)
    await screen.findByText('API connected')
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-01-03' } })

    expect(await screen.findByText('No forecast data for this range')).toBeInTheDocument()
    expect(screen.getByText('— hourly intervals')).toBeInTheDocument()
    expect(screen.getByText('API connected')).toBeInTheDocument()
  })

  it('marks the API unavailable when the health payload is not ok', async () => {
    createApiMock({ healthStatus: 'degraded' })
    render(<App />)

    expect(await screen.findByText('API unavailable')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('health check did not return an OK status')
  })

  it('shows UTC timestamps and MW units in chart tooltips', async () => {
    createApiMock()
    render(<App />)

    expect(await screen.findByText('API connected')).toBeInTheDocument()
    expect(screen.getAllByText(/00:00 UTC/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('12,345 MW').length).toBeGreaterThan(0)
    expect(screen.getAllByText('13,345 MW').length).toBeGreaterThan(0)
    expect(screen.getAllByText('+1,000 MW').length).toBeGreaterThan(0)
    expect(screen.getByText('All times UTC')).toBeInTheDocument()
    expect(screen.getByText('Values shown in MW')).toBeInTheDocument()
  })
})
