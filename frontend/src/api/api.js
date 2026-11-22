const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(endpoint) {
  const response = await fetch(`${API_URL}${endpoint}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Request failed (${response.status})`);
  }

  return response.json();
}

export const api = {
  getSimulations() {
    return request("/simulations");
  },

  getExperiments(simulationId) {
    return request(`/simulations/${encodeURIComponent(simulationId)}/experiments`);
  },

  getCommunityKpis(simulationId, experimentId) {
    return request(
      `/simulations/${encodeURIComponent(simulationId)}/experiments/${encodeURIComponent(experimentId)}/kpis/community`
    );
  },

  getProsumerKpis(simulationId, experimentId) {
    return request(
      `/simulations/${encodeURIComponent(simulationId)}/experiments/${encodeURIComponent(experimentId)}/kpis/prosumers`
    );
  }
};
