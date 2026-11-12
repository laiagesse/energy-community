export default function SectionHeading({ title, description, color }) {
  return (
    <header className="result-section-heading">
      <span className="section-marker" style={{ backgroundColor: color }} />
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
    </header>
  );
}
