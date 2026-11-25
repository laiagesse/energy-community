import { useMemo, useState } from "react";
import { formatKpiValue } from "../utils/formatKpi";

function comparable(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  if (Number.isFinite(numeric)) return numeric;
  return String(value).toLocaleLowerCase();
}

export default function KpiTable({
  columns,
  rows,
  label,
  selectedKpis = [],
  onKpiToggle,
  onProsumerClick,
  period
}) {
  const [sort, setSort] = useState({ key: null, direction: "asc" });

  const sortedRows = useMemo(() => {
    if (!sort.key) return rows;

    return [...rows].sort((a, b) => {
      const av = comparable(a[sort.key]);
      const bv = comparable(b[sort.key]);
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;

      const result = typeof av === "number" && typeof bv === "number"
        ? av - bv
        : String(av).localeCompare(String(bv), undefined, { numeric: true });

      return sort.direction === "asc" ? result : -result;
    });
  }, [rows, sort]);

  const setColumnSort = (key, direction) => setSort({ key, direction });

  return (
    <div className="kpi-table-scroll">
      <table className="kpi-table" aria-label={label}>
        <thead>
          <tr>
            {columns.map((column) => {
              const isProsumerColumn = column.key === "prosumer";
              const isAscending = sort.key === column.key && sort.direction === "asc";
              const isDescending = sort.key === column.key && sort.direction === "desc";
              const isChartSelected = selectedKpis.includes(column.key);

              return (
                <th
                  key={column.key}
                  aria-sort={sort.key === column.key
                    ? (isAscending ? "ascending" : "descending")
                    : "none"}
                >
                  <div className="table-sort-heading kpi-table-heading">
                    <span>{column.label}</span>

                    <span className="table-sort-triangles" aria-label={`Sort ${column.label}`}>
                      <button
                        type="button"
                        className={`table-sort-triangle${isAscending ? " is-active" : ""}`}
                        aria-label="Sort from lowest to highest"
                        title="Sort from lowest to highest"
                        aria-pressed={isAscending}
                        onClick={() => setColumnSort(column.key, "asc")}
                      >
                        ▲
                      </button>
                      <button
                        type="button"
                        className={`table-sort-triangle${isDescending ? " is-active" : ""}`}
                        aria-label="Sort from highest to lowest"
                        title="Sort from highest to lowest"
                        aria-pressed={isDescending}
                        onClick={() => setColumnSort(column.key, "desc")}
                      >
                        ▼
                      </button>
                    </span>

                    {!isProsumerColumn && (
                      <button
                        type="button"
                        className={`kpi-chart-toggle${isChartSelected ? " is-selected" : ""}`}
                        aria-label={`${isChartSelected ? "Remove" : "Compare"} ${column.label} in chart`}
                        aria-pressed={isChartSelected}
                        title="Compare this indicator in a chart"
                        onClick={() => onKpiToggle?.(column.key)}
                      >
                        <svg viewBox="0 0 18 18" aria-hidden="true">
                          <path d="M2.5 15.5h13M4 13V8.5M8 13V3.5M12 13V6M16 13V1.8" />
                        </svg>
                      </button>
                    )}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row) => (
            <tr key={row.prosumer}>
              {columns.map((column, index) => (
                <td key={column.key} className={index === 0 ? "prosumer-name-cell" : ""}>
                  {index === 0
                    ? onProsumerClick
                      ? (
                        <button
                          type="button"
                          className="prosumer-name-button"
                          onClick={() => onProsumerClick(row.prosumer)}
                          title={`Open ${row.prosumer} details`}
                        >
                          {row[column.key]}
                        </button>
                      )
                      : row[column.key]
                    : formatKpiValue(row[column.key], column.key, period)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
