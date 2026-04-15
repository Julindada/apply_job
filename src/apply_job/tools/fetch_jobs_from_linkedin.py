"""
Tool: fetch_jobs_from_linkedin

Calls the Apify LinkedIn Jobs Scraper actor and returns raw job dicts.
Mirrors ApifyClient.fetchJobs() from the Kotlin implementation.
"""

import httpx
from langchain_core.tools import tool

_ACTOR_ID = "curious_coder~linkedin-jobs-scraper"
_APIFY_BASE = "https://api.apify.com/v2/acts"
# Apify's synchronous run endpoint has a hard limit of 300 s;
# set the same value on the HTTP client to avoid a client-side timeout first.
_TIMEOUT_SEC = 300


@tool
def fetch_jobs_from_linkedin(search_url: str, country: str) -> list[dict]:
    """Fetch LinkedIn job listings from Apify and return them as a list of dicts.

    Args:
        search_url: LinkedIn jobs search URL to scrape.
        country: ISO country code used as splitCountry, e.g. "ES", "NL", "PL".
    """
    return _call_apify(urls=[search_url], split_country=country, count=300)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _call_apify(urls: list[str], split_country: str, count: int) -> list[dict]:
    """POST to Apify run-sync endpoint and return the raw JSON list.

    Uses run-sync-get-dataset-items so the response arrives in a single HTTP
    call instead of requiring separate polling for the dataset.
    """
    from apply_job.config import settings

    api_token = settings.apify_token
    endpoint = (
        f"{_APIFY_BASE}/{_ACTOR_ID}"
        f"/run-sync-get-dataset-items?timeout={_TIMEOUT_SEC}"
    )
    payload = {
        "count": count,
        "scrapeCompany": True,
        # splitByLocation=False + splitCountry lets Apify filter by a single
        # country without splitting the result into per-location pages.
        "splitByLocation": False,
        "splitCountry": split_country,
        "urls": urls,
    }

    resp = httpx.post(
        endpoint,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        timeout=_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    return resp.json()
