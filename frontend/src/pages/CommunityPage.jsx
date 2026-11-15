import { useState } from "react";
import { useWizard } from "../context/WizardContext";
import {Field, SectionCard, DataFooter, DataHeader,} from "../components/WizardUI";
import StepProgress from "../components/StepProgress";

const groups = [
  {
    title: "Community installations",
    description: "Installed capacity of each technology shared by the community.",
    fields: [
      ["communityPv", "Solar PV", "kW", "0"],
      ["communityWind", "Wind", "kW", "1.58"],
      ["communityBattery", "Battery", "kWh", "0"],
    ],
  },
  {
    title: "Investment costs",
    description: "Initial investment cost for each technology.",
    fields: [
      ["pvCost", "Solar PV", "€/kW", "1000"],
      ["windCost", "Wind", "€/kW", "2000"],
      ["batteryCost", "Battery", "€/kWh", "800"],
    ],
  },
  {
    title: "Lifespan",
    description:
      "Expected operational lifetime of each technology.",
    fields: [
      ["pvLife", "Solar PV", "years", "25"],
      ["windLife", "Wind", "years", "30"],
      ["batteryLife", "Battery", "years", "10"],
    ],
  },
];

const rules = [
  {
    id: "market",
    title: "Market price",
    description:
      "Members set their own selling prices, and energy is purchased from the cheapest available offer first.",
  },
  {
    id: "one-price",
    title: "Single price",
    description:
      "All energy exchanges use the same price, determined by supply and demand.",
  },
  {
    id: "social",
    title: "Social priority",
    description:
      "Priority is given to members who have achieved the lowest savings so far.",
  },
  {
    id: "environmental",
    title: "Environmental priority",
    description:
      "Surplus energy is traded with other community members before being exported to the grid.",
  },
];

const exampleValues = {
  pvCost: "1000",
  windCost: "2000",
  batteryCost: "800",

  pvLife: "25",
  windLife: "30",
  batteryLife: "10",

  communityPv: "0",
  communityWind: "1.58",
  communityBattery: "0",

  batteryChargePrice: "0.1677",
  p2pRule: "market",
};

export default function CommunityPage() {
  const { community, setCommunity } = useWizard();
  const [form, setForm] = useState(() => ({ ...community }));

  const update = (key, value) => {
    setForm((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const count = Object.entries(form).filter(
    ([key, value]) =>
      key !== "p2pRule" && String(value).trim() !== "" &&
      Number.isFinite(Number(value))
  ).length;

  const fillExample = () => {
    setForm({...exampleValues});
  };

  const canContinue = count === 10;

  const next = () => {
    if (!canContinue) return false;
    setCommunity({ ...form });
    return true;
  };

  return (
    <main className="page-width">
      <DataHeader
        step={2}
        title="Community"
        description="Configure the community's installations, investment costs and energy-sharing strategy."
      />
      <StepProgress current={2} />

      <div className="section-title">
        <h2>Community configuration</h2>
        <button 
          className="button-secondary"
          type="button"
          onClick={fillExample}
        >
          Fill with example values
        </button>
      </div>

      <div className="card-grid">
        {groups.map((group) => (
          <SectionCard
            key={group.title}
            title={group.title}
            description={group.description}
          >
            <div className="wizard-fields three-cols">
              {group.fields.map(
                ([key, label, unit, placeholder]) => (
                  <Field
                    key={key}
                    label={label}
                    value={form[key]}
                    onChange={(value) => update(key, value)}
                    unit={unit}
                    placeholder={`e.g. ${placeholder}`}
                  />
                )
              )}
            </div>
          </SectionCard>
        ))}
        <SectionCard
          title="Battery strategy"
          description="Set the maximum electricity price at which the battery can charge from the grid."
        >
          <div className="wizard-fields one-col">
            <Field
              label="Maximum purchase price for charging"
              value={form.batteryChargePrice}
              onChange={(value) =>
                update("batteryChargePrice", value)
              }
              unit="€/kWh"
              placeholder="e.g. 0.1677"
            />
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Energy sharing rule between members"
        description="Choose how surplus energy is allocated and traded between community members."
      >
        <div className="rule-grid">
          {rules.map((rule) => (
            <label
              key={rule.id}
              className={`rule-option ${
                form.p2pRule === rule.id
                  ? "selected"
                  : ""
              }`}
            >
              <input
                type="radio"
                name="p2pRule"
                checked={form.p2pRule === rule.id}
                onChange={() => update("p2pRule", rule.id)}
              />

              <span>
                <strong>{rule.title}</strong>
                <small>{rule.description}</small>
              </span>
            </label>
          ))}
        </div>
      </SectionCard>

      <details className="advanced-locked">
        <summary>
          Advanced model parameters · 7 locked values (read-only)
        </summary>

        <p>
          The model's internal parameters remain fixed to
          ensure simulation consistency.
        </p>
      </details>

      <DataFooter
        step={2}
        status={`${count} of 10 fields completed`}
        detail="Enter your own values or continue with the example configuration."
        nextTo="/configure/prosumers"
        previousTo="/configure/data"
        disabled={!canContinue}
        onNext={next}
      />
    </main>
  );
}
