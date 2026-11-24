from pathlib import Path
import math
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "Results" / "Results_DOE"
FACTORS = ["P2P Method", "Battery", "Tariff", "Consumption", "PV Installed", "WT Installed"]
PERIOD_COLUMNS = ("Month", "Season", "Period")

P2P_FILE_MAPPING = {
    "Market": "P2P_market",
    "One price": "P2P_one_price",
    "Social": "P2P_social",
    "Environmental": "P2P_enviromental",
}

COMMUNITY_KPIS = {
    "selfSufficiency": "Community Self-Sufficiency",
    "selfSufficiencyGap": "Self-sufficiency difference between prosumers",
    "gridDependency": "Community Grid Dependency",
    "selfConsumption": "Community Self-Consumption",
    "totalFinalBill": "Community total final bill in €",
    "totalSaved": "Community total saved in €",
    "fairness": "Fairness index",
    "baselinePovertyHelp": "Baseline poverty help",
    "avoidedEmissions": "Avoided emissions (Kg CO2 eq)",
    "environmentalImpact": "Enviromental impact",
    "carbonPaybackTime": "TOTAL carbon payback time",
}

PROSUMER_KPIS = {
    "selfConsumption": "Self-Consumption Ratio",
    "selfSufficiency": "Self-Sufficiency Ratio",
    "gridDependency": "Grid Dependency",
    "netP2p": "Net P2P Balance in KWh per simulated period",
    "p2pParticipation": "P2P Participation in KWh per simulated period",
    "sharedEnergy": "Shared energy in KWH (G2P-P2G) per simulated period",
    "p2pDeficit": "P2P trading index in deficit",
    "p2pSurplus": "P2P trading index in surplus",
    "finalBill": "Total final bill in €",
    "saved": "Saved by entering community €",
    "annualProfit": "Profit in %",
    "profitPv": "Profit PV in %",
    "profitWt": "Profit WT in %",
    "profitBattery": "Profit batteries in %",
    "payback": "Payback time",
    "paybackPv": "Payback time PV",
    "paybackWt": "Payback time WT",
    "paybackBattery": "Payback time BATT",
    "billReduction": "Bill reduction in %",
    "gainAppropriation": "EC gain appropiation",
    "savingsAppropriation": "EC savings appropiation",
    "investmentContribution": "Contribution into EC investment",
    "avoidedEmissions": "Avoided emissions (Kg CO2 eq)",
    "environmentalImpact": "Enviromental impact",
    "carbonDebt": "Upfront carbon debt (Kg CO2 eq)",
    "carbonPayback": "TOTAL carbon payback time",
    "pvPayback": "PV carbon payback time",
    "wtPayback": "WT carbon payback time",
    "batteryPayback": "BATT carbon payback time",
}


def _simulation_root(simulation_id: str) -> Path:
    """Resolve a visible simulation folder safely under Results_DOE."""
    if not simulation_id or simulation_id.startswith(".") or Path(simulation_id).name != simulation_id:
        raise ValueError(f"Identificador de simulació no vàlid: {simulation_id}")
    root = RESULTS_ROOT / simulation_id
    if not root.is_dir():
        raise FileNotFoundError(f"No s'ha trobat la simulació: {simulation_id}")
    return root


def list_simulations() -> dict:
    if not RESULTS_ROOT.exists():
        raise FileNotFoundError(f"No s'ha trobat la carpeta de resultats: {RESULTS_ROOT}")
    names = sorted(p.name for p in RESULTS_ROOT.iterdir() if p.is_dir() and not p.name.startswith("."))
    return {"simulations": names}


def _simulation_files(simulation_id: str):
    root = _simulation_root(simulation_id)
    master_file = root / "MasterDoE" / "Master_DoE_Results.xlsx"
    checkpoint_folder = root / "DOE_Individual_Experiments"
    return root, master_file, checkpoint_folder


def _to_json_number(value):
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _period_column(df: pd.DataFrame) -> str:
    populated_columns = [
        column for column in PERIOD_COLUMNS
        if column in df.columns
        and df[column].dropna().astype(str).str.strip().ne("").any()
    ]
    if len(populated_columns) > 1:
        raise ValueError(
            "El fitxer mestre ha de tenir una sola columna de període "
            "amb dades: " + ", ".join(populated_columns)
        )
    if not populated_columns:
        raise ValueError(
            "El fitxer mestre ha de contenir una columna amb períodes: "
            + ", ".join(PERIOD_COLUMNS)
        )
    return populated_columns[0]


