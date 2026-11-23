import { formatKpiValue } from "../utils/formatKpi";

export default function KpiTable({
  columns,
  rows,
  label,
  selectedKpis = [],
  onKpiToggle,
  onProsumerClick
}) {
  return (
    <div className="kpi-table-scroll">
      <table className="kpi-table" aria-label={label}>
        <thead>
          <tr>
            {columns.map(column => (
              <th key={column.key}>
                {column.key === "prosumer" ? column.label : (
                  <span className="kpi-table-heading">
                    <span>{column.label}</span>
                    <button
                      type="button"
                      className={`kpi-chart-toggle ${selectedKpis.includes(column.key) ? "is-selected" : ""}`}
                      aria-label={`${selectedKpis.includes(column.key) ? "Remove" : "Compare"} ${column.label} in chart`}
                      aria-pressed={selectedKpis.includes(column.key)}
                      title="Compare this indicator in a chart"
                      onClick={() => onKpiToggle?.(column.key)}
                    >
                      <svg viewBox="0 0 18 18" aria-hidden="true">
                        <path d="M2.5 15.5h13M4 13V8.5M8 13V3.5M12 13V6M16 13V1.8" />
                      </svg>
                    </button>
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.prosumer}>
              {columns.map((column, index) => (
                <td key={column.key} className={index === 0 ? "prosumer-name-cell" : ""}>
                  {index === 0 ? (
                    <button
                      type="button"
                      className="prosumer-detail-link"
                      onClick={() => onProsumerClick?.(row.prosumer)}
                      title={`Open ${row.prosumer} details`}
                    >
                      {row[column.key]}
                      <span aria-hidden="true">↗</span>
                    </button>
                  ) : formatKpiValue(row[column.key], column.key)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
