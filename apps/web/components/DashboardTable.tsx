type DashboardTableProps = {
  columns: string[];
  rows: Array<Array<string | number | null | undefined>>;
};

export function DashboardTable({ columns, rows }: DashboardTableProps) {
  if (rows.length === 0) {
    return <p className="emptyResultText">No records available yet.</p>;
  }

  return (
    <div className="dashboardTableWrap">
      <table className="dashboardTable">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`}>{cell ?? "Not available"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
