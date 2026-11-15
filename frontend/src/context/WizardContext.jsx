import { createContext, useContext, useMemo, useState } from "react";

const WizardContext = createContext(null);
const initialProsumer = (id, alpha, consumption, pv, wind, battery, tariff) => ({
  id, alpha, consumption, pv, wind, battery, tariff, tariffDetails: {},
});

export function WizardProvider({ children }) {
  const [data, setData] = useState({ source: "example", solarFile: null, windFile: null });
  const [community, setCommunity] = useState({
    pvCost: "", windCost: "", batteryCost: "",
    pvLife: "", windLife: "", batteryLife: "",
    communityPv: "", communityWind: "", communityBattery: "",
    batteryChargePrice: "", p2pRule: "market",
  });
  const [prosumers, setProsumers] = useState([
    initialProsumer("P-01", "0.200", "Working couple", "0.40", "0.09", "0", "Dynamic"),
    initialProsumer("P-02", "0.200", "consum_P02.csv", "0", "1.83", "0", "Fixed"),
    initialProsumer("P-03", "0.200", "consum_P03.csv", "0.12", "1.51", "0", "Time-of-use"),
    initialProsumer("P-04", "0.200", "Single retiree", "0.28", "0.19", "0", "Dynamic"),
    initialProsumer("P-05", "0.200", "Retired couple", "0.35", "0.37", "0", "Dynamic"),
  ]);
  const [alternatives, setAlternatives] = useState({
    seasons: true, p2p: true, pv: true, wind: false, battery: true, price: false, consumption: false,
    selectedSeasons: ["Winter", "Spring", "Summer", "Autumn"],
    selectedP2P: ["market", "one-price"],
  });
  const value = useMemo(() => ({ data, setData, community, setCommunity, prosumers, setProsumers, alternatives, setAlternatives }), [data, community, prosumers, alternatives]);
  return <WizardContext.Provider value={value}>{children}</WizardContext.Provider>;
}
export function useWizard() {
  const context = useContext(WizardContext);
  if (!context) throw new Error("useWizard must be used inside WizardProvider");
  return context;
}
