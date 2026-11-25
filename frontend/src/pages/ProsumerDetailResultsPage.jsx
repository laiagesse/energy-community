import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import DonutChart from "../components/DonutChart";
import IndicatorCard from "../components/IndicatorCard";
import { formatKpiValue } from "../utils/formatKpi";
import { api } from "../api/api";

const colors = {
  green: "#3e7b48",
  red: "#a8433a",
  blue: "#3d5e80",
  ochre: "#b89b62",
  purple: "#8a7799"
};

const EXTRA_INDICATORS = {
  energy: [
    {
      key: "netP2p",
      title: "Net P2P balance",
      description: "Energy shared with the community minus energy received",
      info: "Positive values mean more energy was shared than received; negative values mean more was received."
    },
    {
      key: "p2pParticipation",
      title: "P2P participation",
      description: "Total energy exchanged with the community",
      info: "Energy shared with and received from other prosumers."
    },
    {
      key: "sharedEnergy",
      title: "Shared energy balance",
      description: "Grid purchases minus energy exported",
      info: "Shows the balance between electricity purchased from the grid and energy exported."
    },
    {
      key: "p2pDeficit",
      title: "P2P coverage of energy deficit",
      description: "Share of energy deficit covered by P2P exchanges",
      info: "P2P energy received as a share of the total energy deficit."
    }
  ],
  economic: [
    { key: "profitPv", title: "PV return", description: "Return on photovoltaic investment", info: "Photovoltaic profit divided by photovoltaic investment.", signed: true },
    { key: "profitWt", title: "Wind return", description: "Return on wind investment", info: "Wind profit divided by wind investment.", signed: true },
    { key: "profitBattery", title: "Battery return", description: "Return on battery investment", info: "Battery profit divided by battery investment.", signed: true },
    { key: "paybackPv", title: "PV payback time", description: "Estimated time to recover photovoltaic investment", info: "Photovoltaic investment divided by photovoltaic profit." },
    { key: "paybackWt", title: "Wind payback time", description: "Estimated time to recover wind investment", info: "Wind investment divided by wind profit." },
    { key: "paybackBattery", title: "Battery payback time", description: "Estimated time to recover battery investment", info: "Battery investment divided by battery profit." }
  ],
  social: [
    {
      key: "billReduction",
      title: "Bill reduction",
      description: "Reduction compared with buying all consumed electricity from the grid",
      info: "Difference between the estimated grid-only bill and the final bill with community participation."
    },
    {
      key: "gainAppropriation",
      title: "Community gains share",
      description: "Share of total community revenue",
      info: "This prosumer's share of the community's total net revenue."
    },
    {
      key: "savingsAppropriation",
      title: "Community savings share",
      description: "Share of total community savings",
      info: "This prosumer's share of the community's total savings."
    },
    {
      key: "investmentContribution",
      title: "Investment contribution",
      description: "Share of total community investment",
      info: "This prosumer's share of the community's total investment."
    }
  ],
  environmental: [
    {
      key: "carbonDebt",
      title: "Upfront carbon debt",
      description: "Emissions associated with installed equipment",
      info: "Initial emissions from the equipment allocated to this prosumer."
    },
    {
      key: "pvPayback",
      title: "PV carbon payback",
      description: "Time for PV emissions savings to offset installation emissions",
      info: "Photovoltaic upfront emissions divided by emissions avoided through PV generation."
    },
    {
      key: "wtPayback",
      title: "Wind carbon payback",
      description: "Time for wind emissions savings to offset installation emissions",
      info: "Wind upfront emissions divided by emissions avoided through wind generation."
    },
    {
      key: "batteryPayback",
      title: "Battery carbon payback",
      description: "Time for battery emissions savings to offset installation emissions",
      info: "Battery upfront emissions divided by emissions avoided through battery operation."
    }
  ]
};

function getIndicatorTone(value, {
  direction = "higher",
  neutralAt = 0,
  precision = 1
} = {}) {
  if (!Number.isFinite(value)) return "neutral";

  const difference = Number((value - neutralAt).toFixed(precision));
  if (difference === 0) return "neutral";

  const isPositive = direction === "higher" ? difference > 0 : difference < 0;
  return isPositive ? "positive" : "negative";
}

