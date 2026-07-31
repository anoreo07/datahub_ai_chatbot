import logging
import re
from dataclasses import dataclass

from datahub.emitter.mce_builder import (
    make_chart_urn,
    make_dashboard_urn,
    make_data_platform_urn,
    make_dataset_urn,
    make_domain_urn,
    make_group_urn,
    make_tag_urn,
    make_term_urn,
    make_user_urn,
)
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

GMS_URL = "http://localhost:8080"

emitter = DatahubRestEmitter(GMS_URL)
graph = DataHubGraph(DatahubClientConfig(server=GMS_URL))


DOMAIN_IDS = [
    "manufacturing",
    "logistics",
    "finance",
    "supply_chain",
    "sales",
    "after_sales",
    "vehicle_development",
    "vgreen",
    "data_governance",
]


def domain_urn(domain_id: str) -> str:
    return make_domain_urn(domain_id)


def data_platform_urn(name: str = "sap") -> str:
    return make_data_platform_urn(name)


def dataset_urn(name: str, platform: str = "sap", env: str = "PROD") -> str:
    return make_dataset_urn(platform, name, env)


def glossary_term_urn(name: str) -> str:
    return make_term_urn(name)


def user_urn(email: str) -> str:
    username = re.sub(r"[^a-zA-Z0-9_]", "_", email.split("@")[0])
    return make_user_urn(username)


def group_urn(name: str) -> str:
    return make_group_urn(name)


def tag_urn(name: str) -> str:
    return make_tag_urn(name)


def dashboard_urn(id: str) -> str:
    return make_dashboard_urn("powerbi", id)


def chart_urn(id: str) -> str:
    return make_chart_urn("powerbi", id)
