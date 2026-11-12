from typing import Dict, List, Optional, Union, Any
from enum import Enum
from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse

app = FastAPI(
    title="Renewable Energy Community Digital Twin API",
    description="""
API documentation for the Stochastic Digital Twin of Renewable Energy Communities.

This API defines the interface between the Digital Twin and the other components of the project.
""",
    version="1.0.0"
)


class DataSource(str, Enum):
    default = "default"
    custom = "custom"


class Season(str, Enum):
    winter = "Winter"
    spring = "Spring"
    summer = "Summer"
    autumn = "Autumn"


class P2PMethod(str, Enum):
    market = "Market"
    one_price = "One price"
    social = "Social"
    environmental = "Environmental"


class SimulationStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class PlotCategory(str, Enum):
    ci = "CI Plots"
    pareto = "Pareto Plots"
    sobol = "Sobol Plots"


# INPUT MODELS

class DatasetFiles(BaseModel):
    pv: str = Field(
        ...,
        title="PV generation file",
        description=(
            "CSV file containing photovoltaic generation data. "
            "The file must contain two columns: Datetime and Value."
        ),
        examples=[
            "Photovoltaic_generation_data.csv"
        ],
    )

    wind: str = Field(
        ...,
        title="Wind generation file",
        description=(
            "CSV file containing wind generation data. "
            "The file must contain two columns: Datetime and Value."
        ),
        examples=[
            "Wind_generation_data.csv"
        ],
    )

    buying_price: str = Field(
        ...,
        title="Electricity buying price file",
        description=(
            "CSV file containing the electricity buying price. "
            "The file must contain two columns: Datetime and Value."
        ),
        examples=[
            "Spanish_Buying_price_ESIOS.csv"
        ],
    )

    selling_price: str = Field(
        ...,
        title="Electricity selling price file",
        description=(
            "CSV file containing the electricity selling price. "
            "The file must contain two columns: Datetime and Value."
        ),
        examples=[
            "Spanish_Selling_price_ESIOS.csv"
        ],
    )

    consumptions: str = Field(
        ...,
        title="Prosumer consumption file",
        description=(
            "CSV file containing the consumption profile of the "
            "prosumers. The first column must be Datetime and the "
            "remaining columns represent individual prosumers."
        ),
        examples=[
            "Consumption.csv"
        ],
    )


class DatasetConfiguration(BaseModel):
    data_source: DataSource = Field(..., description="Default or custom dataset.", examples=[
        "custom", "default"], )
    dataset_folder: Optional[str] = Field(
        None,
        title="Dataset folder",
        description=(
            "Path of the folder containing the datasets."
            "Mainly applicable when a custom dataset is selected."
        ),
        examples=[
            "Datasets/Custom/MyCommunity",
        ],
    )
    files: Optional[DatasetFiles] = Field(
        None,
        title="Dataset files",
        description=(
            "Files used by the simulation. Required when a custom "
            "dataset is selected."
        ),
    )


class CommunityParameters(BaseModel):
    UIC_PV: float = Field(1000.0, description="Unit investment cost of photovoltaic generation (€/kW).", gt=0)
    UIC_WT: float = Field(2000.0, description="Unit investment cost of wind generation (€/kW).", gt=0)
    UIC_B: float = Field(800.0, description="Unit investment cost of battery capacity (€/kWh).", gt=0)

    UL_PV: float = Field(25.0, description="Useful lifetime of photovoltaic panels (years).", gt=0)
    UL_WT: float = Field(30.0, description="Useful lifetime of wind turbines (years).", gt=0)
    UL_B: float = Field(10.0, description="Useful lifetime of batteries (years).", gt=0)

    pw_pv_pr: float = Field(0.0, description="Reference installed PV capacity per prosumer (kW).", ge=0)
    pw_wt_pr: float = Field(1.5762, description="Reference installed wind capacity per prosumer (kW).", ge=0)
    ic_pr: float = Field(0.0, description="Reference installed battery capacity per prosumer (kWh).", ge=0)

    BP_charging_allowed: float = Field(
        0.1677,
        description="Threshold buying price from the grid, from which charging battery from the grid is allowed."
    )


class AdvancedParameters(BaseModel):
    MCH: float = Field(0.15, description="Maintenance cost parameter for charging-related assets.")
    MDCH: float = Field(0.15, description="Maintenance cost parameter for discharging-related assets.")
    PR: float = Field(1.0, description="Performance ratio.")
    CO2_eq_upfront_PV: float = Field(
        1887.0,
        description="Upfront PV emissions (kg CO2 eq per kW installed)."
    )
    CO2_eq_upfront_WT: float = Field(
        1235.0,
        description="Upfront wind emissions (kg CO2 eq per kW installed)."
    )
    CO2_eq_upfront_batt: float = Field(
        55.0,
        description="Upfront battery emissions (kg CO2 eq per kWh installed)."
    )
    CO2_eq_emission_grid: float = Field(
        0.308,
        description="Grid electricity emissions factor (kg CO2 eq per kWh)."
    )