function getCoverageShares(own, grid) {
  const ownPercent = Math.max(0, own * 100);
  const gridPercent = Math.max(0, grid * 100);
  const p2pPercent = Math.max(0, 100 - ownPercent - gridPercent);
  const total = ownPercent + gridPercent + p2pPercent;

  return total > 0
    ? {
      own: ownPercent / total * 100,
      grid: gridPercent / total * 100,
      p2p: p2pPercent / total * 100
    }
    : { own: 0, grid: 0, p2p: 0 };
}

function ExtraIndicatorCards({ indicators, kpis, period }) {
  return (
    <div className="prosumer-extra-card-grid">
      {indicators.map(indicator => {
        const value = kpis[indicator.key]?.value ?? null;
        const tone = indicator.signed
          ? getIndicatorTone(value, { precision: 1 })
          : "neutral";

        return (
          <IndicatorCard
            key={indicator.key}
            title={indicator.title}
            description={indicator.description}
            value={formatKpiValue(value, indicator.key, period)}
            valueTone={tone}
            info={indicator.info}
          />
        );
      })}
    </div>
  );
}

function Legend({ items }) {
  return (
    <div className="chart-legend">
      {items.map(item => (
        <div key={item.label}>
          <i style={{ background: item.color }} />
          <span>{item.label}</span>
          {item.value && <strong>{item.value}</strong>}
        </div>
      ))}
    </div>
  );
}

