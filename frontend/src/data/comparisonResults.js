
export const initialScenarios = [
  {
    id: "scenario-a",
    label: "Experiment 1",
    color: "#3e7b48",
    marker: "●"
  },
  {
    id: "scenario-b",
    label: "Experiment 2",
    color: "#b89b62",
    marker: "■"
  },
  {
    id: "scenario-c",
    label: "Experiment 3",
    color: "#8b744b",
    marker: "◆"
  }
];

export const defaultSelectedIndicators = [
  "selfSufficiency",
  "selfConsumption",
  "gridDependency",
  "totalSaved",
  "avoidedEmissions",
  "fairness"
];

export const dimensions = [
  {
    id: "economic",
    label: "Economic",
    color: "#b89b62",
    icon: "",
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
    label: "Energy",
    color: "#3e7b48",
    icon: "",
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
    label: "Environmental",
    color: "#3d5e80",
    icon: "",
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
    label: "Social",
    color: "#8a7799",
    icon: "",
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