class Prosumer(BaseModel):
    prosumer_id: str = Field(..., description="Unique identifier of the prosumer.", examples=["Prosumer_1"], )

    alpha: float = Field(0.2,
                         description="Sharing rate of the energy produced by no-consumption points allocated to the prosumer.")
    MPW_PV: float = Field(15.0, description="Maximum power of PV panels that can be installed for this prosumer (kW).")
    MPW_WT: float = Field(15.0,
                          description="Maximum power of wind turbines that can be installed for this prosumer (kW).")
    ME_B: float = Field(10.0,
                        description="Maximum energy capacity of batteries that can be installed for this prosumer (kWh).")

    pw_pv: float = Field(0.0, description="Installed PV capacity for this prosumer (kW).")
    pw_wt: float = Field(0.0, description="Installed wind capacity for this prosumer (kW).")
    ic_B: float = Field(0.0, description="Installed battery capacity for this prosumer (kWh).")

    tariff: float = Field(3.0, description="Prosumer energy tariff identifier.")


class LevelDefinition(BaseModel):
    level_id: int
    reference_value: float
    per_prosumer_values: Dict[str, float] = Field(default_factory=dict)


class FactorConfig(BaseModel):
    seasons: Optional[List[Season]] = Field(
        None,
        description="Seasons considered in the Design of Experiments."
    )
    p2p_methods: Optional[List[P2PMethod]] = Field(
        None,
        description="P2P trading methods considered in the Design of Experiments."
    )
    tariff_variance_pct: Optional[float] = Field(
        default=None,
        ge=1,
        le=100,
        description="Percentage variation applied to the prosumer tariff."
    )
    consumption_variance_pct: Optional[float] = Field(
        default=None,
        ge=1,
        le=100,
        description="Percentage variation applied to the consumption profiles."
    )
    battery: Optional[List[LevelDefinition]] = Field(
        None,
        description="Battery capacity levels considered in the Design of Experiments."
    )
    wt_installed: Optional[List[LevelDefinition]] = Field(
        None,
        description="Wind capacity levels considered in the Design of Experiments."
    )
    pv_installed: Optional[List[LevelDefinition]] = Field(
        None,
        description="PV capacity levels considered in the Design of Experiments."
    )


class BaselineConfig(BaseModel):
    season: Optional[Season] = Field(
        None,
        description="Season used for the baseline configuration."
    )
    p2p_method: Optional[P2PMethod] = Field(
        None,
        description="P2P trading method used for the baseline configuration."
    )
    tariff_variance_pct: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Tariff variation used for the baseline configuration."
    )
    consumption_variance_pct: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Consumption variation used for the baseline configuration."
    )
    battery_level_id: Optional[int] = Field(
        None,
        description="Identifier of the battery level used for the baseline configuration."
    )
    wt_installed_level_id: Optional[int] = Field(
        None,
        description="Identifier of the wind capacity level used for the baseline configuration."
    )
    pv_installed_level_id: Optional[int] = Field(
        None,
        description="Identifier of the PV capacity level used for the baseline configuration."
    )


class DoEConfiguration(BaseModel):
    enabled: bool = Field(
        True,
        description="Whether the Design of Experiments is enabled."
    )
    factors: FactorConfig = Field(
        ...,
        description="Factors considered in the Design of Experiments."
    )
    baseline: BaselineConfig = Field(
        None,
        description="Baseline configuration used as a reference for the experiments."
    )


class MonteCarloSettings(BaseModel):
    num_iterations: int = Field(
        200,
        ge=1,
        description="Number of Monte Carlo simulations per experiment."
    )
    n_days: int = Field(
        31,
        ge=1,
        le=365,
        description="Number of simulated days per season."
    )
    sim_seed: int = Field(
        10,
        description="Random seed used to make the stochastic experiment repeatable."
    )


class SimulationRequest(BaseModel):
    dataset: DatasetConfiguration
    community_parameters: CommunityParameters
    advanced_parameters: Optional[AdvancedParameters] = None
    prosumers: List[Prosumer] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Prosumer configuration. The application supports 1 to 1000 prosumers."
    )
    doe: DoEConfiguration
    monte_carlo: MonteCarloSettings


# OUTPUT MODELS

class HealthStatus(BaseModel):
    status: str = Field(
        "ok",
        description="Current health status of the API.",
        examples=["ok"]
    )


class ExperimentSummary(BaseModel):
    experiment_id: str


class SimulationCreatedResponse(BaseModel):
    experiment_id: str
    status: SimulationStatus


class SimulationStatusResponse(BaseModel):
    simulation_id: str
    status: SimulationStatus
    current_experiment: Optional[int] = None
    total_experiments: Optional[int] = None
    progress_percentage: Optional[float] = None
    start_time: Optional[str] = None
    error: Optional[str] = None


class ExperimentKPI(BaseModel):
    kpi: str
    mean: float
    ci: float
    median: float
    min: float
    max: float
    std: float
    q1: float
    q3: float
    cv: float
    ci_low: float
    ci_high: float

