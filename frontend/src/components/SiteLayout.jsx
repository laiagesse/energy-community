import { NavLink, Outlet } from "react-router-dom";

export default function SiteLayout() {
  return <>
    <header className="topbar">
      <NavLink to="/" className="brand">
        <span className="brand-icon">E</span><span>Community Twin</span>
      </NavLink>
      <nav className="main-nav">
        <NavLink to="/">Home</NavLink>
        <NavLink to="/configure/data">Configure Simulation</NavLink>
        <NavLink to="/results/community">Analyze Results</NavLink>
        <NavLink to="/how-it-works">How It Works</NavLink>
        <NavLink to="/examples">Examples</NavLink>
        <NavLink to="/contact">Contact</NavLink>
      </nav>
      <button className="language-button" type="button">EN</button>
    </header>
    <Outlet />
  </>;
}
