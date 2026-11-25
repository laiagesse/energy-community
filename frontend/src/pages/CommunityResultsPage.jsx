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
  const maxTotalLoad = Math.max(
    0,
    ...coverageData.map(item => item.totalLoad ?? 0)
  );
  const hasTotalLoad = coverageData.some(item => item.totalLoad != null);
  const chartScale = maxTotalLoad || 1;
  const coverageTicks = Array.from({ length: 5 }, (_, index) => {
    const fraction = index / 4;
    return {
      value: maxTotalLoad * fraction,
      position: 100 - fraction * 100
    };
  });
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
          title="Total saved"
          description={`${period === "annual" ? "Annual" : "Monthly"} community savings`}
          value={kpis.totalSaved ? `${kpis.totalSaved.value.toFixed(0)} €` : "—"}
          className="summary-card"
          info={
            <>
              <p>Total savings achieved by the energy community compared with the estimated cost of purchasing all consumed electricity from the grid.</p>
              <p>Higher values mean greater economic benefits.</p>
            </>
          }
        />

        <IndicatorCard
          title="Self-sufficiency"
          description="Consumption covered by own resources"
          value={kpis.selfSufficiency ? `${(kpis.selfSufficiency.value * 100).toFixed(1)} %` : "—"}
          className="summary-card"
          info={
            <>
              <p>Share of total community demand covered by locally generated energy, either consumed directly or stored in batteries.</p>
              <p>Energy received through peer-to-peer (P2P) exchanges is not included.</p>
              <p>Higher values mean less dependence on external electricity.</p>
            </>
          }
        />

        <IndicatorCard
          title="Fairness"
          description="Distribution equity"
          value={kpis.fairness ? kpis.fairness.value.toFixed(3) : "—"}
          className="summary-card"
          info={
            <>
              <p>Measures how evenly the economic savings of each community member are distributed in relation to the amount of energy each one generates.</p>
              <p>Values closer to 1 indicate a more balanced distribution, while lower values indicate greater differences.</p>
            </>
          }
        />

        <IndicatorCard
          title="Avoided emissions"
          description="Net annual CO₂ reduction"
          value={kpis.avoidedEmissions ? `${kpis.avoidedEmissions.value.toFixed(0)} kg` : "—"}
          className="summary-card"
          info={
            <>
              <p>Estimates the net annual CO₂-equivalent emissions avoided by the community.</p>
              <p>It considers the reduction in grid electricity use as well as the estimated footprint of the installed equipment.</p>
              <p>Higher values mean a greater net reduction in emissions.</p>
            </>
          }
        />
      </section>

      <section id="energy" className="result-section">
        <SectionHeading title="Energy" color={colors.green} />
        <div className="energy-cards">
          <IndicatorCard
            title="Community electricity consumption"
            description={`${selectedPeriodLabel} consumption coverage by energy source`}
            info={
              <>
                <p>Shows how the total electricity consumed by the community is covered by its own resources, electricity purchased from the grid and peer-to-peer (P2P) exchanges.</p>
                <p>Each percentage represents the share of total community consumption covered by that source.</p>
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
            title="Community direct self-consumption"
            description="Share of community generation used immediately without battery storage"
            className="direct-self-consumption-card"
            value={kpis.selfConsumption?.value != null
              ? `${(kpis.selfConsumption.value * 100).toFixed(1)} %`
              : "—"}
            info={
              <>
                <p>Measures the share of the community's total energy generation that members consume immediately, without storing it in a battery.</p>
                <p>Higher values mean more locally generated energy is used directly.</p>
              </>
            }
          >
            <div className="meter"><span style={{ width: kpis.selfConsumption?.value != null
                ? `${(kpis.selfConsumption.value * 100).toFixed(1)}%`
                : "—"} } /></div>
          </IndicatorCard>

          <IndicatorCard
            title="Surplus energy distribution"
            description="How excess community-generated electricity is distributed"
            info={
              <>
                <p>Shows how the surplus electricity generated by the community is distributed between peer-to-peer (P2P) sales and exports to the electricity grid.</p>
                <p>Each percentage represents the share of total surplus energy allocated to each destination.</p>
              </>
            }
          >
          <div className="donut-card-content">
            <DonutChart
              totalConsumption={totalEnergySurplus != null ? totalEnergySurplus.toFixed(1) : "—"}
              label="SURPLUS kWh"
              segments={p2pSurplusPercent == null ? [] : [
                {
                  label: "P2P trading index in surplus",
                  value: p2pSurplusPercent,
                  quantity: totalEnergySurplus != null
                    ? (totalEnergySurplus * p2pSurplus).toFixed(1)
                    : "—",
                  color: colors.blue
                },
                {
                  label: "Other surplus",
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
                label: "P2P trading index in surplus",
                value: p2pSurplusPercent != null ? `${p2pSurplusPercent.toFixed(1)} %` : "—",
                color: colors.blue
              },
              {
                label: "Other surplus",
                value: otherSurplusPercent != null ? `${otherSurplusPercent.toFixed(1)} %` : "—",
                color: colors.red
              }
            ]} />
          </div>
        </IndicatorCard>
        </div>
        <IndicatorCard
          title={`${periodType === "month" ? "Monthly" : "Seasonal"} consumption coverage`}
          description="Share of community consumption covered by each energy source in every period"
          className="chart-card"
          info={
            <>
              <p>Compares the share of community electricity consumption covered by own resources, grid purchases and peer-to-peer exchanges in each period.</p>
              <p>Each period's total load sets that bar's height; the shared y-axis shows kWh.</p>
              <p>Within each bar, the segments are percentages of that period's total load (100%). Hover to see both the percentage and kWh.</p>
            </>
          }
        >
          <div className="chart-heading">
            <Legend items={[
              { label: "Own resources", color: colors.green },
              { label: "Grid", color: colors.red },
              { label: "P2P exchange", color: colors.blue }
            ]} />
          </div>
          <div className="coverage-chart-layout" role="group" aria-label="Consumption coverage by period">
            <div className="coverage-y-axis" aria-label="Total load in kilowatt-hours">
              {coverageTicks.map(tick => (
                <span
                  className="coverage-y-tick"
                  key={tick.position}
                  style={{ top: `${tick.position}%` }}
                >
                  {hasTotalLoad
                    ? tick.value.toLocaleString("en-GB", { maximumFractionDigits: 1 })
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
                      className={`stack-column${hoveredCoverage?.periodId === item.id ? " is-hovered" : ""}`}
                      key={item.id}
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
                  <span key={item.id} title={item.label}>
                    {periodType === "month" ? item.label.slice(0, 3) : item.label}
                  </span>
                ))}
              </div>
            </div>
          </div>

        </IndicatorCard>
      </section>

      <section id="economics" className="result-section">
        <SectionHeading title="Economics" color={colors.ochre}/>
        <div className="economics-summary-grid">
          <IndicatorCard
            title="Community final electricity bill"
            className="bill-comparison-card"
            description={`Total net electricity cost for the community per ${period === "annual" ? "year" : "month"}`}
            value={communityFinalBill != null
              ? `${communityFinalBill.toFixed(0)} €`
              : "—"}
            info={
                <>
                  <p>Represents the total net electricity cost of all community members for the selected period, taking into account electricity purchases from the grid and through P2P exchanges.</p>
                  <p>Revenues from surplus energy sold to the grid or through P2P exchanges are deducted from these costs.</p>
                </>
            }
          >
            {communitySavingsPercent != null && (
              <div className="bill-savings-section">
                <hr />
                <strong className={`bill-savings-result ${communitySaved < 0 ? "is-higher" : "is-lower"}`}>
                  {Math.abs(communitySavingsPercent).toFixed(1)}%{" "}
                  {communitySaved < 0 ? "higher" : "lower"} than without the community
                </strong>
              </div>
            )}
          </IndicatorCard>
          <IndicatorCard
            title="Total saved"
            description={`Estimated ${period === "annual" ? "annual" : "monthly"} economic savings`}
            value={kpis.totalSaved?.value != null
              ? `${kpis.totalSaved.value.toFixed(0)} €`
              : "—"}
            info={
                <>
                  <p>Savings achieved by the community during the selected period compared with the estimated cost of purchasing all consumed electricity from the grid.</p>
                  <p>Higher values mean greater economic benefits.</p>
                </>
            }
          >
            <hr />
            <p className="card-description">Equivalent to the baseline electricity costs of</p>
            <strong className="households-number">
              {kpis.baselinePovertyHelp?.value != null
                ? `${kpis.baselinePovertyHelp.value.toFixed(1)} average households`
                : "—"}
            </strong>
          </IndicatorCard>
        </div>


        <IndicatorCard
          title="Monthly electricity bill comparison"
          description="Community bills compared with estimated costs without the community"
          className="table-card"
          info={
                <>
                  <p>Bill without community is calculated as the community bill with the community plus the saved amount for that period.</p>
                  <p>The final row totals the periods shown; it is an annual total only when all 12 months are available.</p>
                </>
          }
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


        <div className="economics-subsection">
          <div className="economics-subsection-heading">
            <h3>Return on investment</h3>
            <p>Investment performance and estimated time needed to recover the initial investment.</p>
          </div>

          <div className="economics-summary-grid roi-summary-grid">
            <IndicatorCard
              title="Total invested"
              description="Total investment in community energy assets"
              value={formatEuro(kpis.totalInvested?.value)}
              info="Total community investment in generation and storage assets."
            />

            <IndicatorCard
              title="Community profit (ROI)"
              description={`Return on the community investment for ${selectedPeriodLabel || "the selected period"}`}
              value={kpis.profit?.value != null
                ? `${(kpis.profit.value * 100).toFixed(1)} %`
                : "—"}
              info="Calculated as total community profit divided by total community investment for the selected simulated period."
            />

            <IndicatorCard
              title="Community payback time"
              description="Estimated time to recover the community investment"
              value={kpis.payback?.value != null
                ? `${kpis.payback.value.toFixed(1)} months`
                : "—"}
              info="Calculated as total community investment divided by total community profit for the simulated period. With monthly simulations, the result is in months."
            />
          </div>
        </div>

      </section>


      <section id="social" className="result-section">
        <SectionHeading title="Social" color={colors.purple} />
        <div className="two-cards">
          <IndicatorCard
            title="Fairness (Fairness index)"
            description="Equity in the distribution of community benefits"
            value={kpis.fairness?.value != null
              ? kpis.fairness.value.toFixed(3)
              : "—"}
            info={
              <>
                <p>Measures how evenly economic savings are distributed among community members relative to the energy each one generates.</p>
                <p>Values closer to 1 indicate a more balanced distribution.</p>
              </>
            }
          />
          <IndicatorCard
            title="Self-sufficiency gap"
            description="Difference between the most and least self-sufficient participant"
            value={kpis.selfSufficiencyGap?.value != null
              ? `${(kpis.selfSufficiencyGap.value * 100).toFixed(1)} pp`
              : "—"}
            info="Measures the percentage-point difference in self-sufficiency between the community members with the highest and lowest self-sufficiency."
          />
        </div>
      </section>

      <section id="environmental" className="result-section">
        <SectionHeading title="Environmental" color={colors.blue} />
        <div className="two-cards">
          <IndicatorCard
            title="Annual avoided emissions"
            description="Net annual reduction in CO₂-equivalent emissions"
            className="emissions-card"
            value={kpis.avoidedEmissions?.value != null
              ? `${kpis.avoidedEmissions.value.toFixed(0)} kg`
              : "—"}
            info={
              <>
                <p>Estimates the net annual emissions avoided by the community compared with purchasing all energy from the grid.</p>
                <p>It accounts for reduced grid electricity use and the estimated footprint of the installed equipment.</p>
              </>
            }
          >
            <div className="emissions-explainer">
              <strong> {kpis.environmentalImpact?.value != null
                ? `${(100- kpis.environmentalImpact.value * 100).toFixed(0)}% fewer emissions than without the community.`
                : "—"}  
              </strong>
              <p>  {kpis.environmentalImpact?.value != null
                ? `Equivalent to ${(kpis.environmentalImpact.value * 100).toFixed(0)}% of the emissions generated by purchasing all energy from the grid.`
                : "—"}
              </p>
            </div>
          </IndicatorCard>
          <IndicatorCard
            title="Carbon payback time"
            description="Time for carbon savings to offset installation emissions"
            value={kpis.carbonPaybackTime?.value != null
              ? `${kpis.carbonPaybackTime.value.toFixed(1)} years`
              : "—"}
            info="Estimates the years required for the community's carbon savings to offset the emissions generated by manufacturing the installations."
          />
        </div>
      </section>
    </main>
  );
}