class ExperimentProsumerKPI(ExperimentKPI):
    prosumer: str

class BaselineCommunityKPI(BaseModel):
    kpi: str
    autumn: Optional[str] = None
    spring: Optional[str] = None
    summer: Optional[str] = None
    winter: Optional[str] = None

class BaselineProsumerKPI(BaseModel):
    prosumer: str
    kpi: str
    autumn: Optional[str] = None
    spring: Optional[str] = None
    summer: Optional[str] = None
    winter: Optional[str] = None

class PlotListResponse(BaseModel):
    experiment_id: str
    category: PlotCategory
    filenames: List[str]
# ============================================================
# DOCUMENTED ENDPOINTS
# ============================================================
@app.get(
    "/health",
    tags=["System"],
    summary="Check API health",
    description="Checks whether the FastAPI service is running correctly.",
    response_model=HealthStatus
)
def health_check():
    return HealthStatus(
        status="ok"
    )


@app.get(
    "/experiments",
    response_model=List[ExperimentSummary],
    tags=["Results"],
    summary="List available experiments",
)
def get_experiments():
    """
    Return the experiments available in the Results directory.
    """
    return {"experiments": []}

@app.post(
    "/simulation/run",
    response_model=SimulationCreatedResponse,
    tags=["Simulation"],
    summary="Launch a Digital Twin simulation",
)
def run_simulation(request: SimulationRequest):
    return {
        "experiment_id": "SIMULATION_NOT_CONNECTED",
        "status": SimulationStatus.pending,
    }


@app.get(
    "/simulation/{simulation_id}/status",
    response_model=SimulationStatusResponse,
    tags=["Simulation"],
    summary="Get simulation status",
)
def get_simulation_status(experiment_id: str):
    """
    Return the status and progress of a background simulation.
    """
    return {
        "experiment_id": experiment_id,
        "status": SimulationStatus.pending,
        "current_experiment": None,
        "total_experiments": None,
        "progress_percentage": None,
        "start_time": None,
        "error": None,
    }


@app.get(
    "/experiments/{experiment_id}/kpis/community",
    response_model=List[BaselineCommunityKPI],
    tags=["Results"],
    summary="Get community KPIs for an experiment",
)
def get_community_kpis(experiment_id: str):
    """
Returns the main community-level results of a completed Digital Twin simulation.

Community KPIs include:

- Community total saved in €
- Avoided annual emissions (kg CO2 eq)
- Community Self-Sufficiency
- Community Grid Dependency
- Fairness index
- Self-sufficiency difference between prosumers
- Community Self-Consumption
- Community total final bill in €
- Baseline poverty help
- Enviromental impact
- TOTAL carbon payback time in years
    """
    return {
        "experiment_id": experiment_id,
        "results": []
    }


@app.get(
    "/experiments/{experiment_id}/kpis/prosumer",
    response_model=List[BaselineProsumerKPI],
    tags=["Results"],
    summary="Get prosumer KPIs for an experiment",
)
def get_prosumer_kpis(experiment_id: str):
    """
Returns the main prosumer-level results of a completed Digital Twin simulation.

Prosumer KPIs include:

- Self-Consumption Ratio
- Self-Sufficiency Ratio
- Grid Dependency
- Net P2P Balance in KWh per simulated period
- P2P Participation in KWh per simulated period
- Shared energy in KWH (G2P-P2G) per simulated period
- P2P trading index in deficit
- P2P trading index in surplus
- Total final bill in € per month
- Saved by entering community € per month
- Anual profit in %
- Anual profit PV in %
- Anual profit WT in %
- Anual profit bateries in %
- Payback time PV
- Payback time WT
- Payback time BATT
- Bill reduction in %
- EC gain appropiation
- EC savings appropiation
- Contribution into EC investment
- Avoided anual emissions (Kg CO2 eq)
- Enviromental impact
- Upfront carbon debt (Kg CO2 eq)
- TOTAL carbon payback time in years
- PV carbon payback time in years
- WT carbon payback time in years
- BATT carbon payback time in years
    """
    return {
        "experiment_id": experiment_id,
        "results": []
    }

@app.get(
    "/experiments/{experiment_id}/plots/{category}",
    response_model=PlotListResponse,
    tags=["Results"],
    summary="List the image files available for a plot category",
)
def list_plots(
    experiment_id: str,
    category: PlotCategory,
) -> PlotListResponse:

    return {
        "experiment_id": experiment_id,
        "category": category,
        "filenames": [],
    }

@app.get(
    "/experiments/{experiment_id}/plots/{category}/{filename}",
    response_class=FileResponse,
    tags=["Results"],
    summary="Return the specific plot image",
)
def get_plot_image(
    experiment_id: str,
    category: PlotCategory,
    filename: str,
) -> FileResponse:

    return FileResponse(
        path=f"results/{experiment_id}/plots/{category.value}/{filename}",
        media_type="image/png",
        filename=filename,
    )
