
import { useState } from "react";

export default function DonutChart({
  totalConsumption,
  label = "TOTAL CONSUMPTION",
  segments
}) {
  const [hoveredSegment, setHoveredSegment] = useState(null);
  const [mousePosition, setMousePosition] = useState({
    x: 0,
    y: 0
  });
  const radius = 42;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;

  return (
    <div className="donut-chart-wrapper">
      <div className="donut-chart">

        <svg viewBox="0 0 100 100" role="img" aria-label={label}>
          {segments.map((segment, index) => {
            const segmentLength =
              (segment.value / 100) * circumference;

            const currentOffset = offset;
            offset += segmentLength;

            return (
              <circle
                key={segment.label || index}
                cx="50"
                cy="50"
                r={radius}
                fill="none"
                stroke={segment.color}
                strokeWidth={hoveredSegment === index ? 13 : 11}
                strokeDasharray={`${segmentLength} ${circumference - segmentLength}`}
                strokeDashoffset={-currentOffset}
                transform="rotate(-90 50 50)"
                className="donut-segment"
                onMouseEnter={() => setHoveredSegment(index)}
                onMouseMove={(event) => {
                  const rect = event.currentTarget.ownerSVGElement.getBoundingClientRect();

                  setMousePosition({
                    x: event.clientX - rect.left,
                    y: event.clientY - rect.top
                  });
                }}
                onMouseLeave={() => setHoveredSegment(null)}
              />
            );
          })}
        </svg>

        {hoveredSegment !== null && (
          <div
            className="donut-tooltip"
            style={{
              "--tooltip-color": segments[hoveredSegment].color,
              left: `${mousePosition.x}px`,
              top: `${mousePosition.y}px`
            }}
          >
            <strong>{segments[hoveredSegment].label}</strong>
            <span>{segments[hoveredSegment].quantity} kWh</span>
          </div>
        )}

        <div className="donut-hole">
          <strong>{totalConsumption}</strong>
          <span>{label}</span>
        </div>

      </div>
    </div>
  );
}
