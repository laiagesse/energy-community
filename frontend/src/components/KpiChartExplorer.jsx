import { getKpiMeta } from "../utils/prosumerKpiMeta";

const COVERAGE_KEYS = ["selfSufficiency", "gridDependency"];
const DIVERGING_KEYS = ["netP2p", "sharedEnergy"];

const COVERAGE_SEGMENTS = [
  { key: "own", label: "Own resources", color: "#3e7b48" },
  { key: "grid", label: "Grid", color: "#b65d4a" },
  { key: "p2p", label: "P2P exchange", color: "#3d5e80" }
];

const numberOrNull = value => {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

function getCoverage(row) {
  const own = numberOrNull(row.selfSufficiency);
  const grid = numberOrNull(row.gridDependency);
  if (own === null || grid === null) return null;

  const ownPercent = Math.max(0, own * 100);
  const gridPercent = Math.max(0, grid * 100);
  const p2pPercent = Math.max(0, 100 - ownPercent - gridPercent);
  const total = ownPercent + gridPercent + p2pPercent;
  if (!total) return null;

  // Keep the displayed stack at exactly 100%, including small rounding errors.
  return {
    own: ownPercent / total * 100,
    grid: gridPercent / total * 100,
    p2p: p2pPercent / total * 100
  };
}

function formatValue(value, key) {
  if (value === null) return "—";
  const meta = getKpiMeta(key);
  const scaled = value * meta.scale;
  return `${scaled.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${meta.unit}`;
}

function CoverageChart({ rows }) {
  return (
    <div className="kpi-chart-rows kpi-coverage-rows">
      <div className="kpi-coverage-axis"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
      {rows.map(row => {
        const coverage = getCoverage(row);
        return (
          <div className="kpi-chart-row kpi-coverage-row" key={row.prosumer}>
            <strong className="kpi-chart-prosumer">{row.prosumer}</strong>
            {coverage ? (
              <div className="kpi-coverage-track" role="img" aria-label={`${row.prosumer}: Own resources ${coverage.own.toFixed(1)}%, Grid ${coverage.grid.toFixed(1)}%, P2P exchange ${coverage.p2p.toFixed(1)}%`}>
                {COVERAGE_SEGMENTS.map(segment => (
                  <span
                    key={segment.key}
                    className="kpi-coverage-segment"
                    style={{ width: `${coverage[segment.key]}%`, backgroundColor: segment.color }}
                    title={`${segment.label}: ${coverage[segment.key].toFixed(1)}%`}
                  />
                ))}
              </div>
            ) : <span className="kpi-chart-value">No data</span>}
          </div>
        );
      })}
    </div>
  );
}

function DivergingChart({ rows, column }) {
  const values = rows.map(row => numberOrNull(row[column.key])).filter(value => value !== null);
  const maxAbs = Math.max(0, ...values.map(value => Math.abs(value))) || 1;

  return (
    <div className="kpi-chart-rows kpi-diverging-rows">
      {rows.map(row => {
        const raw = numberOrNull(row[column.key]);
        const scaled = raw === null ? null : raw * getKpiMeta(column.key).scale;
        const width = scaled === null ? 0 : Math.abs(scaled) / maxAbs * 50;
        return (
          <div className="kpi-chart-row kpi-diverging-row" key={row.prosumer}>
            <strong className="kpi-chart-prosumer">{row.prosumer}</strong>
            <div className="kpi-diverging-plot">
              <div className="kpi-diverging-track">
                <span className="kpi-diverging-bar negative" style={scaled !== null && scaled < 0 ? { width: `${width}%` } : undefined} />
                <span className="kpi-diverging-zero" />
                <span className="kpi-diverging-bar positive" style={scaled !== null && scaled > 0 ? { width: `${width}%` } : undefined} />
              </div>
              <span className="kpi-chart-value">{formatValue(raw, column.key)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ProgressChart({ rows, column }) {
  return (
    <div className="kpi-chart-rows">
      {rows.map(row => {
        const raw = numberOrNull(row[column.key]);
        const scaled = raw === null ? null : raw * getKpiMeta(column.key).scale;
        const width = scaled === null ? 0 : Math.max(0, Math.min(100, scaled));
        return (
          <div className="kpi-chart-row" key={row.prosumer}>
            <strong className="kpi-chart-prosumer">{row.prosumer}</strong>
            <div className="kpi-progress-line">
              <div className="kpi-progress-track">
                <span className="kpi-progress-fill" style={{ width: `${width}%` }} />
              </div>
              <span className="kpi-chart-value">{formatValue(raw, column.key)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StandardChart({ rows, column }) {
  const values = rows.map(row => numberOrNull(row[column.key]) * getKpiMeta(column.key).scale)
    .filter(Number.isFinite);
  const maxValue = Math.max(0, ...values.map(value => Math.abs(value))) || 1;
  return (
    <div className="kpi-chart-rows">
      {rows.map(row => {
        const raw = numberOrNull(row[column.key]);
        const scaled = raw === null ? null : raw * getKpiMeta(column.key).scale;
        const width = scaled === null ? 0 : Math.abs(scaled) / maxValue * 100;
        return (
          <div className="kpi-chart-row" key={row.prosumer}>
            <strong className="kpi-chart-prosumer">{row.prosumer}</strong>
            <div className="kpi-progress-line">
              <div className="kpi-progress-track"><span className="kpi-progress-fill" style={{ width: `${width}%` }} /></div>
              <span className="kpi-chart-value">{formatValue(raw, column.key)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function KpiChartExplorer({ columns, rows, selectedKpis = [], onKpiToggle, period }) {
  if (!selectedKpis.length) return null;

  const selectedColumns = columns.filter(column => selectedKpis.includes(column.key));
  const coverageSelected = selectedKpis.some(key => COVERAGE_KEYS.includes(key));
  const chartColumns = selectedColumns.filter(column => !COVERAGE_KEYS.includes(column.key));
  return (
    <section className="kpi-chart-explorer" aria-label="KPI comparison chart">
      {coverageSelected && (
        <>
          <div className="kpi-chart-legend kpi-coverage-legend">
            {COVERAGE_SEGMENTS.map(segment => (
              <span key={segment.key}><i className="kpi-chart-color" style={{ backgroundColor: segment.color }} />{segment.label}</span>
            ))}
          </div>
          <CoverageChart rows={rows} />
        </>
      )}

      {chartColumns.map(column => {
        const meta = getKpiMeta(column.key);
        return (
          <section className="kpi-indicator-chart" key={column.key}>
            <div className="kpi-indicator-chart-heading">
              <strong>{column.label}</strong>
              <span>{period === "annual" && (column.key === "finalBill" || column.key === "saved") ? "€" : meta.unit}</span>
              <button type="button" onClick={() => onKpiToggle(column.key)} aria-label={`Remove ${column.label}`}>×</button>
            </div>
            {DIVERGING_KEYS.includes(column.key)
              ? <DivergingChart rows={rows} column={column} />
              : meta.unit === "%"
                ? <ProgressChart rows={rows} column={column} />
                : <StandardChart rows={rows} column={column} />}
          </section>
        );
      })}
    </section>
  );
}
