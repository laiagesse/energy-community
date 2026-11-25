import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import { formatKpiValue } from "../utils/formatKpi";
import { api } from "../api/api";
import { PROSUMER_COLUMNS, PROSUMER_SECTIONS } from "../utils/prosumerKpiMeta";

export default function ProsumerDetailResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const simulationFromUrl = searchParams.get("simulation");
  const prosumerFromUrl = searchParams.get("prosumer") ?? "";
  const [simulationId, setSimulationId] = useState(simulationFromUrl || "");
  const [experiments, setExperiments] = useState([]);
  const [alternative, setAlternative] = useState("");
  const [period, setPeriod] = useState("");
  const [selectedProsumer, setSelectedProsumer] = useState(prosumerFromUrl);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Keep the selector in sync when this page is opened from the prosumer table.
  useEffect(() => {
    setSelectedProsumer(prosumerFromUrl);
  }, [prosumerFromUrl]);

  useEffect(() => {
    let active = true;
    async function loadExperiments() {
      setLoading(true);
      setError(null);
      try {
        let selectedSimulation = simulationFromUrl;
        if (!selectedSimulation) {
          setSimulationId("");
          setExperiments([]);
          setAlternative("");
          setError("No hi ha cap simulació seleccionada.");
          setLoading(false);
          return;
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
        setPeriod(current => available.some(item => item.id === current)
          ? current
          : available.find(item => item.id === "annual")?.id ?? available[0]?.id ?? "");
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
    .map(item => ({ id: item.id, label: item.label })), [data]);
  const selectedPeriod = data?.periods?.find(item => item.id === period);
  const prosumers = selectedPeriod?.prosumers ?? {};
  const prosumerIds = Object.keys(prosumers).sort((a, b) => a.localeCompare(b));
  const prosumerKpis = selectedProsumer ? prosumers[selectedProsumer] : null;

  const handleProsumerChange = value => {
    setSelectedProsumer(value);
    const next = new URLSearchParams(searchParams);
    if (value) next.set("prosumer", value);
    else next.delete("prosumer");
    if (simulationId) next.set("simulation", simulationId);
    setSearchParams(next, { replace: true });
  };

  if (loading && !data) return <main className="page-width results-page"><p>Loading prosumer details...</p></main>;
  if (error) return <main className="page-width results-page"><p className="results-error" role="alert">{error}</p></main>;

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
      <ResultsTabs />
      <div className="results-heading prosumer-detail-heading">
        <div className="results-title-block">
          <h1>{selectedProsumer || "Select a prosumer to view its individual results."}</h1>
        </div>
        <div className="results-actions">
          <select
            id="prosumer-detail-selector"
            value={selectedProsumer}
            onChange={event => handleProsumerChange(event.target.value)}
            disabled={!prosumerIds.length}
            aria-label="Select a prosumer"
          >
            <option value="">Select a prosumer...</option>
            {prosumerIds.map(id => <option value={id} key={id}>{id}</option>)}
          </select>
        </div>
      </div>
      {selectedProsumer && !prosumerKpis && (
        <p className="results-error">No results were found for prosumer “{selectedProsumer}” in this period.</p>
      )}
      {prosumerKpis && PROSUMER_SECTIONS.map(section => {
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
                    <strong>{formatKpiValue(value, key, period)}</strong>
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
