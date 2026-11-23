export const PROSUMER_SECTIONS = [
  { id: "energy", title: "Energy KPIs", color: "#3e7b48" },
  { id: "economic", title: "Economic KPIs", description: "Monthly values and annual returns per participant", color: "#b89b62" },
  { id: "social", title: "Social KPIs", description: "Distribution of benefits, savings and investment", color: "#8a7799" },
  { id: "environmental", title: "Environmental KPIs", color: "#3d5e80" }
];

export const PROSUMER_COLUMNS = {
  energy: [
    ["prosumer", "Prosumer"],
    ["selfConsumption", "Self-Consumption"],
    ["selfSufficiency", "Self-Sufficiency"],
    ["gridDependency", "Grid Dependency"],
    ["netP2p", "Net P2P Balance"],
    ["p2pParticipation", "P2P Participation"],
    ["sharedEnergy", "Shared energy (purchases − grid exports)"],
    ["p2pDeficit", "P2P trading index in deficit"],
    ["p2pSurplus", "P2P trading index in surplus"]
  ],
  economic: [
    ["prosumer", "Prosumer"],
    ["finalBill", "Total final bill (€/month)"],
    ["saved", "Saved by entering community (€/month)"],
    ["annualProfit", "Annual profit (annual return)"]
  ],
  social: [
    ["prosumer", "Prosumer"],
    ["billReduction", "Bill reduction"],
    ["gainAppropriation", "EC gain appropriation"],
    ["savingsAppropriation", "EC savings appropriation"],
    ["investmentContribution", "Contribution into EC investment"]
  ],
  environmental: [
    ["prosumer", "Prosumer"],
    ["avoidedEmissions", "Avoided annual emissions (kg CO₂ eq/year)"],
    ["environmentalImpact", "Environmental impact (with/without community)"],
    ["carbonDebt", "Upfront carbon debt"],
    ["carbonPayback", "Total carbon payback time"]
  ]
};

// Comparisons are allowed only when the unit and scale are known to match.
// Less clearly defined indicators are intentionally restricted to one KPI at a time.
export const KPI_META = {
  selfConsumption: { unit: "%", group: "energy-ratios", scale: 100 },
  selfSufficiency: { unit: "%", group: "energy-ratios", scale: 100 },
  gridDependency: { unit: "%", group: "energy-ratios", scale: 100 },
  p2pParticipation: { unit: "%", group: "energy-ratios", scale: 100 },
  netP2p: { unit: "kWh", group: "energy-volume", scale: 1 },
  sharedEnergy: { unit: "kWh", group: "energy-volume", scale: 1 },
  p2pDeficit: { unit: "index", group: "p2p-deficit", scale: 1 },
  p2pSurplus: { unit: "index", group: "p2p-surplus", scale: 1 },
  finalBill: { unit: "€/month", group: "monthly-euros", scale: 1 },
  saved: { unit: "€/month", group: "monthly-euros", scale: 1 },
  annualProfit: { unit: "annual return", group: "annual-profit", scale: 1 },
  billReduction: { unit: "value", group: "bill-reduction", scale: 1 },
  gainAppropriation: { unit: "value", group: "gain-appropriation", scale: 1 },
  savingsAppropriation: { unit: "value", group: "savings-appropriation", scale: 1 },
  investmentContribution: { unit: "value", group: "investment-contribution", scale: 1 },
  avoidedEmissions: { unit: "kg CO₂ eq/year", group: "avoided-emissions", scale: 1 },
  environmentalImpact: { unit: "value", group: "environmental-impact", scale: 1 },
  carbonDebt: { unit: "value", group: "carbon-debt", scale: 1 },
  carbonPayback: { unit: "years", group: "carbon-payback", scale: 1 }
};

export function getKpiMeta(key) {
  return KPI_META[key] ?? { unit: "value", group: key, scale: 1 };
}
