import { useNavigate } from "react-router-dom";

export function DataHeader({ step, eyebrow, title, description}) {
  return <header className="page-intro">
    <span className="eyebrow">CONFIGURE SIMULATION · STEP {step} OF 5</span>
    <h1>{title}</h1>
    <p>{description}</p>
  </header>
}

export function SectionCard({ title, description, action, children, className = "" }) {
  return <section className={`wizard-card ${className}`}>
    {(title || action) && 
    <div className="wizard-card-heading">{title && 
      <div><h2>{title}</h2>{description && <p>{description}</p>}</div>}{action}
    </div>}
    {children}
  </section>;
}

export function Field({ label, value, onChange, unit, placeholder, type = "number", min, max, step = "any", help, required = false }) {
  return <label className="wizard-field"><span>{label}{required && <i> *</i>}</span><div className="wizard-input-wrap"><input type={type} value={value ?? ""} onChange={e => onChange?.(e.target.value)} placeholder={placeholder} min={min} max={max} step={step} required={required} />{unit && <small>{unit}</small>}</div>{help && <small className="field-help">{help}</small>}</label>;
}

export function DataFooter({ step, status, detail, nextLabel = "Next", nextTo, onNext, disabled = false, previousTo }) {
  const navigate = useNavigate();
  return <footer className="wizard-footer">
    <button type="button" className="button-secondary" onClick={() => previousTo ? navigate(previousTo) : navigate(-1)}>Previous</button>
    <div className="wizard-status">
      <strong>{status}</strong>
      <span>{detail}</span>
    </div>
    <button type="button" className="button-primary" disabled={disabled} onClick={() => { const result = onNext?.(); if (result !== false && nextTo) navigate(nextTo); else if (!onNext && nextTo) navigate(nextTo); }}>{nextLabel} <span>→</span></button>
  </footer>;
}

 