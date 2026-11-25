import { getKpiMeta } from "../utils/prosumerKpiMeta";

const COVERAGE_KEYS = ["selfSufficiency", "gridDependency"];
const DIVERGING_KEYS = ["netP2p", "sharedEnergy"];
const PAYBACK_KEYS = new Set(["payback", "paybackPv", "paybackWt", "paybackBattery"]);

const COVERAGE_SEGMENTS = [
  { key: "own", label: "Self-Sufficiency", color: "#3e7b48" },
  { key: "grid", label: "Grid Dependency", color: "#b65d4a" },
  { key: "p2p", label: "P2P Exchange", color: "#3d5e80" }
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

function getKpiUnit(key, period) {
  return period === "annual" && PAYBACK_KEYS.has(key)
    ? "years"
    : getKpiMeta(key).unit;
}

function formatValue(value, key, period) {
  if (value === null) return "—";
  const meta = getKpiMeta(key);
  const scaled = value * meta.scale;
  return `${scaled.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${getKpiUnit(key, period)}`;
}

function sortRowsByValuesDescending(rows, keys) {
  return [...rows].sort((a, b) => {
    for (const key of keys) {
      const aValue = numberOrNull(a[key]);
      const bValue = numberOrNull(b[key]);
      if (aValue === null && bValue === null) continue;
      if (aValue === null) return 1;
      if (bValue === null) return -1;
      if (aValue !== bValue) return bValue - aValue;
    }
    return 0;
  });
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
              <div className="kpi-coverage-track" role="img" aria-label={`${row.prosumer}: Self-Sufficiency ${coverage.own.toFixed(1)}%, Grid Dependency ${coverage.grid.toFixed(1)}%, P2P Exchange ${coverage.p2p.toFixed(1)}%`}>
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

function DivergingChart({ rows, column, period }) {
  const values = rows.map(row => numberOrNull(row[column.key])).filter(value => value !== null);
  const maxAbs = Math.max(0, ...values.map(value => Math.abs(value))) || 1;
  const targetStep = maxAbs / 2;
  const magnitude = 10 ** Math.floor(Math.log10(targetStep));
  const fraction = targetStep / magnitude;
  const niceFraction = [1, 2, 2.5, 5, 10].find(step => step >= fraction) ?? 10;
  const axisStep = niceFraction * magnitude;
  const axisMax = axisStep * 2;
  const axisFractionDigits = Math.min(
    6,
    Math.max(0, -Math.floor(Math.log10(axisStep)) + (niceFraction === 2.5 ? 1 : 0))
  );
  const axisTicks = [-axisMax, -axisStep, 0, axisStep, axisMax];

  return (
    <div className="kpi-diverging-chart" role="group" aria-label={`${column.label} in kilowatt-hours by prosumer`}>
      <div className="kpi-chart-row kpi-diverging-axis-row" aria-hidden="true">
        <span />
        <div className="kpi-diverging-axis-plot">
          <div className="kpi-diverging-axis-scale">
            {axisTicks.map((tick, index) => (
              <span
                className={index === 0 ? "is-start" : index === axisTicks.length - 1 ? "is-end" : ""}
                key={`${tick}-${index}`}
                style={{ left: `${(tick + axisMax) / (axisMax * 2) * 100}%` }}
              >
                {tick > 0 ? "+" : ""}{tick.toLocaleString(undefined, { maximumFractionDigits: axisFractionDigits })}
              </span>
            ))}
          </div>
          <span className="kpi-diverging-axis-unit">kWh</span>
        </div>
      </div>
      <div className="kpi-chart-rows kpi-diverging-rows">
        <div className="kpi-diverging-grid" aria-hidden="true">
          <div className="kpi-diverging-grid-plot">
            {axisTicks.map((tick, index) => (
              <span
                className={index === 2 ? "is-zero" : ""}
                key={`${tick}-${index}`}
                style={{ left: `${(tick + axisMax) / (axisMax * 2) * 100}%` }}
              />
            ))}
          </div>
        </div>
        {rows.map(row => {
          const raw = numberOrNull(row[column.key]);
          const scaled = raw === null ? null : raw * getKpiMeta(column.key).scale;
          const width = scaled === null ? 0 : Math.min(Math.abs(scaled) / axisMax * 50, 50);
          return (
            <div className="kpi-chart-row kpi-diverging-row" key={row.prosumer}>
              <strong className="kpi-chart-prosumer">{row.prosumer}</strong>
              <div className="kpi-diverging-plot">
                <div className="kpi-diverging-track">
                  <span className="kpi-diverging-bar negative" style={scaled !== null && scaled < 0 ? { width: `${width}%` } : undefined} />
                  <span className="kpi-diverging-bar positive" style={scaled !== null && scaled > 0 ? { width: `${width}%` } : undefined} />
                </div>
                <span className="kpi-chart-value">{formatValue(raw, column.key, period)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ProgressChart({ rows, column, period }) {
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
              <span className="kpi-chart-value">{formatValue(raw, column.key, period)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StandardChart({ rows, column, period }) {
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
              <span className="kpi-chart-value">{formatValue(raw, column.key, period)}</span>
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
  const coverageSortKeys = COVERAGE_KEYS.filter(key => selectedKpis.includes(key));
  const chartColumns = selectedColumns.filter(column => !COVERAGE_KEYS.includes(column.key));
  return (
    <section className="kpi-chart-explorer" aria-label="KPI comparison chart">
      {coverageSelected && (
        <section className="kpi-indicator-chart kpi-coverage-chart">
          <div className="kpi-indicator-chart-heading">
            <strong>Electricity consumption</strong>
            <span>%</span>
          </div>

          <div className="kpi-chart-legend kpi-coverage-legend">
            {COVERAGE_SEGMENTS.map(segment => (
              <span key={segment.key}>
                <i
                  className="kpi-chart-color"
                  style={{ backgroundColor: segment.color }}
                />
                {segment.label}
              </span>
            ))}
          </div>

          <CoverageChart rows={sortRowsByValuesDescending(rows, coverageSortKeys)} />
        </section>
      )}

      {chartColumns.map(column => {
        const meta = getKpiMeta(column.key);
        const chartRows = sortRowsByValuesDescending(rows, [column.key]);
        return (
          <section className="kpi-indicator-chart" key={column.key}>
            <div className="kpi-indicator-chart-heading">
              <strong>{column.label}</strong>
              <span>{period === "annual" && (column.key === "finalBill" || column.key === "saved")
                ? "€"
                : getKpiUnit(column.key, period)}</span>
              <button type="button" onClick={() => onKpiToggle(column.key)} aria-label={`Remove ${column.label}`}>×</button>
            </div>
            {DIVERGING_KEYS.includes(column.key)
              ? <DivergingChart rows={chartRows} column={column} period={period} />
              : meta.unit === "%"
                ? <ProgressChart rows={chartRows} column={column} period={period} />
                : <StandardChart rows={chartRows} column={column} period={period} />}
          </section>
        );
      })}
    </section>
  );
}
