import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import DonutChart from "../components/DonutChart";
import IndicatorCard from "../components/IndicatorCard";
import { api } from "../api/api";

const MONTH_ORDER = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];

const colors = {
  green: "#3e7b48",
  red: "#a8433a",
  blue: "#3d5e80",
  ochre: "#b89b62",
  purple: "#8a7799"
};


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

export default function CommunityResultsPage() {
  const [searchParams] = useSearchParams();
  const simulationId = searchParams.get("simulation") || "";
  const [period, setPeriod] = useState("");
  const [alternative, setAlternative] = useState("");
  const [experiments, setExperiments] = useState([]);
  const [loadingExperiments, setLoadingExperiments] = useState(true);
  const [communityData, setCommunityData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoveredCoverage, setHoveredCoverage] = useState(null);
  const [selectedCoveragePeriodId, setSelectedCoveragePeriodId] = useState(null);
  const [billSort, setBillSort] = useState({ key: null, direction: "asc" });
  const [coverageMousePosition, setCoverageMousePosition] = useState({
    x: 0,
    y: 0
  });

  // Load the available experiments for the selector.
  useEffect(() => {
    let cancelled = false;

    const fetchExperiments = async () => {
      if (!simulationId) {
        setExperiments([]);
        setAlternative("");
        setLoadingExperiments(false);
        setLoading(false);
        setError("No hi ha cap simulació seleccionada.");
        return;
      }
      try {
        const data = await api.getExperiments(simulationId);
        if (cancelled) return;

        const availableExperiments = data.experiments ?? [];
        setExperiments(availableExperiments);
        setAlternative(availableExperiments[0]?.id || "");
        setLoadingExperiments(false);

        if (availableExperiments.length === 0) {
          setLoading(false);
          setError("No experiments are available.");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
          setLoadingExperiments(false);
        }
      }
    };

    fetchExperiments();
    return () => {
      cancelled = true;
    };
  }, [simulationId]);

  // Load the community KPIs whenever the selected experiment changes.
  useEffect(() => {
    if (!alternative) return;

    let cancelled = false;

    const fetchCommunityResults = async () => {
      setLoading(true);
      setError(null);
      setCommunityData(null);

      try {
        const data = await api.getCommunityKpis(simulationId, alternative);
        if (!cancelled) {
          setCommunityData(data);
          if (data.periods?.length) {
            setPeriod(current =>
              data.periods.some(item => item.id === current)
                ? current
                : data.periods.find(item => item.id === "annual")?.id
                  ?? data.periods[0].id
            );
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchCommunityResults();
    return () => {
      cancelled = true;
    };
  }, [alternative, simulationId]);

  const periodType = communityData?.period_type ?? null;
  const periods = communityData?.periods ?? [];
  const selectedPeriodData = periods.find(
    item => item.id === period
  );
  const selectedPeriodLabel = selectedPeriodData?.label ?? "";
  const periodReference = period === "annual"
    ? "the year"
    : selectedPeriodLabel || "the selected period";
  const periodDisplayLabel = period === "annual"
    ? "Annual"
    : selectedPeriodLabel || "Selected-period";
  const paybackUnit = period === "annual"
    ? "years"
    : periodType === "season"
      ? "seasons"
      : "months";
  const kpis = selectedPeriodData?.kpis ?? {};

  const scrollTo = id => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });


  const ownResources = (kpis.selfSufficiency?.value ?? 0) * 100;
  const grid = (kpis.gridDependency?.value ?? 0) * 100;
  const p2p = 100 - ownResources - grid;
  const totalLoad = kpis.totalLoad?.value;
  const totalEnergySurplus = kpis.energySurplus?.value;
  const p2pSurplus = kpis.p2pSurplus?.value;
  const communityFinalBill = kpis.totalFinalBill?.value;
  const communitySaved = kpis.totalSaved?.value;
  const billWithoutCommunity = Number.isFinite(communityFinalBill)
    && Number.isFinite(communitySaved)
    ? communityFinalBill + communitySaved
    : null;
  const communitySavingsPercent = billWithoutCommunity > 0
    ? communitySaved / billWithoutCommunity * 100
    : null;
  const emissionsReductionPercent = kpis.environmentalImpact?.value != null
    ? (1 - kpis.environmentalImpact.value) * 100
    : null;
  const p2pSurplusPercent = p2pSurplus == null ? null : p2pSurplus * 100;
  const otherSurplusPercent = p2pSurplusPercent == null ? null : 100 - p2pSurplusPercent;
  const displayPeriods = periods.filter(item => item.id !== "annual");
  const coverageData = displayPeriods.map(item => {
    const kpis = item.kpis ?? {};

    const grid = (kpis.gridDependency?.value ?? 0) * 100;
    const own = (kpis.selfSufficiency?.value ?? 0) * 100;
    const p2p = 100 - grid - own;
    const totalLoad = kpis.totalLoad?.value;

    return {
      id: item.id,
      label: item.label,
      totalLoad,
      grid,
      own,
      p2p,
      gridKwh: totalLoad != null ? totalLoad * grid / 100 : null,
      ownKwh: totalLoad != null ? totalLoad * own / 100 : null,
      p2pKwh: totalLoad != null ? totalLoad * p2p / 100 : null
    };
  });
  const coverageTickCount = 5;
  const getNiceCoverageStep = value => {
    if (value <= 0) return 1;
    const magnitude = 10 ** Math.floor(Math.log10(value));
    const fraction = value / magnitude;
    const niceFraction = [1, 2, 2.5, 5, 10].find(step => step >= fraction) ?? 10;
    return niceFraction * magnitude;
  };
  const maxTotalLoad = Math.max(
    0,
    ...coverageData.map(item => item.totalLoad ?? 0)
  );
  const hasTotalLoad = coverageData.some(item => item.totalLoad != null);
  const coverageTickSize = getNiceCoverageStep(maxTotalLoad / coverageTickCount);
  const coverageTickIntervals = maxTotalLoad > 0
    ? Math.ceil(maxTotalLoad / coverageTickSize)
    : coverageTickCount;
  const chartScale = coverageTickSize * coverageTickIntervals;
  const coverageTickFractionDigits = coverageTickSize < 0.1
    ? 3
    : coverageTickSize < 1 ? 2 : 1;
  const coverageTicks = Array.from({ length: coverageTickIntervals + 1 }, (_, index) => ({
    value: coverageTickSize * index,
    position: 100 - index / coverageTickIntervals * 100
  }));
  const selectedCoverage = coverageData.find(
    item => item.id === selectedCoveragePeriodId
  );
  const billRows = displayPeriods
    .map(item => {
      const billWithCommunity = item.kpis?.totalFinalBill?.value;
      const saved = item.kpis?.totalSaved?.value;
      const billWithoutCommunity = billWithCommunity != null && saved != null
        ? billWithCommunity + saved
        : null;
      return [item.label, billWithoutCommunity, billWithCommunity ?? null, saved ?? null];
    })
    .filter(row => periodType !== "month" || MONTH_ORDER.includes(String(row[0]).trim().slice(0, 3).toLowerCase()));

  const monthIndex = label => MONTH_ORDER.indexOf(String(label).trim().slice(0, 3).toLowerCase());
  const sortedMonthlyBills = [...billRows].sort((a, b) => {
    let result = 0;
    if (billSort.key === null || billSort.key === 0) {
      if (periodType === "month") {
        result = monthIndex(a[0]) - monthIndex(b[0]);
      } else if (billSort.key === 0) {
        result = String(a[0]).localeCompare(String(b[0]), undefined, { numeric: true });
      }
    } else {
      const av = a[billSort.key];
      const bv = b[billSort.key];
      if (av == null || bv == null) {
        result = av == null ? (bv == null ? 0 : 1) : -1;
      } else {
        result = av - bv;
      }
    }

    return billSort.key === null || billSort.direction === "asc" ? result : -result;
  });
  const sumBillColumn = column => (
    billRows.length > 0 && billRows.every(row => Number.isFinite(row[column]))
      ? billRows.reduce((total, row) => total + row[column], 0)
      : null
  );
  const totalBillWithCommunity = sumBillColumn(2);
  const totalSaved = sumBillColumn(3);
  const totalBillWithoutCommunity = (
    totalBillWithCommunity != null && totalSaved != null
      ? totalBillWithCommunity + totalSaved
      : null
  );
  const hasFullYear = periodType === "month"
    && billRows.length === MONTH_ORDER.length
    && MONTH_ORDER.every(month => billRows.some(row => monthIndex(row[0]) === MONTH_ORDER.indexOf(month)));
  const billTotalLabel = hasFullYear ? "Annual total" : "Total for displayed periods";
  const formatEuro = value => value == null
    ? "—"
    : `${value.toLocaleString("en-GB", { maximumFractionDigits: 0 })} €`;

  const showCoverageTooltip = (event, item, segment) => {
    const column = event.currentTarget.closest(".stack-column");
    const rect = column.getBoundingClientRect();
    setHoveredCoverage({
      periodId: item.id,
      label: segment.label,
      value: segment.value,
      quantity: segment.quantity,
      color: segment.color
    });
    setCoverageMousePosition({
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    });
  };

  return (
    <main className="page-width results-page community-results-page">
      <ResultsPageHeader
        period={period}
        onPeriodChange={setPeriod}
        alternative={alternative}
        onAlternativeChange={setAlternative}
        experiments={experiments}
        loadingExperiments={loadingExperiments}
        simulationId={simulationId}
        periods={periods}
      /><ResultsTabs />

      {loading && <p className="results-status">Loading experiment results...</p>}
      {error && <p className="results-error" role="alert">{error}</p>}

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

      <section className="summary-grid">
        <IndicatorCard
          section="economics"
          title="Total saved"
          description={`${periodDisplayLabel} community savings`}
          value={kpis.totalSaved ? `${kpis.totalSaved.value.toFixed(0)} €` : "—"}
          className="summary-card"
          info="Savings achieved by the community compared with purchasing all consumed electricity from the grid."
        />

        <IndicatorCard
          section="energy"
          title="Self-sufficiency"
          description="Consumption covered by own resources"
          value={kpis.selfSufficiency ? `${(kpis.selfSufficiency.value * 100).toFixed(1)} %` : "—"}
          className="summary-card"
          info={
            <>
              <p>Total community demand covered by locally generated energy, either consumed directly or stored in batteries.</p>
              <p>Higher values mean less dependence on external electricity.</p>
            </>
          }
        />

        <IndicatorCard
          section="social"
          title="Fairness index"
          description="Savings distribution equity"
          value={kpis.fairness ? kpis.fairness.value.toFixed(3) : "—"}
          className="summary-card"
          info={
            <>
              <p>Compares members' savings per unit of generation.</p>
              <p>Values closer to 1 indicate a more even distribution, while lower values indicate greater differences.</p>
            </>
          }
        />

        <IndicatorCard
          section="environmental"
          title="Avoided emissions"
          description={period === "annual"
            ? "Net annual CO₂-eq reduction"
            : `Net CO₂-eq reduction in ${selectedPeriodLabel || "the selected period"}`}
          value={kpis.avoidedEmissions ? `${kpis.avoidedEmissions.value.toFixed(0)} kg` : "—"}
          className="summary-card"
          info={
            <>
              <p>Net CO₂-equivalent emissions avoided after accounting for grid imports and equipment emissions.</p>
            </>
          }
        />
      </section>

      <section id="energy" className="result-section">
        <SectionHeading title="Energy" color={colors.green} />
        <div className="energy-cards">
          <IndicatorCard
            section="energy"
            title="Community electricity consumption"
            description={`${selectedPeriodLabel} consumption coverage by energy source`}
            info={
              <>
                <p>Shows how total community electricity demand is covered by own resources, grid imports and P2P energy exchanges.</p>
              </>
            }
          >
            <div className="donut-card-content">
              <DonutChart
                totalConsumption={totalLoad != null ? totalLoad.toFixed(1) : "—"}
                label="TOTAL kWh"
                segments={[
                  {
                    label: "Own resources",
                    value: ownResources,
                    quantity: totalLoad != null ? (totalLoad * ownResources / 100).toFixed(1) : "—",
                    color: colors.green
                  },
                  {
                    label: "Grid",
                    value: grid,
                    quantity: totalLoad != null ? (totalLoad * grid / 100).toFixed(1) : "—",
                    color: colors.red
                  },
                  {
                    label: "P2P exchange",
                    value: p2p,
                    quantity: totalLoad != null ? (totalLoad * p2p / 100).toFixed(1) : "—",
                    color: colors.blue
                  }
                ]}
              />

              <Legend items={[
                {
                  label: "Own resources",
                  value: `${ownResources.toFixed(1)} %`,
                  color: colors.green
                },
                {
                  label: "Grid",
                  value: `${grid.toFixed(1)} %`,
                  color: colors.red
                },
                {
                  label: "P2P exchange",
                  value: `${p2p.toFixed(1)} %`,
                  color: colors.blue
                }
              ]} />
            </div>
          </IndicatorCard>

          <IndicatorCard
            section="energy"
            title="Community direct self-consumption"
            description="Generated energy consumed directly by its owners"
            className="direct-self-consumption-card"
            value={kpis.selfConsumption?.value != null
              ? `${(kpis.selfConsumption.value * 100).toFixed(1)} %`
              : "—"}
            info={
              <>
                <p>Share of community generation consumed directly, without battery storage.</p>
                <p>Higher values mean more generated energy is used locally.</p>
              </>
            }
          >
            <div className="meter"><span style={{ width: kpis.selfConsumption?.value != null
                ? `${(kpis.selfConsumption.value * 100).toFixed(1)}%`
                : "—"} } /></div>
          </IndicatorCard>

          <IndicatorCard
            section="energy"
            title="Community surplus distribution"
            description="Distribution of excess generated electricity"
            info="Shows how the community's surplus electricity is distributed between P2P energy exchanges and exports to the grid."
          >
          <div className="donut-card-content">
            <DonutChart
              totalConsumption={totalEnergySurplus != null ? totalEnergySurplus.toFixed(1) : "—"}
              label="SURPLUS kWh"
              segments={[
                {
                  label: "P2P exchange",
                  value: p2pSurplusPercent,
                  quantity: totalEnergySurplus != null
                    ? (totalEnergySurplus * p2pSurplus).toFixed(1)
                    : "—",
                  color: colors.blue
                },
                {
                  label: "Grid export",
                  value: otherSurplusPercent,
                  quantity: totalEnergySurplus != null
                    ? (totalEnergySurplus * (1 - p2pSurplus)).toFixed(1)
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
        {period === "annual" && (
          <IndicatorCard
            section="energy"
            title="Monthly consumption coverage"
            description="Share of community consumption covered by each energy source in every month"
            className="chart-card"
            info="Hover over a segment to see its share and energy. Click a period to view its total energy consumption."
          >
          <div className="chart-heading">
            <Legend items={[
              { label: "Own resources", color: colors.green },
              { label: "Grid", color: colors.red },
              { label: "P2P exchange", color: colors.blue }
            ]} />
          </div>
          <div className="coverage-chart-layout" role="group" aria-label="Consumption coverage by period">
            <div className="coverage-y-axis-title">Total demand (kWh)</div>
            <div className="coverage-y-axis" aria-label="Total load in kilowatt-hours">
              {coverageTicks.map(tick => (
                <span
                  className="coverage-y-tick"
                  key={tick.position}
                  style={{ top: `${tick.position}%` }}
                >
                  {hasTotalLoad
                    ? tick.value.toLocaleString("en-GB", {
                      maximumFractionDigits: coverageTickFractionDigits
                    })
                    : "—"} kWh
                </span>
              ))}
            </div>
            <div className="coverage-chart-main">
              <div className="coverage-plot">
                <div className="coverage-gridlines" aria-hidden="true">
                  {coverageTicks.map(tick => (
                    <span
                      className="coverage-gridline"
                      key={tick.position}
                      style={{ top: `${tick.position}%` }}
                    />
                  ))}
                </div>
                {coverageData.map(item => {
                  const segments = [
                    { label: "Own resources", value: item.own, quantity: item.ownKwh, color: colors.green },
                    { label: "Grid", value: item.grid, quantity: item.gridKwh, color: colors.red },
                    { label: "P2P exchange", value: item.p2p, quantity: item.p2pKwh, color: colors.blue }
                  ];
                  const isRightAligned = coverageData.findIndex(period => period.id === item.id)
                    >= coverageData.length / 2;
                  const barHeight = item.totalLoad != null
                    ? Math.max(0, item.totalLoad / chartScale * 100)
                    : 0;

                  return (
                    <div
                      className={`stack-column${hoveredCoverage?.periodId === item.id ? " is-hovered" : ""}${selectedCoveragePeriodId === item.id ? " is-selected" : ""}`}
                      key={item.id}
                      role="button"
                      tabIndex={0}
                      aria-pressed={selectedCoveragePeriodId === item.id}
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
                            style={{ height: `${segment.value}%`, background: segment.color }}
                            onMouseEnter={event => showCoverageTooltip(event, item, segment)}
                            onMouseMove={event => showCoverageTooltip(event, item, segment)}
                            onMouseLeave={() => setHoveredCoverage(null)}
                          />
                        ))}
                      </div>

                      {hoveredCoverage?.periodId === item.id && (
                        <div
                          className={`donut-tooltip coverage-tooltip${isRightAligned ? " is-right-aligned" : ""}`}
                          style={{
                            "--tooltip-color": hoveredCoverage.color,
                            left: isRightAligned ? "auto" : `${coverageMousePosition.x}px`,
                            right: isRightAligned ? ".75rem" : "auto",
                            top: `${coverageMousePosition.y}px`
                          }}
                        >
                          <strong>{hoveredCoverage.label}</strong>
                          <span>
                            {hoveredCoverage.value.toFixed(1)} % ·{" "}
                            {hoveredCoverage.quantity != null
                              ? `${hoveredCoverage.quantity.toFixed(1)} kWh`
                              : "—"}
                          </span>
                        </div>
                      )}
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
                    className={selectedCoveragePeriodId === item.id ? "is-selected" : ""}
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
                  ? selectedCoverage.totalLoad.toLocaleString("en-GB", {
                    maximumFractionDigits: 1
                  })
                  : "—"} kWh
              </strong>
            </p>
          )}

          </IndicatorCard>
        )}
      </section>

      <section id="economics" className="result-section">
        <SectionHeading title="Economics" color={colors.ochre}/>
        <div className="economics-summary-grid">
          <IndicatorCard
            section="economics"
            title="Community final electricity bill"
            className="bill-comparison-card"
            description={period === "annual"
              ? "Total net electricity cost for the community over the year"
              : `Total net electricity cost for the community in ${selectedPeriodLabel || "the selected period"}`}
            value={communityFinalBill != null
              ? `${communityFinalBill.toFixed(0)} €`
              : "—"}
            info="Community's net electricity cost accounting for grid and P2P electricity purchases minus revenue from electricity sold."
          >
            {communitySavingsPercent != null && (
              <div className="bill-savings-section">
                <hr />
                <strong className="bill-savings-result">
                  {Math.abs(communitySavingsPercent) < 0.05
                    ? "About the same as without the community"
                    : `${Math.abs(communitySavingsPercent).toFixed(1)}% ${communitySaved < 0 ? "higher" : "lower"} than without the community`}
                </strong>
              </div>
            )}
          </IndicatorCard>
          <IndicatorCard
            section="economics"
            title="Total saved"
            description={`${periodDisplayLabel} community savings`}
            value={kpis.totalSaved?.value != null
              ? `${kpis.totalSaved.value.toFixed(0)} €`
              : "—"}
            info="Savings achieved by the community compared with purchasing all consumed electricity from the grid."
          >
            <hr />
            <p className="card-description">Equivalent to the grid-only electricity costs for</p>
            <strong className="households-number">
              {kpis.baselinePovertyHelp?.value != null
                ? `${kpis.baselinePovertyHelp.value.toFixed(1)} average households`
                : "—"}
            </strong>
          </IndicatorCard>
        </div>


        {period === "annual" && (
          <IndicatorCard
            section="economics"
            title="Monthly electricity bill comparison"
            description="Comparison of electricity costs with and without the community across each month."
            className="table-card"
            info="Compares the estimated electricity costs without the community with the actual costs under the community energy-sharing model. The difference represents the savings achieved in each period."
          >
          <div className="table-scroll">
            <table className="results-table">
              <thead>
                <tr>
                  {[
                    [periodType === "month" ? "Month" : periodType === "season" ? "Season" : "Period", 0],
                    ["Bill without community", 1],
                    ["Bill with community", 2],
                    ["Saved", 3]
                  ].map(([label, key]) => (
                    <th key={key} aria-sort={billSort.key === key ? (billSort.direction === "asc" ? "ascending" : "descending") : "none"}>
                      <div className="table-sort-heading">
                        <span>{label}</span>
                        <span className="table-sort-triangles">
                          <button
                            type="button"
                            className={`table-sort-triangle${billSort.key === key && billSort.direction === "asc" ? " is-active" : ""}`}
                            aria-label="Sort from lowest to highest"
                            title="Sort from lowest to highest"
                            aria-pressed={billSort.key === key && billSort.direction === "asc"}
                            onClick={() => setBillSort({ key, direction: "asc" })}
                          >▲</button>
                          <button
                            type="button"
                            className={`table-sort-triangle${billSort.key === key && billSort.direction === "desc" ? " is-active" : ""}`}
                            aria-label="Sort from highest to lowest"
                            title="Sort from highest to lowest"
                            aria-pressed={billSort.key === key && billSort.direction === "desc"}
                            onClick={() => setBillSort({ key, direction: "desc" })}
                          >▼</button>
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedMonthlyBills.map((row, index) => (
                  <tr key={`${row[0]}-${index}`}>
                    <td>{row[0]}</td>
                    <td>{formatEuro(row[1])}</td>
                    <td>{formatEuro(row[2])}</td>
                    <td className="saving-cell">{formatEuro(row[3])}</td>
                  </tr>
                ))}
                <tr className="total-row">
                  <td>{billTotalLabel}</td>
                  <td>{formatEuro(totalBillWithoutCommunity)}</td>
                  <td>{formatEuro(totalBillWithCommunity)}</td>
                  <td className="saving-cell">{formatEuro(totalSaved)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          </IndicatorCard>
        )}


        <div className="economics-subsection">
          <div className="economics-subsection-heading">
            <h3>Return on investment</h3>
          </div>

          <div className="economics-summary-grid roi-summary-grid">
            <IndicatorCard
              section="economics"
              title="Total invested"
              description="Total investment in community energy assets"
              value={formatEuro(kpis.totalInvested?.value)}
              info="Upfront cost of installed generation and battery capacity."
            />

            <IndicatorCard
              section="economics"
              title="Community profit"
              description={`Return on the community investment for ${periodReference}`}
              value={kpis.profit?.value != null
                ? `${(kpis.profit.value * 100).toFixed(1)} %`
                : "—"}
              info="Indicates how much financial benefit the community generates from its investment."
            />

            <IndicatorCard
              section="economics"
              title="Community payback time"
              description="Estimated time to recover the community investment"
              value={kpis.payback?.value != null
                ? `${kpis.payback.value.toFixed(1)} ${paybackUnit}`
                : "—"}
              info="Estimates how long it takes for the community to recover its initial investment, based on the profit generated over the selected period."
            />
          </div>
        </div>

      </section>


      <section id="social" className="result-section">
        <SectionHeading title="Social" color={colors.purple} />
        <div className="two-cards">
          <IndicatorCard
            section="social"
            title="Fairness index"
            description="Equity in the distribution of community savings"
            value={kpis.fairness?.value != null
              ? kpis.fairness.value.toFixed(3)
              : "—"}
            info={
              <>
                <p>Compares members' savings per unit of generation.</p>
                <p>Values closer to 1 indicate a more even distribution, while lower values indicate greater differences.</p>
              </>
            }
          />
          <IndicatorCard
            section="social"
            title="Self-sufficiency gap"
            description="Difference between the most and least self-sufficient participant"
            value={kpis.selfSufficiencyGap?.value != null
              ? `${(kpis.selfSufficiencyGap.value * 100).toFixed(1)} pp`
              : "—"}
            info="Gap between the highest and lowest member self-sufficiency. Smaller gaps mean more similar self-sufficiency."
          />
        </div>
      </section>

      <section id="environmental" className="result-section">
        <SectionHeading title="Environmental" color={colors.blue} />
        <div className="two-cards">
          <IndicatorCard
            section="environmental"
            title="Avoided emissions"
            description={period === "annual"
              ? "Net annual CO₂-equivalent reduction"
              : `Net CO₂-equivalent reduction in ${selectedPeriodLabel || "the selected period"}`}
            className="emissions-card"
            value={kpis.avoidedEmissions?.value != null
              ? `${kpis.avoidedEmissions.value.toFixed(0)} kg`
              : "—"}
            info={
              <>
                <p>Net CO₂-equivalent emissions avoided after accounting for grid imports and equipment emissions.</p>
              </>
            }>
            <div className="emissions-explainer">
              <strong> {emissionsReductionPercent != null
                ? `${emissionsReductionPercent.toFixed(0)}% fewer emissions than without the community.`
                : "—"}
              </strong>
              <p>  {kpis.environmentalImpact?.value != null
                ? `Equivalent to ${(kpis.environmentalImpact.value * 100).toFixed(0)}% of the emissions generated by purchasing all energy from the grid.`
                : "—"}
              </p>
            </div>
          </IndicatorCard>
          <IndicatorCard
            section="environmental"
            title="Carbon payback time"
            description="Time to offset installation emissions"
            value={kpis.carbonPaybackTime?.value != null
              ? `${kpis.carbonPaybackTime.value.toFixed(1)} years`
              : "—"}
            info="Estimates how long it takes for avoided emissions to offset the initial emissions generated by the equipment installation."
          />
        </div>
      </section>
    </main>
  );
}
