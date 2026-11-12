
export const initialScenarios = [
  {
    id: "scenario-a",
    label: "Scenario A",
    code: "SIM-A",
    color: "#3e7b48",
    marker: "●"
  },
  {
    id: "scenario-b",
    label: "Scenario B",
    code: "SIM-B",
    color: "#b89b62",
    marker: "■"
  },
  {
    id: "scenario-c",
    label: "Scenario C",
    code: "SIM-C",
    color: "#8b744b",
    marker: "◆"
  }
];

export const scenarioOptions = [
  { label: "Scenario A", code: "SIM-A" },
  { label: "Scenario B", code: "SIM-B" },
  { label: "Scenario C", code: "SIM-C" }
];

export const defaultSelectedIndicators = [
  "monthlySaving",
  "billReduction",
  "selfSufficiency",
  "gridDependency",
  "avoidedEmissions",
  "fairness"
];

export const dimensions = [
  {
    id: "economic",
    label: "Economic",
    color: "#b89b62",
    icon: "▣",
    indicators: [
      {
        id: "monthlySaving",
        label: "Monthly savings per participant (€)",
        direction: "higher",
        values: [28.5, 34.2, 31.8]
      },
      {
        id: "finalBill",
        label: "Final monthly bill (€)",
        direction: "lower",
        values: [null, null, null]
      },
      {
        id: "billReduction",
        label: "Bill reduction (%)",
        direction: "higher",
        values: [24, 29, 27]
      },
      {
        id: "annualProfit",
        label: "Annual investment return (%)",
        direction: "higher",
        values: [null, null, null]
      },
      {
        id: "investmentPayback",
        label: "Investment payback period (years)",
        direction: "lower",
        values: [null, null, null]
      }
    ]
  },
  {
    id: "energy",
    label: "Energy",
    color: "#3e7b48",
    icon: "ϟ",
    indicators: [
      {
        id: "selfSufficiency",
        label: "Community energy self-sufficiency (%)",
        direction: "higher",
        values: [62, 71, 68]
      },
      {
        id: "selfConsumption",
        label: "Community self-consumption (%)",
        direction: "higher",
        values: [null, null, null]
      },
      {
        id: "gridDependency",
        label: "Grid dependency (%)",
        direction: "lower",
        values: [38, 29, 32]
      },
      {
        id: "selfSufficiencyGap",
        label: "Self-sufficiency gap between participants",
        direction: "lower",
        values: [null, null, null]
      }
    ]
  },
  {
    id: "environmental",
    label: "Environmental",
    color: "#3d5e80",
    icon: "◈",
    indicators: [
      {
        id: "avoidedEmissions",
        label: "Annual avoided emissions (kg CO₂ eq)",
        direction: "higher",
        values: [8400, 10200, 9600]
      },
      {
        id: "environmentalImpact",
        label: "Environmental impact · No data",
        direction: "none",
        values: [null, null, null]
      },
      {
        id: "carbonPayback",
        label: "Carbon debt payback period (years)",
        direction: "lower",
        values: [null, null, null]
      }
    ]
  },
  {
    id: "social",
    label: "Social",
    color: "#8a7799",
    icon: "♙",
    indicators: [
      {
        id: "fairness",
        label: "Fairness index",
        direction: "closestOne",
        values: [0.94, 0.89, 0.97]
      },
      {
        id: "benefitDifference",
        label: "Self-sufficiency gap between participants",
        direction: "lower",
        values: [null, null, null]
      }
    ]
  }
];
