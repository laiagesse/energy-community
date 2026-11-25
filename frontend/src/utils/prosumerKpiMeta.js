export const PROSUMER_SECTIONS = [
  { id: "energy", title: "Energy KPIs", color: "#3e7b48" },
  { id: "economic", title: "Economic KPIs", description: "Values and returns for the selected period", color: "#b89b62" },
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
    ["finalBill", "Final bill"],
    ["saved", "Saved by entering community"],
    ["annualProfit", "Profit (Return on investment)"],
    ["payback", "Payback time"]
  ],
  social: [
    ["prosumer", "Prosumer"],
    ["billReduction", "Bill reduction"],
    ["gainAppropriation", "Community gains appropriation"],
    ["savingsAppropriation", "Community savings appropriation"],
    ["investmentContribution", "Investment contribution"]
  ],
  environmental: [
    ["prosumer", "Prosumer"],
    ["avoidedEmissions", "Avoided emissions"],
    ["environmentalImpact", "Environmental impact"],
    ["carbonDebt", "Carbon debt"],
    ["carbonPayback", "Carbon payback time"]
  ]
};

// Comparisons are allowed only when the unit and scale are known to match.
// Less clearly defined indicators are intentionally restricted to one KPI at a time.
export const KPI_META = {
  selfConsumption: { unit: "%", group: "energy-ratios", scale: 100 },
  selfSufficiency: { unit: "%", group: "energy-ratios", scale: 100 },
  gridDependency: { unit: "%", group: "energy-ratios", scale: 100 },
  p2pParticipation: { unit: "kWh", group: "energy-volume", scale: 1 },
  netP2p: { unit: "kWh", group: "energy-volume", scale: 1 },
  sharedEnergy: { unit: "kWh", group: "energy-volume", scale: 1 },
  p2pDeficit: { unit: "%", group: "p2p-deficit", scale: 100 },
  p2pSurplus: { unit: "%", group: "p2p-surplus", scale: 100 },
  finalBill: { unit: "€", group: "monthly-euros", scale: 1 },
  saved: { unit: "€", group: "monthly-euros", scale: 1 },
  annualProfit: { unit: "%", group: "period-profit", scale: 100 },
  payback: { unit: "months", group: "economic-payback", scale: 1 },
  billReduction: { unit: "%", group: "bill-reduction", scale: 100 },
  gainAppropriation: { unit: "%", group: "gain-appropriation", scale: 100 },
  savingsAppropriation: { unit: "%", group: "savings-appropriation", scale: 100 },
  investmentContribution: { unit: "%", group: "investment-contribution", scale: 100 },
  avoidedEmissions: { unit: "kg CO₂ eq", group: "avoided-emissions", scale: 1 },
  environmentalImpact: { unit: "%", group: "environmental-impact", scale: 100 },
  carbonDebt: { unit: "kg CO₂ eq", group: "carbon-debt", scale: 1 },
  carbonPayback: { unit: "months", group: "carbon-payback", scale: 1 }
};

export function getKpiMeta(key) {
  return KPI_META[key] ?? { unit: "value", group: key, scale: 1 };
}
