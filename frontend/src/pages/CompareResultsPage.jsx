
import { useState, useMemo, useEffect } from "react";
import ResultsPageHeader from "../components/ResultsPageHeader";
import ResultsTabs from "../components/ResultsTabs";
import {
  initialScenarios,
  defaultSelectedIndicators,
  dimensions
} from "../data/comparisonResults";

const API_URL = "http://127.0.0.1:8000";

const periods = [
  { id: "winter", label: "Winter" },
  { id: "spring", label: "Spring" },
  { id: "summer", label: "Summer" },
  { id: "autumn", label: "Autumn" }
];

// Formata els valors segons la unitat de cada indicador.
function formatKpiValue(value, format) {
  if (value === null || value === undefined || value === "") {
    return "No data";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) return "No data";

  switch (format) {
    case "percentage":
      return `${new Intl.NumberFormat("en-GB", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1
      }).format(number * 100)}%`;

    case "currency":
      return new Intl.NumberFormat("en-GB", {
        style: "currency",
        currency: "EUR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(number);

    case "emissions":
      return `${new Intl.NumberFormat("en-GB", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1
      }).format(number)} kg CO₂ eq`;

    case "years":
      return `${new Intl.NumberFormat("en-GB", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(number)} years`;

    case "index":
      return new Intl.NumberFormat("en-GB", {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3
      }).format(number);

    default:
      return new Intl.NumberFormat("en-GB", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 3
      }).format(number);
  }
}

// Recupera el valor d'una KPI a partir de la clau exacta de l'API.
function getIndicatorValue(indicator, experimentData, period) {
  if (!experimentData?.periods) return null;

  const selectedPeriod = experimentData.periods.find(
    item => item.id.toLowerCase() === period.toLowerCase()
  );

  if (!selectedPeriod?.kpis) return null;

  return selectedPeriod.kpis[indicator.id]?.value ?? null;
}

// Determina quin escenari té el millor resultat.
function bestScenarioIndex(indicator, scenarios, experimentKpis, period) {
  if (indicator.direction === "none") return -1;

  const values = scenarios
    .map((scenario, index) => {
      const raw = getIndicatorValue(
        indicator,
        experimentKpis[scenario.experimentId],
        period
      );

      if (raw === null || raw === undefined) return null;

      const value = Number(raw);

      if (!Number.isFinite(value)) return null;

      return { value, index };
    })
    .filter(Boolean);

  if (!values.length) return -1;

  if (indicator.direction === "higher") {
    return values.reduce(
      (best, item) => item.value > best.value ? item : best
    ).index;
  }

  if (indicator.direction === "lower") {
    return values.reduce(
      (best, item) => item.value < best.value ? item : best
    ).index;
  }

  if (indicator.direction === "closestOne") {
    return values.reduce(
      (best, item) =>
        Math.abs(item.value - 1) < Math.abs(best.value - 1)
          ? item
          : best
    ).index;
  }

  return -1;
}

export default function CompareResultsPage() {
  const [period, setPeriod] = useState("winter");
  const [alternative, setAlternative] = useState("Current installation");

  const [scenarios, setScenarios] = useState(initialScenarios);
  const [experiments, setExperiments] = useState([]);
  const [experimentKpis, setExperimentKpis] = useState({});
  const [loadingKpis, setLoadingKpis] = useState(false);

  const [selected, setSelected] = useState(defaultSelectedIndicators);
  const [applied, setApplied] = useState(defaultSelectedIndicators);

  const allIndicators = useMemo(
    () => dimensions.flatMap(dimension => dimension.indicators),
    []
  );

  const selectedDimensions = dimensions
    .filter(dimension =>
      dimension.indicators.some(indicator => selected.includes(indicator.id))
    )
    .map(dimension => dimension.id);

  const selectedRows = allIndicators.filter(
    indicator => applied.includes(indicator.id)
  );

  const toggleIndicator = id => {
    setSelected(current =>
      current.includes(id)
        ? current.filter(item => item !== id)
        : [...current, id]
    );
  };

  const toggleDimension = dimension => {
    const ids = dimension.indicators.map(item => item.id);
    const allSelected = ids.every(id => selected.includes(id));

    setSelected(current =>
      allSelected
        ? current.filter(id => !ids.includes(id))
        : [...new Set([...current, ...ids])]
    );
  };

  const toggleAll = dimension => {
    toggleDimension(dimension);
  };

  // Carrega els experiments disponibles.
  useEffect(() => {
    const fetchExperiments = async () => {
      try {
        const response = await fetch(`${API_URL}/experiments`);

        if (!response.ok) {
          throw new Error("Could not load experiments");
        }

        const data = await response.json();
        const availableExperiments = data.experiments ?? [];

        setExperiments(availableExperiments);

        setScenarios(current =>
          current.map((scenario, index) => {
            const experiment = availableExperiments[index];

            if (!experiment) return scenario;

            return {
              ...scenario,
              experimentId: experiment.id,
              experimentName: experiment.name
            };
          })
        );
      } catch (error) {
        console.error("Error loading experiments:", error);
      }
    };

    fetchExperiments();
  }, []);

  // Carrega els KPIs dels experiments seleccionats.
  useEffect(() => {
    const experimentIds = [
      ...new Set(
        scenarios
          .map(scenario => scenario.experimentId)
          .filter(Boolean)
      )
    ];

    if (!experimentIds.length) return;

    let active = true;

    const fetchExperimentKpis = async () => {
      setLoadingKpis(true);

      try {
        const results = await Promise.all(
          experimentIds.map(async experimentId => {
            const response = await fetch(
              `${API_URL}/experiments/${experimentId}/kpis/community`
            );

            if (!response.ok) {
              throw new Error(
                `Could not load KPIs for ${experimentId}`
              );
            }

            const data = await response.json();

            return [experimentId, data];
          })
        );

        if (active) {
          setExperimentKpis(current => ({
            ...current,
            ...Object.fromEntries(results)
          }));
        }
      } catch (error) {
        console.error("Error loading experiment KPIs:", error);
      } finally {
        if (active) {
          setLoadingKpis(false);
        }
      }
    };

    fetchExperimentKpis();

    return () => {
      active = false;
    };
  }, [
    scenarios.map(scenario => scenario.experimentId).join("|")
  ]);

  // Canvia l'experiment seleccionat en una targeta.
  const changeScenario = (scenarioId, experimentId) => {
    const experiment = experiments.find(
      item => item.id === experimentId
    );

    if (!experiment) return;

    setScenarios(current =>
      current.map(scenario =>
        scenario.id === scenarioId
          ? {
              ...scenario,
              experimentId: experiment.id,
              experimentName: experiment.name
            }
          : scenario
      )
    );
  };

  // Elimina un escenari, mantenint-ne sempre dos com a mínim.
  const removeScenario = id => {
    setScenarios(current =>
      current.length > 2
        ? current.filter(scenario => scenario.id !== id)
        : current
    );
  };

  // Afegeix un nou escenari amb un experiment encara no seleccionat.
  const addScenario = () => {
    if (scenarios.length >= 3) return;

    const availableExperiment = experiments.find(
      experiment =>
        !scenarios.some(
          scenario => scenario.experimentId === experiment.id
        )
    );

    if (!availableExperiment) return;

    const letter = ["A", "B", "C"].find(
      item =>
        !scenarios.some(scenario => scenario.id === `scenario-${item.toLowerCase()}`)
    );

    if (!letter) return;

    setScenarios(current => [
      ...current,
      {
        id: `scenario-${letter.toLowerCase()}`,
        label: `Experiment ${current.length + 1}`,
        experimentId: availableExperiment.id,
        experimentName: availableExperiment.name,
        color: "#8b744b",
        marker: "◆"
      }
    ]);
  };

  return (
    <main className="page-width results-page compare-page">
      <ResultsPageHeader
        subtitle="Compare different energy community configurations and identify which one best matches your priorities."
        period={period}
        onPeriodChange={setPeriod}
        alternative={alternative}
        onAlternativeChange={setAlternative}
        periods={periods}
      />

      <ResultsTabs active="compare" />

      {/* EXPERIMENTS TO COMPARE */}
      <section className="compare-section scenario-section">
        <h2>Experiments to compare</h2>

        <div className="scenario-grid">
          {scenarios.map(scenario => (
            <article className="scenario-card" key={scenario.id}>
              <div className="scenario-card-top">
                <span className="scenario-name">
                  <i style={{ color: scenario.color }}>
                    {scenario.marker}
                  </i>
                  {scenario.label}
                </span>

                <button
                  type="button"
                  className="icon-button"
                  aria-label={`Remove ${scenario.label}`}
                  onClick={() => removeScenario(scenario.id)}
                  disabled={scenarios.length <= 2}
                >
                  ✖
                </button>
              </div>

              <strong>{scenario.label}</strong>

              <label
                className="sr-only"
                htmlFor={`${scenario.id}-select`}
              >
                Choose experiment
              </label>

              <select
                id={`${scenario.id}-select`}
                value={scenario.experimentId ?? ""}
                onChange={event =>
                  changeScenario(scenario.id, event.target.value)
                }
                disabled={!experiments.length}
              >
                {experiments.map(experiment => (
                  <option key={experiment.id} value={experiment.id}>
                    {experiment.name}
                  </option>
                ))}
              </select>
            </article>
          ))}
        </div>

        <button
          type="button"
          className="add-scenario-button"
          onClick={addScenario}
          disabled={scenarios.length >= 3 || !experiments.length}
        >
          ＋ Add scenario
        </button>
      </section>

      {/* CUSTOMIZE INDICATORS */}
      <section className="compare-section indicator-section">
        <div className="compare-section-title">
          <h2>Customize indicators</h2>
          <p>
            Select the dimensions and indicators you want to compare.
          </p>
        </div>

        <div className="dimension-chips">
          {dimensions.map(dimension => (
            <button
              key={dimension.id}
              type="button"
              className={
                selectedDimensions.includes(dimension.id) ? "selected" : ""
              }
              style={{ "--dimension-color": dimension.color }}
              onClick={() => toggleDimension(dimension)}
            >
              {selectedDimensions.includes(dimension.id) ? "✓" : "+"}{" "}
              {dimension.label}
            </button>
          ))}
        </div>

        <div className="indicator-catalog">
          <div className="catalog-heading">
            <strong>☷ Full indicator catalogue</strong>
            <span>⌃</span>
          </div>

          <div className="catalog-actions">
            <button
              type="button"
              onClick={() =>
                setSelected(allIndicators.map(item => item.id))
              }
            >
              Select all
            </button>

            <button
              type="button"
              onClick={() => setSelected([])}
            >
              Deselect all
            </button>
          </div>

          <div className="indicator-groups">
            {dimensions.map(dimension => (
              <section className="indicator-group" key={dimension.id}>
                <button
                  type="button"
                  className="indicator-group-title"
                  onClick={() => toggleAll(dimension)}
                  style={{ color: dimension.color }}
                >
                  <span>{dimension.icon}</span>
                  {dimension.label}
                  <span className="chevron">⌃</span>
                </button>

                {dimension.indicators.map(indicator => (
                  <label className="indicator-option" key={indicator.id}>
                    <input
                      type="checkbox"
                      checked={selected.includes(indicator.id)}
                      onChange={() => toggleIndicator(indicator.id)}
                    />
                    <span>{indicator.label}</span>
                  </label>
                ))}
              </section>
            ))}
          </div>

          <p className="catalog-note">
          </p>

          <div className="catalog-footer">
            <button
              type="button"
              className="apply-button"
              onClick={() => setApplied(selected)}
            >
              ✓ Apply filters
            </button>
          </div>
        </div>
      </section>

      {/* COMPARISON RESULTS */}
      <section className="compare-section comparison-results">
        <div className="comparison-title-row">
          <h2>Indicator comparison</h2>

          <span>
            {selectedRows.length} KPIs
            {loadingKpis ? " · Loading..." : ""}
          </span>
        </div>

        <div className="comparison-table-scroll">
          <table className="comparison-table">
            <thead>
              <tr>
                <th className="indicator-column">
                  Indicator
                </th>

                {scenarios.map(scenario => (
                  <th key={scenario.id}>
                    <span className="scenario-table-name">
                      <i style={{ color: scenario.color }}>
                        {scenario.marker}
                      </i>
                      {scenario.label}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {selectedRows.map(indicator => {
                const best = bestScenarioIndex(
                  indicator,
                  scenarios,
                  experimentKpis,
                  period
                );

                return (
                  <tr key={indicator.id}>
                    <td className="indicator-column">
                      <strong
                        style={{
                          borderColor: dimensions.find(dimension =>
                            dimension.indicators.some(
                              item => item.id === indicator.id
                            )
                          )?.color
                        }}
                      >
                        {indicator.label}
                      </strong>

                      <small>
                        {indicator.direction === "higher"
                          ? "↑ Higher is better"
                          : indicator.direction === "lower"
                            ? "↓ Lower is better"
                            : indicator.direction === "closestOne"
                              ? "→ Closer to 1 is better"
                              : "Direction not defined"}
                      </small>
                    </td>

                    {scenarios.map((scenario, index) => {
                      const value = getIndicatorValue(
                        indicator,
                        experimentKpis[scenario.experimentId],
                        period
                      );

                      return (
                        <td key={scenario.id}>
                          <span
                            className={
                              best === index && value !== null
                                ? "best-value"
                                : ""
                            }
                          >
                            {formatKpiValue(value, indicator.format)}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}

              {!selectedRows.length && (
                <tr>
                  <td
                    colSpan={scenarios.length + 1}
                    className="empty-table"
                  >
                    Select indicators and apply the filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
