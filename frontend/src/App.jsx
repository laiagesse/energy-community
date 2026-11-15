
import { Navigate, Route, Routes } from "react-router-dom";
import SiteLayout from "./components/SiteLayout";
import DataStartPage from "./pages/DataStartPage";
import CommunityPage from "./pages/CommunityPage";
import CommunityResultsPage from "./pages/CommunityResultsPage";
import CompareResultsPage from "./pages/CompareResultsPage";
import ProsumerResultsPage from "./pages/ProsumerResultsPage";

import { WizardProvider } from "./context/WizardContext";

function Placeholder({ title }) {
  return <div className="page-width placeholder">
    <span className="eyebrow">COMMUNITY TWIN</span>
    <h1>{title}</h1><p>This page will be developed in the next phases.</p>
    </div>;
}

export default function App() {
  return <WizardProvider><Routes><Route element={<SiteLayout />}>
    <Route path="/" element={<Placeholder title="Home" />} />
    <Route path="/configure/data" element={<DataStartPage />} />
    <Route path="/configure/community" element={<CommunityPage/>} />
    <Route path="/configure/prosumers" element={<Placeholder title="Prosumers" />} />
    <Route path="/configure/alternatives" element={<Placeholder title="Alternatives" />} />
    <Route path="/configure/review" element={<Placeholder title="Review" />} />
    <Route path="/results" element={<Placeholder title="Results" />} />
    <Route path="/results/community" element={<CommunityResultsPage />} />
    <Route path="/results/prosumers" element={<ProsumerResultsPage />} />
    <Route path="/results/compare" element={<CompareResultsPage />} />
    <Route path="/how-it-works" element={<Placeholder title="How It Works" />} />
    <Route path="/examples" element={<Placeholder title="Examples" />} />
    <Route path="/contact" element={<Placeholder title="Contact" />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Route></Routes></WizardProvider>;
}
