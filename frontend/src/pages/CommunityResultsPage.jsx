import { useState, useEffect } from "react";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import DonutChart from "../components/DonutChart";
import InfoButton from "../components/InfoButton";
import { monthlyBills, monthlyCoverage } from "../data/communityResults";

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

function MetricCard({ label, value, detail, info}) {
  return (
    <article className="summary-card">
      <div className="summary-card-top">
        <span>{label}</span>
        <InfoButton content={info} />
      </div>

      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

export default function CommunityResultsPage() {
  const [period, setPeriod] = useState("winter");
  const [alternative, setAlternative] = useState("");
  const [experiments, setExperiments] = useState([]);
  const [communityData, setCommunityData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoveredCoverage, setHoveredCoverage] = useState(null);
  const [coverageMousePosition, setCoverageMousePosition] = useState({
    x: 0,
    y: 0
  });

  // Load the available experiments for the selector.
  useEffect(() => {
    let cancelled = false;

    const fetchExperiments = async () => {
      try {
        const response = await fetch("http://127.0.0.1:8000/experiments");
        if (!response.ok) {
          throw new Error("Could not load the available experiments");
        }

        const data = await response.json();
        if (cancelled) return;

        const availableExperiments = data.experiments ?? [];
        setExperiments(availableExperiments);

        if (availableExperiments.length > 0) {
          setAlternative(current =>
            availableExperiments.some(item => item.id === current)
              ? current
              : availableExperiments[0].id
          );
        } else {
          setLoading(false);
          setError("No experiments are available.");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      }
    };

    fetchExperiments();
    return () => {
      cancelled = true;
    };
  }, []);

  // Load the community KPIs whenever the selected experiment changes.
  useEffect(() => {
    if (!alternative) return;

    let cancelled = false;

    const fetchCommunityResults = async () => {
      setLoading(true);
      setError(null);
      setCommunityData(null);

      try {
        const response = await fetch(
          `http://127.0.0.1:8000/experiments/${alternative}/kpis/community`
        );

        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body.detail || "Could not load community results");
        }

        const data = await response.json();
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
  }, [alternative]);

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

  return (
    <main className="page-width">
      <ResultsPageHeader
        period={period}
        onPeriodChange={setPeriod}
        alternative={alternative}
        onAlternativeChange={setAlternative}
        periods={periods}
        experiments={experiments}
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
        <MetricCard label="Total savings" 
          value={kpis.totalSaved ? `${kpis.totalSaved.value.toFixed(0)} €` : "—"}
          //detail={`${selectedPeriodLabel} community savings`}
          detail= "Monthly community savings"
          info={
            <>
              <p>Total savings achieved by the energy community compared with the estimated cost of purchasing all consumed electricity from the grid.</p>
              <p>Higher values mean greater economic benefits.</p>
            </>
          }
        />
        <MetricCard label="Self-sufficiency" 
          value={kpis.selfSufficiency ? `${(kpis.selfSufficiency.value * 100).toFixed(1)} %` : "—"}
          detail="Consumption covered by own resources" 
          info={
            <>
              <p>Share of total community demand covered by locally generated energy, either consumed directly or stored in batteries.</p>
              <p>Energy received through peer-to-peer (P2P) exchanges is not included.</p>
              <p>Higher values mean less dependence on external electricity.</p>
            </>
          }
        />
        <MetricCard 
          label="Fairness" 
          value={kpis.fairness ? kpis.fairness.value.toFixed(3) : "—"} 
          detail="Distribution equity" 
          info={
            <>
              <p>Measures how evenly the economic savings of each community member are distributed in relation to the amount of energy each one generates.</p>
              <p>Values closer to 1 indicate a more balanced distribution, while lower values indicate greater differences.</p>
            </>
          }
        />
        <MetricCard 
          label="Avoided emissions" 
          value={kpis.avoidedEmissions ? `${kpis.avoidedEmissions.value.toFixed(0)} kg` : "—"}
          detail="Net annual CO₂ reduction" 
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
          <article className="result-card">
            <div className="card-heading-row">
              <div>
                <h3>Community electricity consumption</h3>
                <p className="card-subtitle">{`${selectedPeriodLabel} consumption coverage by energy source`}</p>
              </div>
              <InfoButton
                content={
                  <>
                    <p>Shows how the total electricity consumed by the community is covered by its own resources, electricity purchased from the grid and peer-to-peer (P2P) exchanges.</p>
                    <p>Each percentage represents the share of total community consumption covered by that source.</p>
                  </>
                }
              />
            </div>

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

          </article>

          <article className="result-card">
            <h3>Community direct self-consumption</h3>
            <strong className="large-number">
              {kpis.selfConsumption?.value != null
                ? `${(kpis.selfConsumption.value * 100).toFixed(1)} %`
                : "—"}
            </strong>
            <div className="meter"><span style={{ width: kpis.selfConsumption?.value != null
                ? `${(kpis.selfConsumption.value * 100).toFixed(1)}%`
                : "—"} } /></div>
            <p className="card-description">Proportion of the community's total energy generation that is consumed immediately by its members, without being stored in the battery.</p>
          </article>


        <article className="result-card">
          <div className="card-heading-row">
            <div>
              <h3>Surplus energy distribution</h3>
              <p className="card-subtitle">How excess community-generated electricity is distributed</p>
            </div>

            <InfoButton
              content={
                <>
                  <p>
                    Shows how the surplus electricity generated by the community
                    is distributed between peer-to-peer (P2P) sales and exports
                    to the electricity grid.
                  </p>
                  <p>
                    Each percentage represents the share of total surplus energy
                    allocated to each destination.
                  </p>
                </>
              }
            />
          </div>

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
        </article>

        </div>
        <article className="result-card chart-card">
          <div className="chart-heading">
            <div>
              <h3>{periodType === "month" ? "Monthly" : "Seasonal"} consumption coverage</h3>
              <p className="card-subtitle"></p>
            </div>
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
        </article>
      </section>

      <section id="economics" className="result-section">
        <SectionHeading title="Economics" color={colors.ochre}/>
        <div className="economics-summary-grid">
          <article className="result-card">
            <div className="card-heading-row">
              <h3>Total savings</h3>
              <InfoButton content={
                <>
                  <p>Monthly savings achieved by the community compared with the estimated cost of purchasing all consumed electricity from the grid.</p>
                  <p>Higher values mean greater economic benefits.</p>
                </>
              } />
            </div>
            <strong className="large-number">
              {kpis.totalSaved?.value != null
                ? `${kpis.totalSaved.value.toFixed(0)} €`
                : "—"}
            </strong>
            <p className="card-subtitle">Estimated monthly economic savings</p>
            <hr />
            <p className="card-description">Equivalent to the baseline electricity costs of</p>
            <strong className="households-number">
              {kpis.baselinePovertyHelp?.value != null
                ? `${kpis.baselinePovertyHelp.value.toFixed(1)} average households`
                : "—"}
            </strong>
          </article>

          <article className="result-card">
            <div className="card-heading-row">
            <h3>Community final electricity bill</h3>
            <InfoButton
              content={
                <>
                  <p>Represents the total monthly net electricity cost of all community members, taking into account electricity purchases from the grid and through P2P exchanges.</p>
                  <p>Revenues from surplus energy sold to the grid or through P2P exchanges are deducted from these costs.</p>
                </>
              }
            />
            </div>
            <strong className="large-number">
              {kpis.totalFinalBill?.value != null
                ? `${kpis.totalFinalBill.value.toFixed(0)} €`
                : "—"}
            </strong>
            <p className="card-subtitle">Total net electricity cost for the community per month</p>
          </article>
        </div>


        <article className="result-card table-card">
          <div className="card-heading-row">
            <h3>Monthly electricity bill comparison</h3>
            <InfoButton
              content={
                <>
                  <p>Compares the community's total electricity bill with the estimated cost if members purchased all their electricity from the grid without participating in the energy community.</p>
                  <p>The monthly savings correspond to the difference between these two amounts. The final row shows the total for the year.</p>
                </>
              }
            />
          </div>

          <div className="table-scroll">
            <table className="results-table">
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Bill without community</th>
                  <th>Bill with community</th>
                  <th>Saved</th>
                </tr>
              </thead>
              <tbody>
                {monthlyBills.map(row => (
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
        </article>


        <div className="economics-subsection">
          <div className="economics-subsection-heading">
            <h3>Return on investment</h3>
            <p>Investment performance and estimated time needed to recover the initial investment.</p>
          </div>

          <div className="economics-summary-grid">
            <article className="result-card">
              <div className="card-heading-row">
                <h3>Annual return on investment</h3>
                <InfoButton content="Indicates the annual return generated by the investment in the installations, expressed as a percentage of the total amount invested." />
              </div>
              <strong className="large-number">- %</strong>
              <p className="card-description">
                Each year, you earn approximately this percentage of the amount invested.
              </p>
            </article>

            <article className="result-card">
              <div className="card-heading-row">
                <h3>Estimated investment payback</h3>
                <InfoButton content="Estimates how many years are needed to recover the initial investment based on the annual return. It is calculated as 100 divided by the annual return percentage." />
              </div>
              <strong className="large-number">≈ - years</strong>
              <p className="card-description">
                Estimate of the time needed to recover the initial investment based on the annual return.
              </p>
            </article>
          </div>
        </div>

      </section>


      <section id="social" className="result-section">
        <SectionHeading title="Social" color={colors.purple} />
        <div className="two-cards">
          <article className="result-card">
            <h3>Fairness (Fairness index)</h3>
            <strong className="large-number">
              {kpis.fairness?.value != null
                ? kpis.fairness.value.toFixed(3)
                : "—"}
            </strong>
          </article>
          <article className="result-card">
            <h3>Self-sufficiency gap</h3>
            <strong className="large-number">
              {kpis.selfSufficiencyGap?.value != null
                ? `${(kpis.selfSufficiencyGap.value * 100).toFixed(1)} pp`
                : "—"}
            </strong>
            <p className="card-description">Between the most and least self-sufficient participant.</p>
          </article>
        </div>
      </section>

      <section id="environmental" className="result-section">
        <SectionHeading title="Environmental" color={colors.blue} />
        <div className="two-cards">
          <article className="result-card emissions-card">
            <div>
              <h3>Annual avoided emissions</h3>
              <strong className="large-number">
                {kpis.avoidedEmissions?.value != null
                  ? `${kpis.avoidedEmissions.value.toFixed(0)} kg`
                  : "—"}
              </strong>
              <p className="card-subtitle">CO₂ eq. per year</p>
            </div>
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
          </article>
          <article className="result-card">
            <h3>Carbon payback time</h3>
            <strong className="large-number">
              {kpis.carbonPaybackTime?.value != null
                ? `${kpis.carbonPaybackTime.value.toFixed(1)} years`
                : "—"}
            </strong>
            <p className="card-description">Years for carbon savings to offset the emissions generated by manufacturing the installations.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
