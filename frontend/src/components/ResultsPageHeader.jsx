import { Link, useLocation } from "react-router-dom";

export default function ResultsPageHeader({
  subtitle,
  simulationId,
  experiments = [],
  loadingExperiments = false,
  period,
  onPeriodChange,
  alternative,
  onAlternativeChange,
  periods = [],
}) {
  const location = useLocation();
  const simulationQuery = simulationId
    ? `?simulation=${encodeURIComponent(simulationId)}`
    : location.search;

  return (
    <>
      <Link className="results-back-link" to="/results">
        ← Change simulation
      </Link>

      <div className="results-heading">
        <div className="results-title-block">
          <h1>{simulationId}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>

        <div className="results-actions">
          {experiments.length > 0 && (
            <select
              id="results-alternative"
              value={alternative ?? ""}
              onChange={event => onAlternativeChange?.(event.target.value)}
              disabled={loadingExperiments}
            >
              {experiments.map(experiment => (
                <option key={experiment.id} value={experiment.id}>
                  {experiment.name}
                </option>
              ))}
            </select>
          )}

          <div className="segmented-control" role="group">
            {periods.map(item => (
              <button
                key={item.id}
                type="button"
                className={period === item.id ? "active" : ""}
                onClick={() => onPeriodChange(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            className="download-button"
            onClick={() => window.print()}
          >
            Download
          </button>
        </div>
      </div>
    </>
  );
}
