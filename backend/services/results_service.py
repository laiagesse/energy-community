from pathlib import Path

import math
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "Results" / "Results_DOE"
SIMULATION_ID = "Original_Experiment"
SIMULATION_ROOT = RESULTS_ROOT / SIMULATION_ID
MASTER_FILE = SIMULATION_ROOT / "MasterDoE" / "Master_DoE_Results.xlsx"
CHECKPOINT_FOLDER = SIMULATION_ROOT / "DOE_Individual_Experiments"

FACTORS = [
    "P2P method",
    "BP tariff",
    "Batteries",
    "Consumption",
]
SEASON_ORDER = ["Winter", "Spring", "Summer", "Autumn"]
PERIOD_ORDER = ["winter", "spring", "summer", "autumn"]

P2P_FILE_MAPPING = {
    "Market": "P2P_market",
    "One price": "P2P_one_price",
    "Social": "P2P_social",
    "Enviromental": "P2P_enviromental",
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
    "avoidedEmissions": "Avoided anual emissions (Kg CO2 eq)",
    "environmentalImpact": "Enviromental impact",
    "carbonPaybackTime": "TOTAL carbon payback time in years",
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
    "finalBill": "Total final bill in € per month",
    "saved": "Saved by entering community € per month",
    "annualProfit": "Anual profit in %",
    "profitPv": "Anual profit PV in %",
    "profitWt": "Anual profit WT in %",
    "profitBattery": "Anual profit bateries in %",
    "paybackPv": "Payback time PV",
    "paybackWt": "Payback time WT",
    "paybackBattery": "Payback time BATT",
    "billReduction": "Bill reduction in %",
    "gainAppropriation": "EC gain appropiation",
    "savingsAppropriation": "EC savings appropiation",
    "investmentContribution": "Contribution into EC investment",
    "avoidedEmissions": "Avoided anual emissions (Kg CO2 eq)",
    "environmentalImpact": "Enviromental impact",
    "carbonDebt": "Upfront carbon debt (Kg CO2 eq)",
    "carbonPayback": "TOTAL carbon payback time in years",
    "pvPayback": "PV carbon payback time in years",
    "wtPayback": "WT carbon payback time in years",
    "batteryPayback": "BATT carbon payback time in years",
}


def _to_json_number(value):
    """Convert Pandas/NumPy numeric values into JSON-safe Python numbers."""
    if value is None or pd.isna(value):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _load_experiment(experiment_id: str) -> dict:
    """Return the experiment metadata, including its seasonal run orders."""
    experiments = get_experiments()["experiments"]
    experiment = next(
        (item for item in experiments if item["id"] == experiment_id),
        None,
    )
    if experiment is None:
        raise ValueError(f"Experiment no trobat: {experiment_id}")
    return experiment


def get_experiments() -> dict:
    """List the experiment configurations found in the master DoE workbook."""
    if not MASTER_FILE.is_file():
        raise FileNotFoundError(f"No s'ha trobat el fitxer mestre: {MASTER_FILE}")

    df = pd.read_excel(MASTER_FILE, sheet_name="Community DoE", header=1)
    missing = [column for column in FACTORS + ["Season", "Run Order"] if column not in df.columns]
    if missing:
        raise ValueError("Falten columnes al fitxer mestre: " + ", ".join(missing))

    grouped = df.groupby(FACTORS, sort=False, dropna=False)
    experiments = []

    for factor_values, group in grouped:
        factors = dict(zip(FACTORS, factor_values))
        run_orders = {}

        for season in SEASON_ORDER:
            season_rows = group[group["Season"].astype(str).str.strip() == season]
            if len(season_rows) != 1:
                raise ValueError(
                    f"S'esperava una fila per a {season} i se n'han trobat {len(season_rows)}."
                )
            run_orders[season] = int(season_rows.iloc[0]["Run Order"])

        experiments.append({"factors": factors, "run_orders": run_orders})

    # Keep the baseline configuration first, as in the previous implementation.
    experiments.sort(
        key=lambda exp: (
            exp["factors"]["P2P method"] != "Market"
            or exp["factors"]["BP tariff"] != "Baseline"
            or exp["factors"]["Batteries"] != "Baseline"
            or exp["factors"]["Consumption"] != "Baseline"
        )
    )

    for index, experiment in enumerate(experiments, start=1):
        factors = experiment["factors"]
        experiment["id"] = f"experiment_{index}"
        experiment["name"] = (
            f"Experiment {index} — {factors['P2P method']} · "
            f"{factors['BP tariff']} tariff · "
            f"{factors['Batteries']} batteries · "
            f"{factors['Consumption']} consumption"
        )

    return {
        "experiments": [
            {
                "id": item["id"],
                "name": item["name"],
                "factors": item["factors"],
                "run_orders": item["run_orders"],
            }
            for item in experiments
        ]
    }


