import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/api";

export default function SimulationsResultsPage() {
  const [searchParams] = useSearchParams();
  const [simulations, setSimulations] = useState([]);
  const [selectedSimulation, setSelectedSimulation] = useState(searchParams.get("simulation") || "");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSimulations = async () => {
      try {
        const data = await api.getSimulations();
        const available = data.simulations ?? [];
        setSimulations(available);
        setSelectedSimulation(current => available.includes(current) ? current : (available[0] || ""));
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchSimulations();
  }, []);

  return (
    <main className="page-width results-page simulations-results-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Results</p>
          <h1>Simulation results</h1>
          <p>Select a simulation to explore its results.</p>
        </div>
      </header>

      <section className="result-section">
        <label htmlFor="simulation-selector">Available simulations</label>
        {loading ? <p>Loading simulations...</p> : error ? <p role="alert">Error: {error}</p> : simulations.length === 0 ? <p>No simulations available.</p> : (
          <>
            <select id="simulation-selector" value={selectedSimulation} onChange={event => setSelectedSimulation(event.target.value)}>
              {simulations.map(simulation => <option key={simulation} value={simulation}>{simulation}</option>)}
            </select>
            <div className="simulation-actions">
              <Link className="button-primary" to={`/results/community?simulation=${encodeURIComponent(selectedSimulation)}`}>
                View community results
              </Link>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
