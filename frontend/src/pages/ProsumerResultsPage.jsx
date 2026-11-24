import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import KpiTable from "../components/KpiTable";
import KpiChartExplorer from "../components/KpiChartExplorer";
import { api } from "../api/api";
import { PROSUMER_COLUMNS, PROSUMER_SECTIONS, getKpiMeta } from "../utils/prosumerKpiMeta";

export default function ProsumerResultsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const simulationId = searchParams.get("simulation");
  const [period, setPeriod] = useState("");
  const [resolvedSimulationId, setResolvedSimulationId] = useState(simulationId || "");
  const [alternative, setAlternative] = useState("");
  const [experiments, setExperiments] = useState([]);
  const [prosumerData, setProsumerData] = useState(null);
  const [loadingExperiments, setLoadingExperiments] = useState(true);
  const [loadingResults, setLoadingResults] = useState(false);
  const [error, setError] = useState(null);
  const [selectedKpis, setSelectedKpis] = useState({});

  useEffect(() => {
    let active = true;
    const fetchExperiments = async () => {
      setLoadingExperiments(true);
      setError(null);
      try {
        let selectedSimulation = simulationId;
        if (!selectedSimulation) {
          setResolvedSimulationId("");
          setExperiments([]);
          setAlternative("");
          setError("No hi ha cap simulació seleccionada.");
          return;
        }
        const data = await api.getExperiments(selectedSimulation);
        if (!active) return;
        setResolvedSimulationId(selectedSimulation);
        setExperiments(data.experiments ?? []);
        setAlternative(current =>
          data.experiments?.some(item => item.id === current)
            ? current
            : data.experiments?.[0]?.id ?? ""
        );
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoadingExperiments(false);
      }
    };
    fetchExperiments();
    return () => { active = false; };
  }, [simulationId]);

  useEffect(() => {
    if (!alternative || !resolvedSimulationId) return;
    let active = true;
    const fetchProsumerResults = async () => {
      setLoadingResults(true);
      setError(null);
      setProsumerData(null);
      try {
        const data = await api.getProsumerKpis(resolvedSimulationId, alternative);
        if (!active) return;
        setProsumerData(data);
        const available = data.periods ?? [];
        if (!available.some(item => item.id === period)) setPeriod(available[0]?.id ?? "");
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoadingResults(false);
      }
    };
    fetchProsumerResults();
    return () => { active = false; };
  }, [alternative, resolvedSimulationId]);

  const periods = (prosumerData?.periods ?? [])
    .map(item => ({ id: item.id, label: item.label }));
  const selectedPeriodData = prosumerData?.periods?.find(item => item.id === period);
  const prosumers = selectedPeriodData?.prosumers ?? {};
  const prosumerRows = Object.entries(prosumers).map(([prosumer, kpis]) => {
    const row = { prosumer };
    Object.entries(kpis).forEach(([key, result]) => { row[key] = result?.value ?? null; });
    return row;
  });

  const handleKpiToggle = (sectionId, key) => {
    setSelectedKpis(current => {
      const currentKeys = current[sectionId] ?? [];
      if (currentKeys.includes(key)) {
        return { ...current, [sectionId]: currentKeys.filter(item => item !== key) };
      }
      const newGroup = getKpiMeta(key).group;
      const compatible = currentKeys.filter(item => getKpiMeta(item).group === newGroup);
      return { ...current, [sectionId]: [...compatible, key] };
    });
  };

  const openProsumer = prosumer => {
    const query = searchParams.toString();
    const params = new URLSearchParams(query);
    params.set("prosumer", prosumer);
    navigate(`/results/prosumer-detail?${params.toString()}`);
  };

  if (loadingExperiments) return <p>Loading experiments...</p>;
  if (error && !prosumerData) return <p role="alert">Error: {error}</p>;
  if (!experiments.length) return <p>No experiments available.</p>;
  if (loadingResults) return <p>Loading prosumer results...</p>;
  if (error) return <p role="alert">Error: {error}</p>;
  if (!prosumerData) return <p>No prosumer results available.</p>;

  return (
    <main className="page-width results-page prosumer-results-page">
      <ResultsPageHeader
        simulationId={resolvedSimulationId}
        experiments={experiments}
        loadingExperiments={loadingExperiments}
        period={period}
        onPeriodChange={setPeriod}
        alternative={alternative}
        onAlternativeChange={setAlternative}
        periods={periods}
      />
      <ResultsTabs />
      <div className="prosumer-table-intro">
        <p>Select the chart icon in an indicator heading to compare prosumers. Select a prosumer name to open its details in the Prosumer details tab.</p>
      </div>
      {PROSUMER_SECTIONS.map(section => {
        const sectionColumns = PROSUMER_COLUMNS[section.id].map(([key, label]) => ({ key, label }));
        const sectionSelected = selectedKpis[section.id] ?? [];
        return (
          <section className="result-section" key={section.id}>
            <SectionHeading title={section.title} description={section.description} color={section.color} />
            <KpiTable
              columns={sectionColumns}
              rows={prosumerRows}
              label={`${section.title} by prosumer`}
              selectedKpis={sectionSelected}
              onKpiToggle={key => handleKpiToggle(section.id, key)}
              onProsumerClick={openProsumer}
            />
            <KpiChartExplorer
              columns={sectionColumns}
              rows={prosumerRows}
              selectedKpis={sectionSelected}
              onKpiToggle={key => handleKpiToggle(section.id, key)}
            />
          </section>
        );
      })}
    </main>
  );
}
