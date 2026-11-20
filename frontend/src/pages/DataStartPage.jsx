import { useState } from "react";
import { useWizard } from "../context/WizardContext";
import { SectionCard, DataFooter, DataHeader, UploadRow, RadioCard } from "../components/WizardUI";
import StepProgress from "../components/StepProgress";

export default function DataStartPage() {
  const { data, setData } = useWizard();
  const [source, setSource] = useState(data.source || "example");
  const [solarFile, setSolarFile] = useState(data.solarFile || null);
  const [windFile, setWindFile] = useState(data.windFile || null);
  
  const chooseFile = (kind, file) => {
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) { window.alert("The file exceeds the 20 MB limit."); return; }
    if (!file.name.toLowerCase().endsWith(".csv")) { window.alert("Please select a CSV file."); return; }
    kind === "solar" ? setSolarFile(file) : setWindFile(file);
  };
  
  const count = Number(!!solarFile) + Number(!!windFile);
  const canContinue = source === "example" || count === 2;
  const next = () => { setData({ source, solarFile, windFile }); };
  
  return <main className="page-width">
    <DataHeader step={1} title="Energy Generation Data" description="Choose which solar and wind generation data you want to use for the simulation."/>
    <StepProgress current={1} />

    <div className="source-options">
      <RadioCard
        name="dataSource"
        value="example"
        selected={source === "example"}
        onChange={setSource}
        title="Try with example data"
        description="Explore the simulation using predefined solar and wind production profiles."
        note="Barcelona · 1 year of hourly data."
      >
      </RadioCard>

      <RadioCard
        name="dataSource"
        value="custom"
        selected={source === "custom"}
        onChange={setSource}
        title="Upload your own data"
        description="Upload the solar and wind production data for your location in CSV format."
        note="CSV · max. 20 MB"
      >
      </RadioCard>
    </div>

    {source === "custom" && <SectionCard title="Generation data files" description={`${count} of 2 files uploaded`} className="upload-panel-react">
      <UploadRow title="Solar photovoltaic production" file={solarFile} onFile={file => chooseFile("solar", file)} />
      <UploadRow title="Wind power production" file={windFile} onFile={file => chooseFile("wind", file)} />
      <div className="format-info">
        <h3>File format</h3>
        <p>Exactly two columns, separated by a semicolon.</p>
        <div className="format-grid">
          <div><strong>Columns</strong><span>1) Datetime · format YYYY-MM-DD HH:MM:SS<br/>2) Value · energy in kWh per installed kW</span></div><code>Datetime;Value<br/>2025-01-01 00:00:00;0.142</code></div>
        </div>
    </SectionCard>}

    <DataFooter 
      step={1} 
      status={source === "example" ? "Example data selected" : `${count} of 2 files uploaded`} 
      detail={source === "example" ? "Next step: Community" : canContinue ? "Files ready to continue" : "Upload both files to continue"} 
      nextTo="/configure/community" 
      disabled={!canContinue} 
      onNext={next} />
  </main>
}
