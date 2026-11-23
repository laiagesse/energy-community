import { NavLink, useLocation } from "react-router-dom";

export default function ResultsTabs({ prosumerId }) {
  const location = useLocation();
  const query = location.search;
  const detailId = prosumerId ?? (location.pathname.startsWith("/results/prosumers/")
    ? decodeURIComponent(location.pathname.split("/").filter(Boolean).at(-1))
    : null);

  return (
    <nav className="results-tabs" aria-label="Results views">
      <NavLink to={`/results/community${query}`}>Community</NavLink>
      <NavLink to={`/results/prosumers${query}`}>Prosumers</NavLink>
      {detailId && (
        <NavLink to={`/results/prosumers/${encodeURIComponent(detailId)}${query}`}>
          Prosumer detail
        </NavLink>
      )}
      <NavLink to={`/results/compare${query}`}>Compare alternatives</NavLink>
    </nav>
  );
}
