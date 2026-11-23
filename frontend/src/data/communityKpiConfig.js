// Catàleg dels indicadors de comunitat disponibles a la comparació.
// Les metadades es defineixen al frontend; l'API només n'aporta els valors.
export const defaultSelectedIndicators = [
  "selfSufficiency",
  "selfConsumption",
  "gridDependency",
  "totalSaved",
  "avoidedEmissions",
  "fairness"
];

export const communityKpiSections = [
  {
    id: "economic",
    title: "Economic KPIs",
    color: "#b89b62",
    indicators: [
      {
        id: "totalFinalBill",
        label: "Community total final bill (€)",
        direction: "lower",
        format: "currency"
      },
      {
        id: "totalSaved",
        label: "Community total saved (€)",
        direction: "higher",
        format: "currency"
      },
      {
        id: "baselinePovertyHelp",
        label: "Baseline poverty help",
        direction: "none",
        format: "number"
      }
    ]
  },
  {
    id: "energy",
    title: "Energy KPIs",
    color: "#3e7b48",
    indicators: [
      {
        id: "selfSufficiency",
        label: "Community energy self-sufficiency (%)",
        direction: "higher",
        format: "percentage"
      },
      {
        id: "selfConsumption",
        label: "Community self-consumption (%)",
        direction: "higher",
        format: "percentage"
      },
      {
        id: "gridDependency",
        label: "Community grid dependency (%)",
        direction: "lower",
        format: "percentage"
      },
      {
        id: "selfSufficiencyGap",
        label: "Self-sufficiency gap between prosumers",
        direction: "lower",
        format: "percentage"
      }
    ]
  },
  {
    id: "environmental",
    title: "Environmental KPIs",
    color: "#3d5e80",
    indicators: [
      {
        id: "avoidedEmissions",
        label: "Annual avoided emissions (kg CO₂ eq)",
        direction: "higher",
        format: "emissions"
      },
      {
        id: "environmentalImpact",
        label: "Environmental impact (%)",
        direction: "none",
        format: "percentage"
      },
      {
        id: "carbonPaybackTime",
        label: "Carbon payback time (years)",
        direction: "lower",
        format: "years"
      }
    ]
  },
  {
    id: "social",
    title: "Social KPIs",
    color: "#8a7799",
    indicators: [
      {
        id: "fairness",
        label: "Fairness index",
        direction: "closestOne",
        format: "index"
      }
    ]
  }
];
