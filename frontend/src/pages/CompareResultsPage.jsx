import { useState, useMemo } from "react";
import ResultsPageHeader from "../components/ResultsPageHeader";
import ResultsTabs from "../components/ResultsTabs";
import {
  initialScenarios,
  defaultSelectedIndicators,
  scenarioOptions,
  dimensions
} from "../data/comparisonResults";

function bestScenarioIndex(indicator, scenarios) {
  const values = scenarios.map((scenario, index) => {
    const sourceIndex = scenarioOptions.findIndex(option => option.code === scenario.code);
    const raw = indicator.values[sourceIndex];
    return raw == null ? null : { value: Number(String(raw).replace(",", ".")), index };
  }).filter(Boolean);

  if (!values.length || indicator.direction === "none") return -1;
  if (indicator.direction === "higher") return values.reduce((best, item) => item.value > best.value ? item : best).index;
  if (indicator.direction === "lower") return values.reduce((best, item) => item.value < best.value ? item : best).index;
  if (indicator.direction === "closestOne") return values.reduce((best, item) => Math.abs(item.value - 1) < Math.abs(best.value - 1) ? item : best).index;
  return -1;
}

export default function CompareResultsPage() {
  const [period, setPeriod] = useState("Annual");
  const [alternative, setAlternative] = useState("Current installation");
  const [scenarios, setScenarios] = useState(initialScenarios);
  const [selected, setSelected] = useState(defaultSelectedIndicators);
  const [applied, setApplied] = useState(defaultSelectedIndicators);
  const allIndicators = useMemo(() => dimensions.flatMap(dimension => dimension.indicators), []);
  const selectedDimensions = dimensions.filter(d => d.indicators.some(i => selected.includes(i.id))).map(d => d.id);

  const toggleIndicator = id => setSelected(current => current.includes(id) ? current.filter(x => x !== id) : [...current, id]);
  const toggleDimension = dimension => {
    const ids = dimension.indicators.map(item => item.id);
    const allSelected = ids.every(id => selected.includes(id));
    setSelected(current => allSelected ? current.filter(id => !ids.includes(id)) : [...new Set([...current, ...ids])]);
  };
  const toggleAll = dimension => {
    const ids = dimension.indicators.map(item => item.id);
    const allSelected = ids.every(id => selected.includes(id));
    setSelected(current => allSelected ? current.filter(id => !ids.includes(id)) : [...new Set([...current, ...ids])]);
  };
  const changeScenario = (id, code) => setScenarios(current => current.map(s => {
    if (s.id !== id) return s;
    const option = scenarioOptions.find(item => item.code === code);
    return option ? { ...s, label: option.label, code: option.code } : s;
  }));
  const removeScenario = id => setScenarios(current => current.length > 2 ? current.filter(s => s.id !== id) : current);
  const addScenario = () => {
    if (scenarios.length >= 3) return;
    const available = scenarioOptions.find(option => !scenarios.some(s => s.code === option.code));
    if (!available) return;
    const letter = ["A", "B", "C"].find(x => !scenarios.some(s => s.label.endsWith(x)));
    setScenarios(current => [...current, { id: `scenario-${letter}`, label: available.label, code: available.code, color: "#8b744b", marker: "◆" }]);
  };
  const selectedRows = allIndicators.filter(indicator => applied.includes(indicator.id));

  return (
    <main className="page-width results-page compare-page">
      <ResultsPageHeader
        subtitle="Compare different energy community configurations and identify which one best matches your priorities."
        period={period}
        onPeriodChange={setPeriod}
        alternative={alternative}
        onAlternativeChange={setAlternative}
      />
      <ResultsTabs active="compare" />

      <section className="compare-section scenario-section">
        <h2>Scenarios to compare</h2>
        <div className="scenario-grid">
          {scenarios.map((scenario, index) => (
            <article className="scenario-card" key={scenario.id}>
              <div className="scenario-card-top">
                <span className="scenario-name"><i style={{ color: scenario.color }}>{scenario.marker}</i>{scenario.label}</span>
                <button type="button" className="icon-button" aria-label={`Remove ${scenario.label}`} onClick={() => removeScenario(scenario.id)} disabled={scenarios.length <= 2}>♧</button>
              </div>
              <strong>{scenario.label}</strong>
              <label className="sr-only" htmlFor={`${scenario.id}-select`}>Choose scenario</label>
              <select id={`${scenario.id}-select`} value={scenario.code} onChange={event => changeScenario(scenario.id, event.target.value)}>
                {scenarioOptions.map(option => <option key={option.code} value={option.code}>{`Change ${option.label}`}</option>)}
              </select>
            </article>
          ))}
        </div>
        <button type="button" className="add-scenario-button" onClick={addScenario} disabled={scenarios.length >= 3}>＋ Add scenario</button>
      </section>

      <section className="compare-section indicator-section">
        <div className="compare-section-title">
          <h2>Customize indicators</h2>
          <p>Select the dimensions and indicators you want to compare.</p>
        </div>
        <div className="dimension-chips">
          {dimensions.map(dimension => (
            <button key={dimension.id} type="button" className={selectedDimensions.includes(dimension.id) ? "selected" : ""} style={{ "--dimension-color": dimension.color }} onClick={() => toggleDimension(dimension)}>
              {selectedDimensions.includes(dimension.id) ? "✓" : "+"} {dimension.label}
            </button>
          ))}
        </div>

        <div className="indicator-catalog">
          <div className="catalog-heading">
            <strong>☷ Full indicator catalogue</strong>
            <span>⌃</span>
          </div>
          <div className="catalog-actions">
            <button type="button" onClick={() => setSelected(allIndicators.map(item => item.id))}>Select all</button>
            <button type="button" onClick={() => setSelected([])}>Deselect all</button>
          </div>
          <div className="indicator-groups">
            {dimensions.map(dimension => (
              <section className="indicator-group" key={dimension.id}>
                <button type="button" className="indicator-group-title" onClick={() => toggleAll(dimension)} style={{ color: dimension.color }}>
                  <span>{dimension.icon}</span>{dimension.label}<span className="chevron">⌃</span>
                </button>
                {dimension.indicators.map(indicator => (
                  <label className="indicator-option" key={indicator.id}>
                    <input type="checkbox" checked={selected.includes(indicator.id)} onChange={() => toggleIndicator(indicator.id)} />
                    <span>{indicator.label}</span>
                  </label>
                ))}
              </section>
            ))}
          </div>
          <p className="catalog-note">The self-sufficiency gap is a single indicator shared between dimensions. No data: definition and unit are not available.</p>
          <div className="catalog-footer">
            <button type="button" className="text-button" onClick={() => setSelected([])}>Clear filters</button>
            <button type="button" className="apply-button" onClick={() => setApplied(selected)}>✓ Apply filters</button>
          </div>
        </div>
      </section>

      <section className="compare-section comparison-results">
        <div className="comparison-title-row">
          <h2>Indicator comparison</h2>
          <span>{selectedRows.length} KPIs · Sample values</span>
        </div>
        <div className="comparison-table-scroll">
          <table className="comparison-table">
            <thead>
              <tr>
                <th className="indicator-column">Indicator and unit<small>Fixed column · Favourable direction indicated</small></th>
                {scenarios.map(scenario => (
                  <th key={scenario.id}>
                    <span className="scenario-table-name"><i style={{ color: scenario.color }}>{scenario.marker}</i>{scenario.label}</span>
                    <small>{scenario.code}</small>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {selectedRows.map(indicator => {
                const best = bestScenarioIndex(indicator, scenarios);
                return (
                  <tr key={indicator.id}>
                    <td className="indicator-column">
                      <strong style={{ borderColor: dimensions.find(d => d.indicators.some(i => i.id === indicator.id))?.color }}>{indicator.label}</strong>
                      <small>{indicator.direction === "higher" ? "↑ Higher is better" : indicator.direction === "lower" ? "↓ Lower is better" : indicator.direction === "closestOne" ? "→ Closer to 1 is better" : "Direction not defined"}</small>
                    </td>
                    {scenarios.map((scenario, index) => {
                      const sourceIndex = scenarioOptions.findIndex(option => option.code === scenario.code);
                      const value = indicator.values[sourceIndex] ?? null;
                      return <td key={scenario.id}><span className={best === index && value !== null ? "best-value" : ""}>{value ?? "No data"}</span></td>;
                    })}
                  </tr>
                );
              })}
              {!selectedRows.length && <tr><td colSpan={scenarios.length + 1} className="empty-table">Select indicators and apply the filters.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
