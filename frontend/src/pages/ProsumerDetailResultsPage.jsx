import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import { formatKpiValue } from "../utils/formatKpi";
import { api } from "../api/api";
import { PROSUMER_COLUMNS, PROSUMER_SECTIONS } from "../utils/prosumerKpiMeta";

const SEASON_ORDER = ["winter", "spring", "summer", "autumn"];

export default function ProsumerDetailResultsPage() {
  const { prosumerId } = useParams();
  const [searchParams] = useSearchParams();
  const simulationFromUrl = searchParams.get("simulation");
  const [simulationId, setSimulationId] = useState(simulationFromUrl || "");
  const [experiments, setExperiments] = useState([]);
  const [alternative, setAlternative] = useState("");
  const [period, setPeriod] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    async function loadExperiments() {
      try {
        let selectedSimulation = simulationFromUrl;
        if (!selectedSimulation) {
          const simulations = await api.getSimulations();
          selectedSimulation = simulations.simulations?.find(name => name !== "Original_Experiment");
          if (!selectedSimulation) throw new Error("No simulations available");
        }
        const result = await api.getExperiments(selectedSimulation);
        if (!active) return;
        setSimulationId(selectedSimulation);
        setExperiments(result.experiments ?? []);
        setAlternative(current => result.experiments?.some(item => item.id === current)
          ? current : result.experiments?.[0]?.id ?? "");
      } catch (err) {
        if (active) { setError(err.message); setLoading(false); }
      }
    }
    loadExperiments();
    return () => { active = false; };
  }, [simulationFromUrl]);

  useEffect(() => {
    if (!simulationId || !alternative) return;
    let active = true;
    async function loadResults() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getProsumerKpis(simulationId, alternative);
        if (!active) return;
        setData(result);
        const available = result.periods ?? [];
        setPeriod(current => available.some(item => item.id === current) ? current : available[0]?.id ?? "");
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    }
    loadResults();
    return () => { active = false; };
  }, [simulationId, alternative]);

  const periods = useMemo(() => (data?.periods ?? [])
    .slice()
    .sort((a, b) => SEASON_ORDER.indexOf(a.id) - SEASON_ORDER.indexOf(b.id))
    .map(item => ({ id: item.id, label: item.label })), [data]);
  const selectedPeriod = data?.periods?.find(item => item.id === period);
  const prosumerKpis = selectedPeriod?.prosumers?.[prosumerId];

  if (loading && !data) return <main className="page-width results-page"><p>Loading prosumer details...</p></main>;
  if (error) return <main className="page-width results-page"><p className="results-error" role="alert">{error}</p></main>;
  if (!prosumerKpis) return (
    <main className="page-width results-page">
      <p className="results-error">No results were found for prosumer “{prosumerId}” in this period.</p>
      <Link to={`/results/prosumers${searchParams.toString() ? `?${searchParams}` : ""}`}>Back to prosumers</Link>
    </main>
  );

  return (
    <main className="page-width results-page prosumer-detail-results-page">
      <ResultsPageHeader
        simulationId={simulationId}
        experiments={experiments}
        period={period}
        onPeriodChange={setPeriod}
        alternative={alternative}
        onAlternativeChange={setAlternative}
        periods={periods}
      />
      <ResultsTabs prosumerId={prosumerId} />
      <div className="prosumer-detail-intro">
        <Link to={`/results/prosumers${searchParams.toString() ? `?${searchParams}` : ""}`} className="results-back-link">← All prosumers</Link>
        <h2>{prosumerId}</h2>
        <p>Individual results for {prosumerId} · {selectedPeriod?.label ?? period}</p>
      </div>
      {PROSUMER_SECTIONS.map(section => {
        const columns = PROSUMER_COLUMNS[section.id].filter(([key]) => key !== "prosumer");
        return (
          <section className="result-section prosumer-detail-section" key={section.id}>
            <SectionHeading title={section.title} description={section.description} color={section.color} />
            <div className="prosumer-detail-kpi-grid">
              {columns.map(([key, label]) => {
                const value = prosumerKpis[key]?.value ?? null;
                return (
                  <article className="prosumer-detail-kpi" key={key}>
                    <span>{label}</span>
                    <strong>{formatKpiValue(value, key)}</strong>
                  </article>
                );
              })}
            </div>
          </section>
        );
      })}
    </main>
  );
}
