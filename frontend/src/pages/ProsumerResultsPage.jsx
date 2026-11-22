import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import KpiTable from "../components/KpiTable";

const API_URL = "http://127.0.0.1:8000";

const columns = {
  energy: [
    ["prosumer", "Prosumer"], ["selfConsumption", "Self-Consumption Ratio"], ["selfSufficiency", "Self-Sufficiency Ratio"],
    ["gridDependency", "Grid Dependency"], ["netP2p", "Net P2P Balance"], ["p2pParticipation", "P2P Participation"],
    ["sharedEnergy", "Shared energy (purchases − grid exports)"], ["p2pDeficit", "P2P trading index in deficit"], ["p2pSurplus", "P2P trading index in surplus"]
  ],
  economic: [
    ["prosumer", "Prosumer"], ["finalBill", "Total final bill (€/month)"], ["saved", "Saved by entering community (€/month)"],
    ["annualProfit", "Annual profit (annual return)"], ["profitPv", "Annual profit PV"], ["profitWt", "Annual profit WT"],
    ["profitBattery", "Annual profit B"], ["paybackPv", "Payback time PV"], ["paybackWt", "Payback time WT"], ["paybackBattery", "Payback time B"]
  ],
  social: [
    ["prosumer", "Prosumer"], ["billReduction", "Bill reduction"], ["gainAppropriation", "EC gain appropriation"],
    ["savingsAppropriation", "EC savings appropriation"], ["investmentContribution", "Contribution into EC investment"]
  ],
  environmental: [
    ["prosumer", "Prosumer"], ["avoidedEmissions", "Avoided annual emissions (kg CO₂ eq/year)"],
    ["environmentalImpact", "Environmental impact (with/without community)"], ["carbonDebt", "Upfront carbon debt"],
    ["carbonPayback", "Total carbon payback time"], ["pvPayback", "PV carbon payback time"],
    ["wtPayback", "WT carbon payback time"], ["batteryPayback", "BATT carbon payback time"]
  ]
};

const sections = [
  { id: "energy", title: "Energy KPIs", color: "#3e7b48" },
  { id: "economic", title: "Economic KPIs", description: "Monthly values and annual returns per participant", color: "#b89b62" },
  { id: "social", title: "Social KPIs", description: "Distribution of benefits, savings and investment", color: "#8a7799" },
  { id: "environmental", title: "Environmental KPIs", color: "#3d5e80" }
];

const SEASON_ORDER = ["winter", "spring", "summer", "autumn"];

export default function ProsumerResultsPage() {
  const [searchParams] = useSearchParams();
  const simulationId = searchParams.get("simulation");
  const [period, setPeriod] = useState("");
  const [resolvedSimulationId, setResolvedSimulationId] = useState(simulationId || "");
  const [alternative, setAlternative] = useState("");
  const [experiments, setExperiments] = useState([]);
  const [prosumerData, setProsumerData] = useState(null);
  const [loadingExperiments, setLoadingExperiments] = useState(true);
  const [loadingResults, setLoadingResults] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    const fetchExperiments = async () => {
      setLoadingExperiments(true);
      setError(null);
      try {
        let selectedSimulation = simulationId;
        if (!selectedSimulation) {
          const simulationsResponse = await fetch(`${API_URL}/simulations`);
          if (!simulationsResponse.ok) throw new Error("Could not load simulations");
          const simulationsData = await simulationsResponse.json();
          selectedSimulation = simulationsData.simulations?.find(name => name !== "Original_Experiment");
          if (!selectedSimulation) throw new Error("No simulations available");
        }

        const response = await fetch(
          `${API_URL}/simulations/${encodeURIComponent(selectedSimulation)}/experiments`
        );
        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(detail?.detail || "Could not load experiments");
        }
        const data = await response.json();
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

  const selectedExperiment = experiments.find(item => item.id === alternative);
  const effectiveSimulationId = resolvedSimulationId;

  useEffect(() => {
    if (!alternative || !effectiveSimulationId) return;
    let active = true;
    const fetchProsumerResults = async () => {
      setLoadingResults(true);
      setError(null);
      setProsumerData(null);
      try {
        const response = await fetch(
          `${API_URL}/simulations/${encodeURIComponent(effectiveSimulationId)}/experiments/${encodeURIComponent(alternative)}/kpis/prosumers`
        );
        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(detail?.detail || "Could not load prosumer results");
        }
        const data = await response.json();
        if (!active) return;
        setProsumerData(data);
        const available = data.periods ?? [];
        if (!available.some(item => item.id === period)) {
          setPeriod(available[0]?.id ?? "");
        }
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoadingResults(false);
      }
    };
    fetchProsumerResults();
    return () => { active = false; };
  }, [alternative, effectiveSimulationId]);

  const periods = (prosumerData?.periods ?? [])
    .slice()
    .sort((a, b) => SEASON_ORDER.indexOf(a.id) - SEASON_ORDER.indexOf(b.id))
    .map(item => ({ id: item.id, label: item.label }));

  const selectedPeriodData = prosumerData?.periods?.find(item => item.id === period);
  const prosumers = selectedPeriodData?.prosumers ?? {};
  const prosumerRows = Object.entries(prosumers).map(([prosumer, kpis]) => {
    const row = { prosumer };
    Object.entries(kpis).forEach(([key, result]) => { row[key] = result?.value ?? null; });
    return row;
  });

  if (loadingExperiments) return <p>Loading experiments...</p>;
  if (error && !prosumerData) return <p>Error: {error}</p>;
  if (!experiments.length) return <p>No experiments available.</p>;
  if (loadingResults) return <p>Loading prosumer results...</p>;
  if (error) return <p>Error: {error}</p>;
  if (!prosumerData) return <p>No prosumer results available.</p>;

  return (
    <main className="page-width results-page prosumer-results-page">
      <ResultsPageHeader
        simulationId={effectiveSimulationId}
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
        <p>Expand a chart to get additional information for a KPI</p>
      </div>
      {sections.map(section => (
        <section className="result-section" key={section.id}>
          <SectionHeading title={section.title} description={section.description} color={section.color} />
          <KpiTable
            columns={columns[section.id].map(([key, label]) => ({ key, label }))}
            rows={prosumerRows}
            label={`${section.title} by prosumer`}
          />
        </section>
      ))}
    </main>
  );
}