def _checkpoint_path(run_order: int, season: str, p2p_method: str) -> Path:
    mapped_p2p = P2P_FILE_MAPPING.get(str(p2p_method).strip())
    if mapped_p2p is None:
        raise ValueError(f"Mètode P2P no reconegut: {p2p_method}")

    checkpoint = CHECKPOINT_FOLDER / f"Exp_{run_order}_{season}_{mapped_p2p}.xlsx"
    if not checkpoint.is_file():
        raise FileNotFoundError(f"No s'ha trobat el checkpoint: {checkpoint}")
    return checkpoint


def get_experiment_community_kpis(experiment_id: str) -> dict:
    """Return community KPIs for the selected experiment, grouped by season."""
    experiment = _load_experiment(experiment_id)
    p2p_method = experiment["factors"]["P2P method"]
    periods = []

    for season in PERIOD_ORDER:
        run_order = experiment["run_orders"].get(season.capitalize())
        if run_order is None:
            raise ValueError(f"No s'ha trobat el Run Order de {season}")

        checkpoint = _checkpoint_path(run_order, season, p2p_method)
        stats = pd.read_excel(checkpoint, sheet_name="Community KPIs", index_col=0)
        kpis = {}

        for api_key, original_name in COMMUNITY_KPIS.items():
            if original_name not in stats.index:
                continue
            row = stats.loc[original_name]
            kpis[api_key] = {
                "value": _to_json_number(row.get("mean"))
            }

        periods.append({
            "id": season,
            "label": season.capitalize(),
            "kpis": kpis,
        })

    return {
        "experiment_id": experiment_id,
        "type": "community",
        "period_type": "season",
        "periods": periods,
    }


def get_experiment_prosumer_kpis(experiment_id: str) -> dict:
    """Return prosumer KPIs for the selected experiment, grouped by season."""
    experiment = _load_experiment(experiment_id)
    p2p_method = experiment["factors"]["P2P method"]
    periods = []

    for season in PERIOD_ORDER:
        run_order = experiment["run_orders"].get(season.capitalize())
        if run_order is None:
            raise ValueError(f"No s'ha trobat el Run Order de {season}")

        checkpoint = _checkpoint_path(run_order, season, p2p_method)
        stats = pd.read_excel(checkpoint, sheet_name="Prosumer KPIs")

        required = {"Prosumer", "KPI", "mean"}
        missing = required.difference(stats.columns)
        if missing:
            raise ValueError(
                f"Falten columnes a 'Prosumer KPIs' de {checkpoint.name}: "
                + ", ".join(sorted(missing))
            )

        stats["Prosumer"] = stats["Prosumer"].ffill()
        prosumers = {}

        for _, row in stats.iterrows():
            if pd.isna(row["Prosumer"]) or pd.isna(row["KPI"]):
                continue

            prosumer = str(row["Prosumer"]).strip()
            original_name = str(row["KPI"]).strip()
            api_key = next(
                (key for key, name in PROSUMER_KPIS.items() if name == original_name),
                None,
            )
            if api_key is None:
                continue

            prosumers.setdefault(prosumer, {})[api_key] = {
                "value": _to_json_number(row["mean"])
            }

        periods.append({
            "id": season,
            "label": season.capitalize(),
            "prosumers": prosumers,
        })

    return {
        "experiment_id": experiment_id,
        "type": "prosumers",
        "period_type": "season",
        "periods": periods,
    }


def get_prosumer_kpis() -> dict:
    """Backward-compatible helper: return prosumer KPIs for the baseline."""
    experiments = get_experiments()["experiments"]
    if not experiments:
        raise ValueError("No s'han trobat experiments.")
    return get_experiment_prosumer_kpis(experiments[0]["id"])
