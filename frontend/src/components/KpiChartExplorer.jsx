import { getKpiMeta } from "../utils/prosumerKpiMeta";

export default function KpiChartExplorer({ columns, rows, selectedKpis = [], onKpiToggle }) {
  if (!selectedKpis.length) return null;

  const selectedColumns = columns.filter(column => selectedKpis.includes(column.key));
  const values = rows.flatMap(row => selectedColumns
    .map(column => Number(row[column.key]) * getKpiMeta(column.key).scale)
    .filter(Number.isFinite));
  const maxValue = Math.max(0, ...values.map(value => Math.abs(value))) || 1;
  const unit = getKpiMeta(selectedColumns[0]?.key).unit;

  const displayValue = (value, key) => {
    if (value == null || !Number.isFinite(Number(value))) return "—";
    const meta = getKpiMeta(key);
    const scaled = Number(value) * meta.scale;
    return `${scaled.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${meta.unit}`;
  };

  return (
    <section className="kpi-chart-explorer" aria-label="KPI comparison chart">
      <div className="kpi-chart-explorer-heading">
        <div>
          <span className="kpi-chart-eyebrow">COMPARISON</span>
          <h3>Compare prosumers</h3>
          <p>Selected indicators · {unit}</p>
        </div>
        <button type="button" className="kpi-chart-close" onClick={() => selectedKpis.forEach(onKpiToggle)}>
          Clear selection
        </button>
      </div>

      <div className="kpi-chart-legend">
        {selectedColumns.map((column, index) => (
          <span key={column.key}>
            <i className={`kpi-chart-color kpi-chart-color-${index % 4}`} />
            {column.label}
            <button type="button" onClick={() => onKpiToggle(column.key)} aria-label={`Remove ${column.label}`}>×</button>
          </span>
        ))}
      </div>

      <div className="kpi-chart-rows">
        {rows.map(row => (
          <div className="kpi-chart-row" key={row.prosumer}>
            <strong className="kpi-chart-prosumer">{row.prosumer}</strong>
            <div className="kpi-chart-bars">
              {selectedColumns.map((column, index) => {
                const raw = row[column.key];
                const value = raw == null ? null : Number(raw) * getKpiMeta(column.key).scale;
                const width = value == null || !Number.isFinite(value)
                  ? 0
                  : Math.max(0, Math.min(100, Math.abs(value) / maxValue * 100));
                return (
                  <div className="kpi-chart-bar-line" key={column.key}>
                    <span className={`kpi-chart-bar kpi-chart-color-${index % 4}`} style={{ width: `${width}%` }} />
                    <span className="kpi-chart-value">{displayValue(raw, column.key)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
