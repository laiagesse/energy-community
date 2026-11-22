import { useState, useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";

export default function SiteLayout() {
  const [menuOpen, setMenuOpen] = useState(false);

  const navItems = [
    { to: "/", label: "Home" },
    { to: "/configure/data", label: "Configure Simulation" },
    { to: "/results", label: "Analyze Results" },
    { to: "/how-it-works", label: "How It Works" },
    { to: "/examples", label: "Examples" },
    { to: "/contact", label: "Contact" },
  ];

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 1250) {
        setMenuOpen(false);
      }
    };

    window.addEventListener("resize", handleResize);

    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <>
      <header className="topbar">
        <NavLink to="/" className="brand">
          <span className="brand-icon">E</span>
          <span>Community Twin</span>
        </NavLink>

        <nav className="main-nav">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <button className="language-button" type="button">EN</button>

        <button
          className={`menu-toggle ${menuOpen ? "open" : ""}`}
          type="button"
          aria-label="Toggle navigation menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          <span></span>
          <span></span>
          <span></span>
        </button>
      </header>

      <nav className={`mobile-nav ${menuOpen ? "visible" : ""}`}>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => setMenuOpen(false)}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </>
  );
}
