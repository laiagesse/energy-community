import { useState, useEffect } from "react";
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

export default function ProsumerResultsPage() {
  const [period, setPeriod] = useState("winter");
  const [alternative, setAlternative] = useState("");
  const [experiments, setExperiments] = useState([]);
  const [prosumerData, setProsumerData] = useState(null);
  const [loadingExperiments, setLoadingExperiments] = useState(true);
  const [loadingResults, setLoadingResults] = useState(false);
  const [error, setError] = useState(null);

  // Load the available DoE experiments for the header selector.
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
        if (availableExperiments.length > 0) {
          setAlternative(availableExperiments[0].id);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoadingExperiments(false);
      }
    };

    fetchExperiments();
  }, []);

  // Reload prosumer KPIs whenever the selected experiment changes.
  useEffect(() => {
    if (!alternative) return;

    const fetchProsumerResults = async () => {
      setLoadingResults(true);
      setError(null);
      setProsumerData(null);

      try {
        const response = await fetch(
          `${API_URL}/experiments/${alternative}/kpis/prosumers`
        );
        if (!response.ok) {
          const detail = await response.json().catch(() => null);
          throw new Error(detail?.detail || "Could not load prosumer results");
        }

        const data = await response.json();
        setProsumerData(data);
        const availablePeriods = data.periods ?? [];
        if (!availablePeriods.some(item => item.id === period) && availablePeriods.length > 0) {
          setPeriod(availablePeriods[0].id);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoadingResults(false);
      }
    };

    fetchProsumerResults();
  }, [alternative]);

  const periods = prosumerData?.periods ?? [];
  const selectedPeriodData = periods.find(item => item.id === period);
  const prosumers = selectedPeriodData?.prosumers ?? {};
  const prosumerRows = Object.entries(prosumers).map(([prosumer, kpis]) => {
    const row = { prosumer };
    Object.entries(kpis).forEach(([key, result]) => {
      row[key] = result?.value ?? null;
    });
    return row;
  });

  if (loadingExperiments) {
    return <p>Loading experiments...</p>;
  }
  if (error && !prosumerData) {
    return <p>Error: {error}</p>;
  }
  if (experiments.length === 0) {
    return <p>No experiments available.</p>;
  }
  if (loadingResults) {
    return <p>Loading prosumer results...</p>;
  }
  if (error) {
    return <p>Error: {error}</p>;
  }
  if (!prosumerData) {
    return <p>No prosumer results available.</p>;
  }

  return (
    <main className="page-width results-page prosumer-results-page">
      <ResultsPageHeader
        period={period}
        onPeriodChange={setPeriod}
        alternative={alternative}
        onAlternativeChange={setAlternative}
        experiments={experiments}
        periods={periods}
      />
      <ResultsTabs active="prosumers" />

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
