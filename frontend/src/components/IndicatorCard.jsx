import InfoButton from "./InfoButton";

export default function IndicatorCard({
  title,
  description,
  info,
  value,
  className = "",
  children
}) {
  return (
    <article className={`result-card indicator-card ${className}`.trim()}>
      <header className="indicator-card-header">
        <div className="indicator-card-heading">
          <h3>{title}</h3>
        </div>
        {info && <InfoButton content={info} />}
      </header>
      {description && <p className="indicator-card-description">{description}</p>}
      <div className="indicator-card-content">
        {value !== undefined && value !== null && (
          <strong className="large-number indicator-card-value">{value}</strong>
        )}
        {children}
      </div>
    </article>
  );
}
