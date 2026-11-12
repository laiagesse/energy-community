export default function KpiTable({ columns, rows, label }) {
  return (
    <div className="kpi-table-scroll">
      <table className="kpi-table" aria-label={label}>
        <thead>
          <tr>{columns.map(column => <th key={column.key}>{column.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map(row => (
            <tr key={row.prosumer}>
              {columns.map((column, index) => (
                <td key={column.key} className={index === 0 ? "prosumer-name-cell" : ""}>{row[column.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