export default function ProsumerDetailResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const simulationFromUrl = searchParams.get("simulation");
  const prosumerFromUrl = searchParams.get("prosumer") ?? "";
  const [simulationId, setSimulationId] = useState(simulationFromUrl || "");
  const [experiments, setExperiments] = useState([]);
  const [alternative, setAlternative] = useState("");
  const [period, setPeriod] = useState("");
  const [selectedProsumer, setSelectedProsumer] = useState(prosumerFromUrl);
  const [selectedCoveragePeriodId, setSelectedCoveragePeriodId] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Keep the selector in sync when this page is opened from the prosumer table.
  useEffect(() => {
    setSelectedProsumer(prosumerFromUrl);
  }, [prosumerFromUrl]);

  useEffect(() => {
    let active = true;
    async function loadExperiments() {
      setLoading(true);
      setError(null);
      try {
        let selectedSimulation = simulationFromUrl;
        if (!selectedSimulation) {
          setSimulationId("");
          setExperiments([]);
          setAlternative("");
          setError("No hi ha cap simulació seleccionada.");
          setLoading(false);
          return;
        }
        const result = await api.getExperiments(selectedSimulation);
        if (!active) return;
        setSimulationId(selectedSimulation);
        setExperiments(result.experiments ?? []);
        setAlternative(current => result.experiments?.some(item => item.id === current)
          ? current : result.experiments?.[0]?.id ?? "");
      } catch (err) {
        if (active) { setError(err.message); setLoading(false); }
      }
    }
    loadExperiments();
    return () => { active = false; };
  }, [simulationFromUrl]);

  useEffect(() => {
    if (!simulationId || !alternative) return;
    let active = true;
    async function loadResults() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getProsumerKpis(simulationId, alternative);
        if (!active) return;
        setData(result);
        const available = result.periods ?? [];
        setPeriod(current => available.some(item => item.id === current)
          ? current
          : available.find(item => item.id === "annual")?.id ?? available[0]?.id ?? "");
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    }
    loadResults();
    return () => { active = false; };
  }, [simulationId, alternative]);

  const periods = useMemo(() => (data?.periods ?? [])
    .map(item => ({ id: item.id, label: item.label })), [data]);
  const selectedPeriod = data?.periods?.find(item => item.id === period);
  const prosumers = selectedPeriod?.prosumers ?? {};
  const prosumerIds = Object.keys(prosumers).sort((a, b) => a.localeCompare(b));
  const prosumerKpis = selectedProsumer ? prosumers[selectedProsumer] : null;
  const resultPeriods = data?.periods ?? [];
  const periodType = data?.period_type ?? "month";
  const selectedPeriodLabel = selectedPeriod?.label ?? "";
  const periodReference = period === "annual"
    ? "the year"
    : selectedPeriodLabel || "the selected period";
  const kpis = prosumerKpis ?? {};
  const value = key => kpis[key]?.value ?? null;
  const totalLoad = value("totalLoad");
  const totalEnergySurplus = value("energySurplus");
  const energyShares = getCoverageShares(value("selfSufficiency") ?? 0, value("gridDependency") ?? 0);
  const p2pSurplusPercent = value("p2pSurplus") == null ? null : value("p2pSurplus") * 100;
  const otherSurplusPercent = p2pSurplusPercent == null ? null : 100 - p2pSurplusPercent;
  const baselineBill = Number.isFinite(value("finalBill")) && Number.isFinite(value("saved"))
    ? value("finalBill") + value("saved")
    : null;
  const savingsPercent = baselineBill > 0 ? value("saved") / baselineBill * 100 : null;
  const savingsTone = getIndicatorTone(savingsPercent, { precision: 1 });
  const emissionsReductionPercent = value("environmentalImpact") == null
    ? null
    : (1 - value("environmentalImpact")) * 100;
  const emissionsReductionTone = getIndicatorTone(emissionsReductionPercent, { precision: 0 });
  const displayPeriods = resultPeriods.filter(item => item.id !== "annual");
  const coverageData = displayPeriods.map(item => {
    const itemKpis = item.prosumers?.[selectedProsumer] ?? {};
    const own = itemKpis.selfSufficiency?.value ?? 0;
    const grid = itemKpis.gridDependency?.value ?? 0;
    const shares = getCoverageShares(own, grid);
    const periodLoad = itemKpis.totalLoad?.value ?? null;

    return {
      id: item.id,
      label: item.label,
      totalLoad: periodLoad,
      ...shares,
      ownKwh: periodLoad == null ? null : periodLoad * shares.own / 100,
      gridKwh: periodLoad == null ? null : periodLoad * shares.grid / 100,
      p2pKwh: periodLoad == null ? null : periodLoad * shares.p2p / 100
    };
  });
  const maxTotalLoad = Math.max(0, ...coverageData.map(item => item.totalLoad ?? 0));
  const coverageTickSize = (() => {
    if (maxTotalLoad <= 0) return 1;
    const target = maxTotalLoad / 5;
    const magnitude = 10 ** Math.floor(Math.log10(target));
    const fraction = target / magnitude;
    const niceFraction = [1, 2, 2.5, 5, 10].find(step => step >= fraction) ?? 10;
    return niceFraction * magnitude;
  })();
  const coverageTickIntervals = maxTotalLoad > 0
    ? Math.ceil(maxTotalLoad / coverageTickSize)
    : 5;
  const chartScale = coverageTickSize * coverageTickIntervals;
  const coverageTickFractionDigits = coverageTickSize < 0.1
    ? 3
    : coverageTickSize < 1 ? 2 : 1;
  const coverageTicks = Array.from({ length: coverageTickIntervals + 1 }, (_, index) => ({
    value: coverageTickSize * index,
    position: 100 - index / coverageTickIntervals * 100
  }));
  const selectedCoverage = coverageData.find(item => item.id === selectedCoveragePeriodId)
    ?? coverageData[0];
  const monthlyBillRows = displayPeriods.map(item => {
    const itemKpis = item.prosumers?.[selectedProsumer] ?? {};
    const bill = itemKpis.finalBill?.value ?? null;
    const saved = itemKpis.saved?.value ?? null;

    return {
      label: item.label,
      withoutCommunity: bill != null && saved != null ? bill + saved : null,
      withCommunity: bill,
      saved
    };
  });
  const formatEuro = amount => amount == null
    ? "—"
    : `${amount.toLocaleString("en-GB", { maximumFractionDigits: 0 })} €`;
  const scrollTo = id => document.getElementById(id)?.scrollIntoView({
    behavior: "smooth",
    block: "start"
  });

  const handleProsumerChange = value => {
    setSelectedProsumer(value);
    const next = new URLSearchParams(searchParams);
    if (value) next.set("prosumer", value);
    else next.delete("prosumer");
    if (simulationId) next.set("simulation", simulationId);
    setSearchParams(next, { replace: true });
  };

  if (loading && !data) return <main className="page-width results-page"><p>Loading prosumer details...</p></main>;
  if (error) return <main className="page-width results-page"><p className="results-error" role="alert">{error}</p></main>;

  return (
    <main className="page-width results-page prosumer-detail-results-page">
      <ResultsPageHeader
        simulationId={simulationId}
        experiments={experiments}
        period={period}
        onPeriodChange={setPeriod}
        alternative={alternative}
        onAlternativeChange={setAlternative}
        periods={periods}
      />
      <ResultsTabs />
      <div className="results-heading prosumer-detail-heading">
        <div className="results-title-block">
          <h1>{selectedProsumer || "Select a prosumer to view its individual results."}</h1>
        </div>
        <div className="results-actions">
          <select
            id="prosumer-detail-selector"
            value={selectedProsumer}
            onChange={event => handleProsumerChange(event.target.value)}
            disabled={!prosumerIds.length}
            aria-label="Select a prosumer"
          >
            <option value="">Select a prosumer...</option>
            {prosumerIds.map(id => <option value={id} key={id}>{id}</option>)}
          </select>
        </div>
      </div>
      {prosumerKpis && (
        <div className="jump-links">
          <span>Go to</span>
          {[
            { label: "Energy", id: "energy", color: colors.green },
            { label: "Economics", id: "economics", color: colors.ochre },
            { label: "Social", id: "social", color: colors.purple },
            { label: "Environmental", id: "environmental", color: colors.blue }
          ].map(section => (
            <button
              key={section.id}
              type="button"
              style={{ "--section-color": section.color }}
              onClick={() => scrollTo(section.id)}
            >{section.label}</button>
          ))}
        </div>
      )}
      {selectedProsumer && !prosumerKpis && (
        <p className="results-error">No results were found for prosumer “{selectedProsumer}” in this period.</p>
      )}
      {prosumerKpis && (
        <>
          <section className="summary-grid">
            <IndicatorCard
              title="Total saved"
              description={`${period === "annual" ? "Annual" : selectedPeriodLabel} savings from community participation`}
              value={formatKpiValue(value("saved"), "saved", period)}
              valueTone={getIndicatorTone(value("saved"), { precision: 0 })}
              className="summary-card"
              info="Savings compared with purchasing all consumed electricity from the grid."
            />
            <IndicatorCard
              title="Self-sufficiency"
              description="Your demand covered by your own resources"
              value={formatKpiValue(value("selfSufficiency"), "selfSufficiency", period)}
              valueTone={getIndicatorTone(value("selfSufficiency") == null
                ? null
                : value("selfSufficiency") * 100, { neutralAt: 50, precision: 1 })}
              className="summary-card"
              info="Share of your electricity demand covered by your own generation, either directly or through battery storage."
            />
            <IndicatorCard
              title="Bill reduction"
              description="Reduction compared with grid-only electricity costs"
              value={formatKpiValue(value("billReduction"), "billReduction", period)}
              valueTone={getIndicatorTone(value("billReduction") == null
                ? null
                : value("billReduction") * 100, { precision: 1 })}
              className="summary-card"
              info="Difference between the estimated cost of buying all your electricity from the grid and your final bill."
            />
            <IndicatorCard
              title="Avoided emissions"
              description={period === "annual"
                ? "Net annual CO₂-equivalent reduction"
                : `Net CO₂-equivalent reduction in ${selectedPeriodLabel || "the selected period"}`}
              value={formatKpiValue(value("avoidedEmissions"), "avoidedEmissions", period)}
              valueTone={getIndicatorTone(value("avoidedEmissions"), { precision: 0 })}
              className="summary-card"
              info="Net emissions avoided after accounting for your grid imports and the emissions associated with your equipment."
            />
          </section>

          <section id="energy" className="result-section">
            <SectionHeading title="Energy" color={colors.green} />
            <div className="energy-cards">
              <IndicatorCard
                title="Your electricity consumption"
                description={`${selectedPeriodLabel} demand covered by each energy source`}
                info="Shows how your electricity demand is met by your own resources, grid imports and P2P energy received."
              >
                <div className="donut-card-content">
                  <DonutChart
                    totalConsumption={totalLoad != null ? totalLoad.toFixed(1) : "—"}
                    label="TOTAL kWh"
                    segments={[
                      {
                        label: "Own resources",
                        value: energyShares.own,
                        quantity: totalLoad != null ? (totalLoad * energyShares.own / 100).toFixed(1) : "—",
                        color: colors.green
                      },
                      {
                        label: "Grid",
                        value: energyShares.grid,
                        quantity: totalLoad != null ? (totalLoad * energyShares.grid / 100).toFixed(1) : "—",
                        color: colors.red
                      },
                      {
                        label: "P2P exchange",
                        value: energyShares.p2p,
                        quantity: totalLoad != null ? (totalLoad * energyShares.p2p / 100).toFixed(1) : "—",
                        color: colors.blue
                      }
                    ]}
                  />
                  <Legend items={[
                    { label: "Own resources", value: `${energyShares.own.toFixed(1)} %`, color: colors.green },
                    { label: "Grid", value: `${energyShares.grid.toFixed(1)} %`, color: colors.red },
                    { label: "P2P exchange", value: `${energyShares.p2p.toFixed(1)} %`, color: colors.blue }
                  ]} />
                </div>
              </IndicatorCard>

              <IndicatorCard
                title="Direct self-consumption"
                description="Your generation consumed directly"
                value={formatKpiValue(value("selfConsumption"), "selfConsumption", period)}
                valueTone={getIndicatorTone(value("selfConsumption") == null
                  ? null
                  : value("selfConsumption") * 100, { neutralAt: 50, precision: 1 })}
                className="direct-self-consumption-card"
                info="Share of your generated energy consumed directly, without battery storage. Higher values mean more of your generation is used immediately."
              >
                <div className="meter">
                  <span style={{
                    width: value("selfConsumption") != null
                      ? `${Math.max(0, Math.min(100, value("selfConsumption") * 100))}%`
                      : "0%"
                  }} />
                </div>
              </IndicatorCard>

              <IndicatorCard
                title="Your surplus distribution"
                description="Distribution of your excess generated electricity"
                info="Shows how your surplus electricity is divided between P2P exchanges and exports to the grid."
              >
                <div className="donut-card-content">
                  <DonutChart
                    totalConsumption={totalEnergySurplus != null ? totalEnergySurplus.toFixed(1) : "—"}
                    label="SURPLUS kWh"
                    segments={[
                      {
                        label: "P2P exchange",
                        value: p2pSurplusPercent ?? 0,
                        quantity: totalEnergySurplus != null && p2pSurplusPercent != null
                          ? (totalEnergySurplus * p2pSurplusPercent / 100).toFixed(1)
                          : "—",
                        color: colors.blue
                      },
                      {
                        label: "Grid export",
                        value: otherSurplusPercent ?? 0,
                        quantity: totalEnergySurplus != null && otherSurplusPercent != null
                          ? (totalEnergySurplus * otherSurplusPercent / 100).toFixed(1)
                          : "—",
                        color: colors.red
                      }
                    ]}
                  />
                  <Legend items={[
                    {
                      label: "P2P exchange",
                      value: p2pSurplusPercent != null ? `${p2pSurplusPercent.toFixed(1)} %` : "—",
                      color: colors.blue
                    },
                    {
                      label: "Grid export",
                      value: otherSurplusPercent != null ? `${otherSurplusPercent.toFixed(1)} %` : "—",
                      color: colors.red
                    }
                  ]} />
                </div>
              </IndicatorCard>
            </div>

            <ExtraIndicatorCards
              indicators={EXTRA_INDICATORS.energy}
              kpis={kpis}
              period={period}
            />

            {period === "annual" && (
              <IndicatorCard
                title={`${periodType === "season" ? "Seasonal" : "Monthly"} consumption coverage`}
                description="Share of your demand covered by each energy source in every period"
                className="chart-card"
                info="Bar height shows your total demand in each period; segments show the share met by your own resources, grid imports and P2P. Hover for kWh and percentages; click a period to see total consumption."
              >
                <div className="chart-heading">
                  <Legend items={[
                    { label: "Own resources", color: colors.green },
                    { label: "Grid", color: colors.red },
                    { label: "P2P exchange", color: colors.blue }
                  ]} />
                </div>
                <div className="coverage-chart-layout" role="group" aria-label="Prosumer consumption coverage by period">
                  <div className="coverage-y-axis-title">Total demand (kWh)</div>
                  <div className="coverage-y-axis" aria-label="Total prosumer load in kilowatt-hours">
                    {coverageTicks.map(tick => (
                      <span className="coverage-y-tick" key={tick.position} style={{ top: `${tick.position}%` }}>
                        {coverageData.some(item => item.totalLoad != null)
                          ? tick.value.toLocaleString("en-GB", { maximumFractionDigits: coverageTickFractionDigits })
                          : "—"} kWh
                      </span>
                    ))}
                  </div>
                  <div className="coverage-chart-main">
                    <div className="coverage-plot">
                      <div className="coverage-gridlines" aria-hidden="true">
                        {coverageTicks.map(tick => (
                          <span className="coverage-gridline" key={tick.position} style={{ top: `${tick.position}%` }} />
                        ))}
                      </div>
                      {coverageData.map(item => {
                        const segments = [
                          { label: "Own resources", value: item.own, quantity: item.ownKwh, color: colors.green },
                          { label: "Grid", value: item.grid, quantity: item.gridKwh, color: colors.red },
                          { label: "P2P exchange", value: item.p2p, quantity: item.p2pKwh, color: colors.blue }
                        ];
                        const barHeight = item.totalLoad != null
                          ? Math.max(0, item.totalLoad / chartScale * 100)
                          : 0;

                        return (
                          <div
                            className={`stack-column${selectedCoverage?.id === item.id ? " is-selected" : ""}`}
                            key={item.id}
                            role="button"
                            tabIndex={0}
                            aria-pressed={selectedCoverage?.id === item.id}
                            aria-label={`Select ${item.label}; total consumption ${item.totalLoad != null ? item.totalLoad.toFixed(1) : "unavailable"} kWh`}
                            onClick={() => setSelectedCoveragePeriodId(item.id)}
                            onKeyDown={event => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                setSelectedCoveragePeriodId(item.id);
                              }
                            }}
                          >
                            <div className="stack-bars" style={{ height: `${barHeight}%` }}>
                              {segments.map(segment => (
                                <i
                                  key={segment.label}
                                  title={`${segment.label}: ${segment.value.toFixed(1)}% · ${segment.quantity != null ? `${segment.quantity.toFixed(1)} kWh` : "—"}`}
                                  style={{ height: `${segment.value}%`, background: segment.color }}
                                />
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div
                      className="coverage-period-labels"
                      style={{ gridTemplateColumns: `repeat(${Math.max(coverageData.length, 1)}, minmax(0, 1fr))` }}
                    >
                      {coverageData.map(item => (
                        <span
                          className={selectedCoverage?.id === item.id ? "is-selected" : ""}
                          key={item.id}
                          title={item.label}
                        >
                          {periodType === "month" ? item.label.slice(0, 3) : item.label}
                        </span>
                      ))}
                    </div>
                    <div className="coverage-x-axis-title">Period</div>
                  </div>
                </div>
                {selectedCoverage && (
                  <p className="coverage-selected-total" role="status">
                    Total energy consumed in {selectedCoverage.label}:{" "}
                    <strong>
                      {selectedCoverage.totalLoad != null
                        ? selectedCoverage.totalLoad.toLocaleString("en-GB", { maximumFractionDigits: 1 })
                        : "—"} kWh
                    </strong>
                  </p>
                )}
              </IndicatorCard>
            )}
          </section>

          <section id="economics" className="result-section">
            <SectionHeading title="Economics" color={colors.ochre} />
            <div className="economics-summary-grid">
              <IndicatorCard
                title="Your final electricity bill"
                description={period === "annual"
                  ? "Your total net electricity cost over the year"
                  : `Your total net electricity cost in ${selectedPeriodLabel || "the selected period"}`}
                value={formatKpiValue(value("finalBill"), "finalBill", period)}
                valueTone={savingsTone}
                className="bill-comparison-card"
                info="Your net electricity cost after accounting for grid and P2P purchases and revenue from energy sold."
              >
                {savingsPercent != null && (
                  <div className="bill-savings-section">
                    <hr />
                    <strong className={`bill-savings-result is-${savingsTone}`}>
                      {savingsTone === "neutral"
                        ? "About the same as buying all electricity from the grid"
                        : `${Math.abs(savingsPercent).toFixed(1)}% ${value("saved") < 0 ? "higher" : "lower"} than without the community`}
                    </strong>
                  </div>
                )}
              </IndicatorCard>
              <IndicatorCard
                title="Savings from community participation"
                description={`${period === "annual" ? "Annual" : selectedPeriodLabel} savings compared with grid-only electricity`}
                value={formatKpiValue(value("saved"), "saved", period)}
                valueTone={getIndicatorTone(value("saved"), { precision: 0 })}
                info="Savings achieved compared with purchasing all your consumed electricity from the grid."
              />
            </div>

            {period === "annual" && (
              <IndicatorCard
                title={`${periodType === "season" ? "Seasonal" : "Monthly"} electricity bill comparison`}
                description="Your estimated electricity costs with and without the community across each period."
                className="table-card"
                info="Compares the estimated grid-only cost with your final bill under the community energy-sharing model."
              >
                <div className="table-scroll">
                  <table className="results-table">
                    <thead>
                      <tr>
                        <th>{periodType === "season" ? "Season" : "Month"}</th>
                        <th>Bill without community</th>
                        <th>Bill with community</th>
                        <th>Saved</th>
                      </tr>
                    </thead>
                    <tbody>
                      {monthlyBillRows.map(row => (
                        <tr key={row.label}>
                          <td>{row.label}</td>
                          <td>{formatEuro(row.withoutCommunity)}</td>
                          <td>{formatEuro(row.withCommunity)}</td>
                          <td className="saving-cell">{formatEuro(row.saved)}</td>
                        </tr>
                      ))}
                      <tr className="total-row">
                        <td>Annual total</td>
                        <td>{formatEuro(value("finalBill") != null && value("saved") != null
                          ? value("finalBill") + value("saved")
                          : null)}</td>
                        <td>{formatEuro(value("finalBill"))}</td>
                        <td className="saving-cell">{formatEuro(value("saved"))}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </IndicatorCard>
            )}

            <div className="economics-subsection">
              <div className="economics-subsection-heading">
                <h3>Return on investment</h3>
                <p>Investment performance and estimated time to recover your investment.</p>
              </div>
              <div className="economics-summary-grid roi-summary-grid">
                <IndicatorCard
                  title="Total invested"
                  description="Investment in your share of community energy assets"
                  value={formatKpiValue(value("totalInvested"), "totalInvested", period)}
                  info="Upfront cost of generation and battery capacity allocated to you."
                />
                <IndicatorCard
                  title="Your profit (ROI)"
                  description={`Return on your investment for ${periodReference}`}
                  value={formatKpiValue(value("annualProfit"), "annualProfit", period)}
                  valueTone={getIndicatorTone(value("annualProfit") == null
                    ? null
                    : value("annualProfit") * 100, { precision: 1 })}
                  info="Your profit for the selected period divided by your total investment."
                />
                <IndicatorCard
                  title="Your payback time"
                  description="Estimated time to recover your investment"
                  value={formatKpiValue(value("payback"), "payback", period)}
                  info="Your total investment divided by the profit generated over the selected period."
                />
              </div>
            </div>
          </section>

          <section id="social" className="result-section">
            <SectionHeading title="Social" color={colors.purple} />
            <ExtraIndicatorCards
              indicators={EXTRA_INDICATORS.social}
              kpis={kpis}
              period={period}
            />
          </section>

          <section id="environmental" className="result-section">
            <SectionHeading title="Environmental" color={colors.blue} />
            <div className="two-cards">
              <IndicatorCard
                title="Avoided emissions"
                description={period === "annual"
                  ? "Net annual CO₂-equivalent reduction"
                  : `Net CO₂-equivalent reduction in ${selectedPeriodLabel || "the selected period"}`}
                className="emissions-card"
                value={formatKpiValue(value("avoidedEmissions"), "avoidedEmissions", period)}
                valueTone={getIndicatorTone(value("avoidedEmissions"), { precision: 0 })}
                info="Net emissions avoided after accounting for your grid imports and the emissions associated with your equipment."
              >
                <div className="emissions-explainer">
                  <strong className={`indicator-value-${emissionsReductionTone}`}>
                    {emissionsReductionPercent != null
                      ? `${emissionsReductionPercent.toFixed(0)}% fewer emissions than without the community.`
                      : "—"}
                  </strong>
                  <p>
                    {value("environmentalImpact") != null
                      ? `Equivalent to ${(value("environmentalImpact") * 100).toFixed(0)}% of the emissions from buying all your electricity from the grid.`
                      : "—"}
                  </p>
                </div>
              </IndicatorCard>
              <IndicatorCard
                title="Carbon payback time"
                description="Time for your carbon savings to offset installation emissions"
                value={formatKpiValue(value("carbonPayback"), "carbonPayback", period)}
                info="Estimates how long it takes for your avoided emissions to offset the initial emissions from your equipment."
              />
            </div>
          </section>
        </>
      )}
    </main>
  );
}
