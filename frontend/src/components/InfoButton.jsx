import { useState } from "react";

export default function InfoButton({ content }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="info-button-wrapper">
      <button
        type="button"
        className="info-button"
        aria-label="More information"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
      >
        <svg
          viewBox="0 0 24 24"
          width="15"
          height="15"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M12 11v5" />
          <path d="M12 8h.01" />
        </svg>
      </button>

      {isOpen && (
        <div className="info-button-popup" role="tooltip">
          {content}
        </div>
      )}
    </div>
  );
}