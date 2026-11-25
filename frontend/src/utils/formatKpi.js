
const INTEGER_KPIS = new Set([
  "totalFinalBill",
  "totalSaved",
  "finalBill",
  "saved",
  "avoidedEmissions",
  "carbonDebt",
]);

const PERCENTAGE_KPIS = new Set([
  "selfConsumption",
  "selfSufficiency",
  "gridDependency",
  "p2pDeficit",
  "p2pSurplus",
  "annualProfit",
  "profitPv",
  "profitWt",
  "profitBattery",
  "billReduction",
  "gainAppropriation",
  "savingsAppropriation",
  "investmentContribution",
  "environmentalImpact",
]);

const UNITS = {
  netP2p: " kWh",
  p2pParticipation: " kWh",
  sharedEnergy: " kWh",
  totalLoad: " kWh",
  energySurplus: " kWh",
  finalBill: " €/month",
  saved: " €/month",
  totalInvested: " €",
  payback: " months",
  avoidedEmissions: " kg CO₂ eq",
  carbonDebt: " kg CO₂ eq",
  carbonPayback: " months",
  paybackPv: " months",
  paybackWt: " months",
  paybackBattery: " months",
  pvPayback: " months",
  wtPayback: " months",
  batteryPayback: " months",
};

const FINANCIAL_PAYBACK_KPIS = new Set([
  "payback",
  "paybackPv",
  "paybackWt",
  "paybackBattery",
]);

export function formatKpiValue(value, key, period) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value !== "number") return value;

  const decimals = INTEGER_KPIS.has(key)
    ? 0
    : key === "fairness"
      ? 3
      : 1;

  const displayValue = PERCENTAGE_KPIS.has(key)
    ? value * 100
    : value;

  const formatted = new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(displayValue);

  if (PERCENTAGE_KPIS.has(key)) return `${formatted} %`;
  if (period === "annual" && FINANCIAL_PAYBACK_KPIS.has(key)) {
    return `${formatted} years`;
  }

  if ((key === "finalBill" || key === "saved") && period === "annual") {
    return `${formatted} €`;
  }

  return `${formatted}${UNITS[key] ?? ""}`;
}
