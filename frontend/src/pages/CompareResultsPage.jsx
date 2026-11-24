
import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import ResultsPageHeader from "../components/ResultsPageHeader";
import ResultsTabs from "../components/ResultsTabs";
import { api } from "../api/api";
import { communityKpiSections, defaultSelectedIndicators } from "../data/communityKpiConfig";

const SCENARIO_MARKERS = ["●", "■", "◆", "▲", "★", "⬟", "✦", "✚", "⬢", "✿", "◉", "✧", "⬣", "✪", "❖", "✳", "⬤", "◈", "✺", "✥"];
const SCENARIO_COLORS = ["#3e7b48", "#b89b62", "#8b744b", "#3d5e80", "#8a7799", "#b65d4a", "#39858a", "#7c8541"];

function getAvailablePeriods(experiments) {
  return [...new Map(
    experiments.flatMap(experiment => experiment.available_periods ?? [])
      .map(period => [period.id, period])
  ).values()];
}

function alternativeLetter(index) {
  let value = index + 1;
  let label = "";
  while (value > 0) {
    value--;
    label = String.fromCharCode(65 + value % 26) + label;
    value = Math.floor(value / 26);
  }
  return label;
}

function scenarioPresentation(index) {
  const marker = SCENARIO_MARKERS[index % SCENARIO_MARKERS.length];
  const suffix = index >= SCENARIO_MARKERS.length
    ? String(Math.floor(index / SCENARIO_MARKERS.length) + 1)
    : "";
  return {
    id: `scenario-${index + 1}`,
    label: `Alternative ${alternativeLetter(index)}`,
    marker: `${marker}${suffix}`,
    color: SCENARIO_COLORS[index % SCENARIO_COLORS.length]
  };
}

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

    case "months":
      return `${new Intl.NumberFormat("en-GB", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(number)} months`;

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
  const [searchParams] = useSearchParams();
  const simulationId = searchParams.get("simulation");
  const [resolvedSimulationId, setResolvedSimulationId] = useState(simulationId || "");
  const [period, setPeriod] = useState("");
  const [alternative, setAlternative] = useState("");

  const [scenarios, setScenarios] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [experimentKpis, setExperimentKpis] = useState({});
  const [loadingKpis, setLoadingKpis] = useState(false);

  const allIndicators = communityKpiSections.flatMap(section =>
    section.indicators.map(indicator => ({
      ...indicator,
      category: section.title,
      sectionId: section.id,
      color: section.color
    }))
  );

  const [selected, setSelected] = useState(defaultSelectedIndicators);
  const [applied, setApplied] = useState(defaultSelectedIndicators);
  const selectedDimensions = communityKpiSections
    .filter(section =>
      section.indicators.some(indicator => selected.includes(indicator.id))
    )
    .map(section => section.id);

  const selectedRows = allIndicators.filter(indicator => applied.includes(indicator.id));

  const toggleDimension = section => {
    const ids = section.indicators.map(indicator => indicator.id);
    const allSelected = ids.every(id => selected.includes(id));

    setSelected(current =>
      allSelected
        ? current.filter(id => !ids.includes(id))
        : [...new Set([...current, ...ids])]
    );
  };

  const toggleIndicator = id => {
    setSelected(current =>
      current.includes(id)
        ? current.filter(item => item !== id)
        : [...current, id]
    );
  };

  // Carrega els experiments de la simulació seleccionada.
  useEffect(() => {
    let active = true;
    const fetchExperiments = async () => {
      try {
        let selectedSimulation = simulationId;
        if (!selectedSimulation) {
          setResolvedSimulationId("");
          setExperiments([]);
          setScenarios([]);
          throw new Error("No hi ha cap simulació seleccionada.");
        }

        const data = await api.getExperiments(selectedSimulation);
        if (!active) return;

        const availableExperiments = data.experiments ?? [];
        setResolvedSimulationId(selectedSimulation);
        setExperiments(availableExperiments);
        setScenarios(
          availableExperiments.slice(0, Math.min(2, availableExperiments.length)).map((experiment, index) => ({
            ...scenarioPresentation(index),
            experimentId: experiment.id,
            experimentName: experiment.name
          }))
        );
        const periodIds = getAvailablePeriods(availableExperiments).map(item => item.id);
        setPeriod(current => periodIds.includes(current) ? current : (periodIds[0] ?? ""));
      } catch (error) {
        console.error("Error loading experiments:", error);
      }
    };
    fetchExperiments();
    return () => { active = false; };
  }, [simulationId]);

  // Carrega els KPIs dels experiments seleccionats dins la simulació activa.
  useEffect(() => {
    const experimentIds = [...new Set(
      scenarios.map(scenario => scenario.experimentId).filter(Boolean)
    )];
    if (!resolvedSimulationId || !experimentIds.length) return;

    let active = true;
    const fetchExperimentKpis = async () => {
      setLoadingKpis(true);
      try {
        const results = await Promise.all(
          experimentIds.map(async experimentId => {
            const data = await api.getCommunityKpis(resolvedSimulationId, experimentId);
            return [experimentId, data];
          })
        );
        if (active) setExperimentKpis(Object.fromEntries(results));
      } catch (error) {
        console.error("Error loading experiment KPIs:", error);
      } finally {
        if (active) setLoadingKpis(false);
      }
    };
    fetchExperimentKpis();
    return () => { active = false; };
  }, [resolvedSimulationId, scenarios.map(scenario => scenario.experimentId).join("|")]);

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

  // Elimina qualsevol alternativa.
  const removeScenario = id => {
    setScenarios(current => current.filter(scenario => scenario.id !== id));
  };

  // Afegeix el primer experiment que encara no s'estigui comparant.
  const addScenario = () => {
    const availableExperiment = experiments.find(
      experiment => !scenarios.some(scenario => scenario.experimentId === experiment.id)
    );
    if (!availableExperiment) return;

    const usedIndexes = scenarios
      .map(scenario => Number(scenario.id.replace("scenario-", "")) - 1)
      .filter(Number.isInteger);
    let nextIndex = 0;
    while (usedIndexes.includes(nextIndex)) nextIndex++;

    setScenarios(current => [
      ...current,
      {
        ...scenarioPresentation(nextIndex),
        experimentId: availableExperiment.id,
        experimentName: availableExperiment.name
      }
    ]);
  };

  return (
    <main className="page-width results-page compare-page">
      <ResultsPageHeader
        simulationId={resolvedSimulationId}
        subtitle="Compare different energy community configurations and identify which one best matches your priorities."
        period={period}
        onPeriodChange={setPeriod}
        alternative={alternative}
        onAlternativeChange={setAlternative}
        periods={getAvailablePeriods(experiments)}
      />

      <ResultsTabs />

      {/* EXPERIMENTS TO COMPARE */}
      <section className="compare-section scenario-section">
        <h2>Experiments to compare</h2>

        <div className="scenario-grid">
          {scenarios.map(scenario => (
            <article className="scenario-card" key={scenario.id}>
              <div className="scenario-card-top">
                <span className="scenario-name">
                  <i style={{ color: scenario.color }}>{scenario.marker}</i>
                  <span style={{ color: scenario.color }}>{scenario.label}</span>
                </span>
                <button
                  type="button"
                  className="icon-button"
                  aria-label={`Remove ${scenario.label}`}
                  onClick={() => removeScenario(scenario.id)}
                >
                  ✖
                </button>
              </div>

              <label className="sr-only" htmlFor={`${scenario.id}-select`}>
                Choose experiment
              </label>
              <select
                id={`${scenario.id}-select`}
                value={scenario.experimentId ?? ""}
                onChange={event => changeScenario(scenario.id, event.target.value)}
                disabled={!experiments.length}
              >
                {experiments.map(experiment => (
                  <option
                    key={experiment.id}
                    value={experiment.id}
                    disabled={scenarios.some(item => item.id !== scenario.id && item.experimentId === experiment.id)}
                  >
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
          disabled={!experiments.some(experiment => !scenarios.some(scenario => scenario.experimentId === experiment.id))}
        >
          ＋ Add alternative
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
          {communityKpiSections.map(section => (
            <button
              key={section.id}
              type="button"
              className={selectedDimensions.includes(section.id) ? "selected" : ""}
              style={{ "--dimension-color": section.color }}
              onClick={() => toggleDimension(section)}
            >
              {selectedDimensions.includes(section.id) ? "✓" : "+"}{" "}
              {section.title}
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
              onClick={() => setSelected(allIndicators.map(item => item.id))}
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
            {communityKpiSections.map(section => {
              const allSelected = section.indicators.every(indicator =>
                selected.includes(indicator.id)
              );

              return (
                <section className="indicator-group" key={section.id}>
                  <button
                    type="button"
                    className="indicator-group-title"
                    onClick={() => toggleDimension(section)}
                    style={{ color: section.color }}
                  >
                    {section.title}
                    <span className="chevron">
                      {allSelected ? "✓" : "+"}
                    </span>
                  </button>

                  {section.indicators.map(indicator => (
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
              );
            })}
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
                <th className="indicator-column">Indicator</th>

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
                          borderColor: indicator.color
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
                        <td key={scenario.id} style={{ textAlign: "left" }}>
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
