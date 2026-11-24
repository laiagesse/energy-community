import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import DonutChart from "../components/DonutChart";
import IndicatorCard from "../components/IndicatorCard";
import { monthlyBills, monthlyCoverage } from "../data/communityResults";
import { api } from "../api/api";

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
  const [period, setPeriod] = useState("winter");
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
                : data.periods[0].id
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
  const coverageData = periods.map(item => {
    const kpis = item.kpis ?? {};

    const grid = (kpis.gridDependency?.value ?? 0) * 100;
    const own = (kpis.selfSufficiency?.value ?? 0) * 100;
    const p2p = 100 - grid - own;

    return {
      id: item.id,
      label: item.label,
      grid,
      own,
      p2p
    };
  });

  const sortedMonthlyBills = billSort.key === null ? monthlyBills : [...monthlyBills].sort((a, b) => {
    const parseCell = value => {
      const normalized = String(value ?? "").replace(/[^0-9,.-]/g, "").replace(/\.(?=\d{3}(?:\D|$))/g, "").replace(",", ".");
      const number = normalized.trim() === "" ? NaN : Number(normalized);
      return Number.isFinite(number) ? number : String(value ?? "").toLocaleLowerCase();
    };
    const av = parseCell(a[billSort.key]);
    const bv = parseCell(b[billSort.key]);
    const result = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv), undefined, { numeric: true });
    return billSort.direction === "asc" ? result : -result;
  });

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
          description="Monthly community savings"
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
                totalConsumption="-"
                label="TOTAL kWh"
                segments={[
                  {
                    label: "Own resources",
                    value: ownResources,
                    quantity: 0,
                    color: colors.green
                  },
                  {
                    label: "Grid",
                    value: grid,
                    quantity: 0,
                    color: colors.red
                  },
                  {
                    label: "P2P exchange",
                    value: p2p,
                    quantity: 0,
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
              totalConsumption="100 %"
              label="SURPLUS"
              segments={[
                {
                  label: "P2P sales",
                  value: 24,
                  quantity: "24%",
                  color: colors.blue
                },
                {
                  label: "Grid exports",
                  value: 76,
                  quantity: "76%",
                  color: colors.red
                }
              ]}
            />

            <Legend items={[
              { label: "P2P sales", value: "24 %", color: colors.blue },
              { label: "Grid exports", value: "76 %", color: colors.red }
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
              <p>Hover over a segment to see its value.</p>
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
          <div
            className="stacked-chart"
            role="img"
            aria-label="Consumption coverage by period"
          >
            {coverageData.map(item => (
              <div className="stack-column" key={item.id}>
                <div className="stack-bars">

                  <i
                    style={{ height: `${item.p2p}%`, background: colors.blue }}
                    onMouseEnter={() => setHoveredCoverage({
                      periodId: item.id,
                      label: "P2P exchange",
                      value: item.p2p,
                      color: colors.blue
                    })}
                    onMouseMove={event => {
                      const rect = event.currentTarget.closest(".stack-column").getBoundingClientRect();
                      setCoverageMousePosition({
                        x: event.clientX - rect.left,
                        y: event.clientY - rect.top
                      });
                    }}
                    onMouseLeave={() => setHoveredCoverage(null)}
                  />

                  <i
                    style={{ height: `${item.grid}%`, background: colors.red }}
                    onMouseEnter={() => setHoveredCoverage({
                      periodId: item.id,
                      label: "Grid",
                      value: item.grid,
                      color: colors.red
                    })}
                    onMouseMove={event => {
                      const rect = event.currentTarget.closest(".stack-column").getBoundingClientRect();
                      setCoverageMousePosition({
                        x: event.clientX - rect.left,
                        y: event.clientY - rect.top
                      });
                    }}
                    onMouseLeave={() => setHoveredCoverage(null)}
                  />

                  <i
                    style={{ height: `${item.own}%`, background: colors.green }}
                    onMouseEnter={() => setHoveredCoverage({
                      periodId: item.id,
                      label: "Own resources",
                      value: item.own,
                      color: colors.green
                    })}
                    onMouseMove={event => {
                      const rect = event.currentTarget.closest(".stack-column").getBoundingClientRect();
                      setCoverageMousePosition({
                        x: event.clientX - rect.left,
                        y: event.clientY - rect.top
                      });
                    }}
                    onMouseLeave={() => setHoveredCoverage(null)}
                  />

                </div>

                {hoveredCoverage?.periodId === item.id && (
                  <div
                    className="donut-tooltip"
                    style={{
                      "--tooltip-color": hoveredCoverage.color,
                      left: `${coverageMousePosition.x}px`,
                      top: `${coverageMousePosition.y}px`
                    }}
                  >
                    <strong>{hoveredCoverage.label}</strong>
                    <span>{hoveredCoverage.value.toFixed(1)} %</span>
                  </div>
                )}

                <span>{item.label}</span>
              </div>
            ))}
          </div>

        </IndicatorCard>
      </section>

      <section id="economics" className="result-section">
        <SectionHeading title="Economics" color={colors.ochre}/>
        <div className="economics-summary-grid">
          <IndicatorCard
            title="Total saved"
            description="Estimated monthly economic savings"
            value={kpis.totalSaved?.value != null
              ? `${kpis.totalSaved.value.toFixed(0)} €`
              : "—"}
            info={
                <>
                  <p>Monthly savings achieved by the community compared with the estimated cost of purchasing all consumed electricity from the grid.</p>
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

          <IndicatorCard
            title="Community final electricity bill"
            description="Total net electricity cost for the community per month"
            value={kpis.totalFinalBill?.value != null
              ? `${kpis.totalFinalBill.value.toFixed(0)} €`
              : "—"}
            info={
                <>
                  <p>Represents the total monthly net electricity cost of all community members, taking into account electricity purchases from the grid and through P2P exchanges.</p>
                  <p>Revenues from surplus energy sold to the grid or through P2P exchanges are deducted from these costs.</p>
                </>
            }
          />
        </div>


        <IndicatorCard
          title="Monthly electricity bill comparison"
          description="Community bills compared with estimated costs without the community"
          className="table-card"
          info={
                <>
                  <p>Compares the community's total electricity bill with the estimated cost if members purchased all their electricity from the grid without participating in the energy community.</p>
                  <p>The monthly savings correspond to the difference between these two amounts. The final row shows the total for the year.</p>
                </>
          }
        >
          <div className="table-scroll">
            <table className="results-table">
              <thead>
                <tr>
                  {[
                    ["Month", 0],
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
                {sortedMonthlyBills.map(row => (
                  <tr key={row[0]}>
                    <td>{row[0]}</td>
                    <td>{row[1]}</td>
                    <td>{row[2]}</td>
                    <td className="saving-cell">{row[3]}</td>
                  </tr>
                ))}
                <tr className="total-row">
                  <td>Annual total</td>
                  <td>3,170 €</td>
                  <td>1,696 €</td>
                  <td className="saving-cell">1,474 €</td>
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

          <div className="economics-summary-grid">
            <IndicatorCard
              title="Annual return on investment"
              description="Percentage of the total installation investment returned each year"
              value="- %"
              info="Indicates the annual return generated by the investment in the installations, expressed as a percentage of the total amount invested."
            />

            <IndicatorCard
              title="Estimated investment payback"
              description="Estimated time needed to recover the initial investment"
              value="≈ - years"
              info="Estimates how many years are needed to recover the initial investment based on the annual return. It is calculated as 100 divided by the annual return percentage."
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
