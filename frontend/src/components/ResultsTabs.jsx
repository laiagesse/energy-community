import { NavLink } from "react-router-dom";

export default function ResultsTabs() {
  return (
    <nav className="results-tabs" aria-label="Results views">
      <NavLink to="/results/community">Community</NavLink>
      <NavLink to="/results/prosumers">Prosumers</NavLink>
      <NavLink to="/results/compare">Compare alternatives</NavLink>
    </nav>
  );
}