def get_experiments(simulation_id: str | None = None) -> dict:
    """Read experiment configurations and their periods from a DoE workbook."""
    if not simulation_id:
        return {
            "simulation_id": None,
            "experiments": [],
            "message": "No hi ha cap simulació seleccionada.",
        }
    _, master_file, _ = _simulation_files(simulation_id)
    if not master_file.is_file():
        raise FileNotFoundError(f"No s'ha trobat el fitxer mestre: {master_file}")

    df = pd.read_excel(master_file, sheet_name="Community DoE", header=1)
    df.columns = [str(column).strip() for column in df.columns]
    period_column = _period_column(df)
    required = FACTORS + [period_column, "Experiment_ID"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(
            "El fitxer mestre no té el format nou esperat. "
            "Falten columnes: " + ", ".join(missing)
        )

    df = df.dropna(subset=["Experiment_ID", period_column, "P2P Method"]).copy()
    df["_period_label"] = df[period_column].astype(str).str.strip()
    df = df[df["_period_label"].ne("")].copy()
    df["_period_id"] = df["_period_label"].str.lower()

    experiments = []
    for factor_values, group in df.groupby(FACTORS, sort=False, dropna=False):
        factors = dict(zip(FACTORS, factor_values))
        experiment_ids = {}
        available_periods = []
        period_ids = dict.fromkeys(group["_period_id"].tolist())
        for period_id in period_ids:
            period_rows = group[group["_period_id"] == period_id]
            if len(period_rows) != 1:
                raise ValueError(
                    f"Configuració {factors}: s'esperava una fila per a {period_id} "
                    f"i se n'han trobat {len(period_rows)}."
                )
            period_label = str(period_rows.iloc[0]["_period_label"])
            raw_id = period_rows.iloc[0]["Experiment_ID"]
            if pd.isna(raw_id):
                raise ValueError(f"Experiment_ID buit per a {period_label}: {factors}")
            experiment_ids[period_label] = int(raw_id)
            available_periods.append({"id": period_id, "label": period_label})

        if experiment_ids:
            experiments.append({
                "factors": factors,
                "run_orders": experiment_ids,
                "available_periods": available_periods,
                "period_type": period_column.lower(),
            })

    def is_baseline(item):
        f = item["factors"]
        return (
            str(f["P2P Method"]).strip().lower() == "market"
            and all(pd.to_numeric(f[k], errors="coerce") == 0
                    for k in ["Battery", "Tariff", "Consumption", "PV Installed", "WT Installed"])
        )

    experiments.sort(key=lambda item: not is_baseline(item))

    for index, experiment in enumerate(experiments, start=1):
        f = experiment["factors"]
        experiment["id"] = f"experiment_{index}"
        experiment["name"] = (
            f"Experiment {index} — {f['P2P Method']} · Battery {f['Battery']} · "
            f"Tariff {f['Tariff']} · Consumption {f['Consumption']} · "
            f"PV {f['PV Installed']} · WT {f['WT Installed']}"
        )

    return {
        "simulation_id": simulation_id,
        "experiments": [
            {
                "id": item["id"],
                "name": item["name"],
                "factors": item["factors"],
                "run_orders": item["run_orders"],
                "available_periods": item["available_periods"],
                "period_type": item["period_type"],
            }
            for item in experiments
        ],
        "period_type": period_column.lower(),
    }


def _load_experiment(simulation_id: str, experiment_id: str) -> dict:
    experiments = get_experiments(simulation_id)["experiments"]
    experiment = next((item for item in experiments if item["id"] == experiment_id), None)
    if experiment is None:
        raise ValueError(f"Experiment no trobat: {experiment_id}")
    return experiment


def _checkpoint_path(checkpoint_folder: Path, run_order: int, period: str, p2p_method: str) -> Path:
    mapped = P2P_FILE_MAPPING.get(str(p2p_method).strip())
    if mapped is None:
        raise ValueError(f"Mètode P2P no reconegut: {p2p_method}")
    if not period or period in {".", ".."} or Path(period).name != period:
        raise ValueError(f"Període no vàlid: {period}")
    path = checkpoint_folder / f"Exp_{run_order}_{period}_{mapped}.xlsx"
    if not path.is_file():
        raise FileNotFoundError(f"No s'ha trobat el checkpoint: {path}")
    return path


def get_experiment_community_kpis(simulation_id: str, experiment_id: str) -> dict:
    experiment = _load_experiment(simulation_id, experiment_id)
    _, _, checkpoint_folder = _simulation_files(simulation_id)
    p2p_method = experiment["factors"]["P2P Method"]
    periods = []
    for period in experiment["available_periods"]:
        period_id = period["id"]
        period_label = period["label"]
        run_order = experiment["run_orders"][period_label]
        checkpoint = _checkpoint_path(checkpoint_folder, run_order, period_id, p2p_method)
        stats = pd.read_excel(checkpoint, sheet_name="Community KPIs", index_col=0)
        kpis = {}
        for api_key, original_name in COMMUNITY_KPIS.items():
            if original_name in stats.index:
                kpis[api_key] = {"value": _to_json_number(stats.loc[original_name].get("mean"))}
        periods.append({"id": period_id, "label": period_label, "kpis": kpis})
    return {"simulation_id": simulation_id, "experiment_id": experiment_id, "type": "community", "period_type": experiment["period_type"], "periods": periods}


def get_experiment_prosumer_kpis(simulation_id: str, experiment_id: str) -> dict:
    experiment = _load_experiment(simulation_id, experiment_id)
    _, _, checkpoint_folder = _simulation_files(simulation_id)
    p2p_method = experiment["factors"]["P2P Method"]
    periods = []
    for period in experiment["available_periods"]:
        period_id = period["id"]
        period_label = period["label"]
        run_order = experiment["run_orders"][period_label]
        checkpoint = _checkpoint_path(checkpoint_folder, run_order, period_id, p2p_method)
        stats = pd.read_excel(checkpoint, sheet_name="Prosumer KPIs")
        required = {"Prosumer", "KPI", "mean"}
        missing = required.difference(stats.columns)
        if missing:
            raise ValueError(f"Falten columnes a 'Prosumer KPIs' de {checkpoint.name}: " + ", ".join(sorted(missing)))
        stats["Prosumer"] = stats["Prosumer"].ffill()
        prosumers = {}
        for _, row in stats.iterrows():
            if pd.isna(row["Prosumer"]) or pd.isna(row["KPI"]):
                continue
            prosumer = str(row["Prosumer"]).strip()
            original_name = str(row["KPI"]).strip()
            api_key = next((key for key, name in PROSUMER_KPIS.items() if name == original_name), None)
            if api_key:
                prosumers.setdefault(prosumer, {})[api_key] = {"value": _to_json_number(row["mean"])}
        periods.append({"id": period_id, "label": period_label, "prosumers": prosumers})
    return {"simulation_id": simulation_id, "experiment_id": experiment_id, "type": "prosumers", "period_type": experiment["period_type"], "periods": periods}
