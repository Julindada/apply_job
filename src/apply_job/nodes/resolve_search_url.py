"""
Node: resolve_search_url

Maps an ISO country code to the corresponding LinkedIn geoId and builds
the full search URL. This node must run before fetch_jobs_from_linkedin_node.
"""

from urllib.parse import urlencode

from apply_job.state import AgentState

# LinkedIn geoId per country (ISO 3166-1 alpha-2)
_GEO_IDS: dict[str, int] = {
    "DE": 101282230,   # Germany
    "NL": 102890719,   # Netherlands
    "ES": 105646813,   # Spain
    "AT": 103883259,   # Austria
    "CH": 106693272,   # Switzerland
    "BE": 100565514,   # Belgium
    "FR": 105015875,   # France
    "PT": 100364837,   # Portugal
    "GB": 101165590,   # United Kingdom
    "SE": 105117694,   # Sweden
    "DK": 104514075,   # Denmark
    "PL": 105072130,   # Poland
}

# Fixed search filters — keep consistent across all runs
_BASE_PARAMS = {
    "f_E": "2,4",                              # Entry level + Mid-Senior
    "f_JT": "F",                               # Full-time only
    "f_T": "25194,10738,23347,1660",           # Software/Backend job function IDs
    "f_TPR": "r604800",                        # Posted in the last 7 days
    "keywords": "Backend Java",
    "sortBy": "R",                             # Sort by relevance
}

_LINKEDIN_BASE = "https://www.linkedin.com/jobs/search/"


def resolve_search_url_node(state: AgentState) -> dict:
    country = state["country"].upper()
    geo_id = _GEO_IDS.get(country)
    if geo_id is None:
        raise ValueError(
            f"Unsupported country '{country}'. "
            f"Supported: {sorted(_GEO_IDS)}"
        )
    params = {**_BASE_PARAMS, "geoId": geo_id}
    url = _LINKEDIN_BASE + "?" + urlencode(params)
    return {"search_url": url}
