import { Link } from "react-router-dom";

export default function ResultsPageHeader({ subtitle, period, onPeriodChange, alternative, onAlternativeChange }) {
  return (
    <>
      <Link className="results-back-link" to="/results">← Change simulation</Link>
      <div className="results-heading">
        <div className="results-title-block">
          <h1>Example community</h1>  {/*input nom sim */}
          {subtitle && <p>{subtitle}</p>}
        </div>
        <div className="results-actions">
          <select id="results-alternative" value={alternative} onChange={event => onAlternativeChange(event.target.value)}>
            <option>Current installation</option> {/*input alternatives */}
          </select>
          <div className="segmented-control" role="group" aria-label="Display period">
            {["Annual", "Monthly"].map(option => (
              <button key={option} type="button" className={period === option ? "active" : ""} onClick={() => onPeriodChange(option)}>
                {option}
              </button>
            ))}
          </div> {/* descarregar excel del back */}
          <button type="button" className="download-button" onClick={() => window.print()}>Download</button>
        </div>
      </div>
    </>
  );
}
