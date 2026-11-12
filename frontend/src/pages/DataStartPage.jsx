import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileUp, Download, CheckCircle2 } from "lucide-react";
import StepProgress from "../components/StepProgress";

export default function DataStartPage() {
  const [source, setSource] = useState("example");
  const [solarFile, setSolarFile] = useState(null);
  const [windFile, setWindFile] = useState(null);
  const navigate = useNavigate();

  const chooseFile = (kind, file) => {
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) {
      window.alert("The file exceeds the 20 MB limit.");
      return;
    }
    if (kind === "solar") setSolarFile(file);
    else setWindFile(file);
  };

  const canContinue = source === "example" || (!!solarFile && !!windFile);

  return <main className="page-width data-page">
    <div className="page-intro">
      <span className="eyebrow">CONFIGURE SIMULATION · STEP 1 OF 6</span>
      <h1>Initial Data</h1>
      <p>Choose the solar and wind generation data you want to use for the simulation.</p>
    </div>
    <StepProgress current={1} />

    <div className="source-options">
      <button type="button" className={`source-option ${source === "example" ? "selected" : ""}`} onClick={() => setSource("example")}>
        <span className="radio-mark">{source === "example" && <span />}</span>
        <span className="source-option-content">
          <strong>Try with example data</strong>
          <span>Barcelona · 1 year of hourly data. Ideal for exploring the tool.</span>
          <em>Recommended</em>
        </span>
      </button>
      <button type="button" className={`source-option ${source === "custom" ? "selected" : ""}`} onClick={() => setSource("custom")}>
        <span className="radio-mark">{source === "custom" && <span />}</span>
        <span className="source-option-content">
          <strong>Upload your own data</strong>
          <span>Upload the solar and wind production data for your location in CSV format.</span>
          <em>CSV · max. 20 MB</em>
        </span>
      </button>
    </div>

    {source === "custom" && <section className="upload-panel">
      <div className="upload-panel-heading">
        <div><h2>Generation Files</h2><p>{Number(!!solarFile) + Number(!!windFile)} of 2 files uploaded</p></div>
        <span className="upload-limit">CSV · max. 20 MB</span>
      </div>
      <UploadRow title="Solar production (photovoltaic)" file={solarFile} onFile={f => chooseFile("solar", f)} />
      <UploadRow title="Wind production" file={windFile} onFile={f => chooseFile("wind", f)} />
      <div className="format-info">
        <h3>File Format</h3>
        <p>Exactly two columns, separated by a semicolon.</p>
        <div className="format-grid">
          <div><strong>Columns</strong><span>1) Datetime · format YYYY-MM-DD HH:MM:SS<br/>2) Value · energy in kWh per installed kW</span></div>
          <code>Datetime;Value<br/>2025-01-01 00:00:00;0.142</code>
        </div>
      </div>
    </section>}

    <footer className="wizard-footer">
      <button type="button" className="button-secondary" disabled>Previous</button>
      <div className="wizard-status">
        <strong>{source === "example" ? "Example data selected" : `${Number(!!solarFile) + Number(!!windFile)} of 2 files uploaded`}</strong>
        <span>{source === "example" ? "Next step: Community" : canContinue ? "Files ready to continue" : "Upload both files to continue"}</span>
      </div>
      <button type="button" className="button-primary" disabled={!canContinue} onClick={() => navigate("/configure/community")}>Next <span>→</span></button>
    </footer>
    <div className="prototype-note">This screen reproduces the “1a · Data · Example” mockup. CSV validation and processing will be connected to the backend once it is ready.</div>
  </main>;
}

function UploadRow({ title, file, onFile }) {
  return <div className="upload-row">
    <div className="upload-symbol"><FileUp size={19}/></div>
    <div className="upload-file-label"><strong>{title}</strong><span>{file ? file.name : "No file uploaded · pending"}</span></div>
    {file && <CheckCircle2 className="upload-check" size={18}/>}
    <label className="button-secondary upload-button">Upload file<input type="file" accept=".csv,text/csv" onChange={e => onFile(e.target.files?.[0])}/></label>
    <button type="button" className="button-template" onClick={() => window.alert("The CSV template will be available once the final backend format has been defined.")}><Download size={14}/> Download template</button>
  </div>;
}