import { useState } from "react";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import KpiTable from "../components/KpiTable";
import { prosumerKpis } from "../data/prosumerResults";

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
  { id: "energy", title: "Energy KPIs", description: "Total consumption = direct self-consumption + battery discharge for own consumption + energy purchased P2P + energy purchased from the grid", color: "#3e7b48" },
  { id: "economic", title: "Economic KPIs", description: "Monthly values and annual returns per participant", color: "#b89b62" },
  { id: "social", title: "Social KPIs", description: "Distribution of benefits, savings and investment", color: "#8a7799" },
  { id: "environmental", title: "Environmental KPIs", description: "Annual emissions without the community = consumption · grid CO₂ emissions", color: "#3d5e80" }
];

export default function ProsumerResultsPage() {
  const [period, setPeriod] = useState("Annual");
  const [alternative, setAlternative] = useState("Current installation");

  return (
    <main className="page-width results-page prosumer-results-page">
      <ResultsPageHeader period={period} onPeriodChange={setPeriod} alternative={alternative} onAlternativeChange={setAlternative} />
      <ResultsTabs active="prosumers" />

      <div className="prosumer-table-intro">
        <p>All prosumers at once · click ▸ to expand a chart or additional information for a KPI</p>
        <button type="button" className="season-select">Year · average across the 4 seasons <span>⌄</span></button>
      </div>

      {sections.map(section => (
        <section className="prosumer-kpi-section" key={section.id}>
          <SectionHeading title={section.title} description={section.description} color={section.color} />
          <KpiTable
            columns={columns[section.id].map(([key, label]) => ({ key, label }))}
            rows={prosumerKpis[section.id]}
            label={`${section.title} by prosumer`}
          />
        </section>
      ))}
    </main>
  );
}
