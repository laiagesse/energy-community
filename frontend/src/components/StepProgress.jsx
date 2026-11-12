const steps = ["Data", "Community", "Prosumers", "Alternatives", "Review"];

export default function StepProgress({ current = 1 }) {
  return <div className="step-progress">{steps.map((step, i) => {
    const n = i + 1;
    return <div className="step-item" key={step}>
      <div className="step-line-row">
        <span className={`step-number ${n <= current ? "done" : ""}`}>{n}</span>
        {i < steps.length - 1 && <span className="step-line" />}
      </div>
      <span className={`step-label ${n === current ? "current" : ""}`}>{step}</span>
    </div>;
  })}</div>;
}