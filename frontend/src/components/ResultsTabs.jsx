import { NavLink, useLocation } from "react-router-dom";

export default function ResultsTabs() {
  const location = useLocation();
  const query = location.search;

  return (
    <nav className="results-tabs" aria-label="Results views">
      <NavLink to={`/results/community${query}`}>Community</NavLink>
      <NavLink to={`/results/prosumers${query}`}>Prosumers</NavLink>
      <NavLink to={`/results/compare${query}`}>Compare alternatives</NavLink>
    </nav>
  );
}
