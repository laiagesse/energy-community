import { useState } from "react";
import ResultsTabs from "../components/ResultsTabs";
import ResultsPageHeader from "../components/ResultsPageHeader";
import SectionHeading from "../components/SectionHeading";
import DonutChart from "../components/DonutChart";
import { monthlyBills, monthlyCoverage } from "../data/communityResults";
import InfoButton from "../components/InfoButton";

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
  const [period, setPeriod] = useState("Annual");
  const [alternative, setAlternative] = useState("Current installation");

  const scrollTo = id => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <main className="page-width">
      <ResultsPageHeader period={period} onPeriodChange={setPeriod} alternative={alternative} onAlternativeChange={setAlternative} />
      <ResultsTabs />

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

      <section className="summary-grid" aria-label="Community summary">
        <MetricCard label="Total savings" value="1,474 €" detail="Annual community savings"
          info={
            <>
              <p>Total annual savings achieved by the energy community compared with the estimated cost of purchasing all consumed electricity from the grid.</p>
              <p>Higher values mean greater economic benefits.</p>
            </>
          }
        />
        <MetricCard label="Self-sufficiency" value="35 %" detail="Consumption covered by own resources" 
          info={
            <>
              <p>Share of total community demand covered by locally generated energy, either consumed directly or stored in batteries.</p>
              <p>Energy received through peer-to-peer (P2P) exchanges is not included.</p>
              <p>Higher values mean less dependence on external electricity.</p>
            </>
          }
        />
        <MetricCard label="Fairness" value="0.999" detail="Distribution equity" 
          info={
            <>
              <p>Measures how evenly the economic savings of each community member are distributed in relation to the amount of energy each one generates.</p>
              <p>Values closer to 1 indicate a more balanced distribution, while lower values indicate greater differences.</p>
            </>
          }
        />
        <MetricCard label="Avoided emissions" value="2,158 kg" detail="Net annual CO₂ reduction" 
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
                <p className="card-subtitle">Annual consumption by energy source</p>
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
                totalConsumption="12,450"
                label="TOTAL kWh"
                segments={[
                  {
                    label: "Own resources",
                    value: 35,
                    quantity: 4_357.5,
                    color: colors.green
                  },
                  {
                    label: "Grid",
                    value: 59,
                    quantity: 7_345.5,
                    color: colors.red
                  },
                  {
                    label: "P2P exchange",
                    value: 6,
                    quantity: 747,
                    color: colors.blue
                  }
                ]}
              />
              <Legend items={[
                { label: "Own resources", value: "35 %", color: colors.green },
                { label: "Grid", value: "59 %", color: colors.red },
                { label: "P2P exchange", value: "6 %", color: colors.blue }
              ]} />
            </div>
          </article>

          <article className="result-card">
            <h3>Community direct self-consumption</h3>
            <strong className="large-number">58 %</strong>
            <div className="meter"><span style={{ width: "58%" }} /></div>
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
              <h3>Monthly consumption coverage</h3>
              <p className="card-subtitle"></p>
            </div>
            <Legend items={[
              { label: "Own resources", color: colors.green },
              { label: "Grid", color: colors.red },
              { label: "P2P exchange", color: colors.blue }
            ]} />
          </div>
          <div className="stacked-chart" role="img" aria-label="Monthly consumption coverage stacked bar chart">
            {monthlyCoverage.map(month => (
              <div className="stack-column" key={month.month}>
                <div className="stack-bars">
                  <i style={{ height: `${month.p2p}%`, background: colors.blue }} />
                  <i style={{ height: `${month.grid}%`, background: colors.red }} />
                  <i style={{ height: `${month.own}%`, background: colors.green }} />
                </div>
                <span>{month.month}</span>
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
                  <p>Total annual savings achieved by the energy community compared with the estimated cost of purchasing all consumed electricity from the grid.</p>
                  <p>Higher values mean greater economic benefits.</p>
                </>
              } />
            </div>
            <strong className="large-number">1,474 €</strong>
            <p className="card-subtitle">Estimated annual economic savings</p>
            <hr />
            <p className="card-description">Equivalent to the baseline electricity costs of</p>
            <strong className="households-number">2.3 average households</strong>
          </article>

          <article className="result-card">
            <div className="card-heading-row">
            <h3>Community final electricity bill</h3>
            <InfoButton
              content={
                <>
                  <p>Represents the total annual net electricity cost of all community members, taking into account electricity purchases from the grid and through P2P exchanges.</p>
                  <p>Revenues from surplus energy sold to the grid or through P2P exchanges are deducted from these costs.</p>
                </>
              }
            />
            </div>
            <strong className="large-number">{period === "Annual" ? "1,696 €" : "141 €"}</strong>
            <p className="card-subtitle">{period === "Annual" ? "Total net electricity cost for the community per year" : "Total net electricity cost for the community per month"}</p>
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
              <strong className="large-number">5.1 %</strong>
              <p className="card-description">
                Each year, you earn approximately this percentage of the amount invested.
              </p>
            </article>

            <article className="result-card">
              <div className="card-heading-row">
                <h3>Estimated investment payback</h3>
                <InfoButton content="Estimates how many years are needed to recover the initial investment based on the annual return. It is calculated as 100 divided by the annual return percentage." />
              </div>
              <strong className="large-number">≈ 20 years</strong>
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
            <strong className="large-number">0.999</strong>
          </article>
          <article className="result-card">
            <h3>Self-sufficiency gap</h3>
            <strong className="large-number">12 pp</strong>
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
              <strong className="large-number">2,158</strong>
              <p className="card-subtitle">kg CO₂ eq. per year</p>
            </div>
            <div className="emissions-explainer">
              <strong>34 % fewer emissions than without the community</strong>
              <p>Equivalent to 66 % of the emissions generated by purchasing all energy from the grid (Environmental impact).</p>
            </div>
          </article>
          <article className="result-card">
            <h3>Carbon payback time</h3>
            <strong className="large-number">2.8 years</strong>
            <p className="card-description">Years for carbon savings to offset the emissions generated by manufacturing the installations.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
