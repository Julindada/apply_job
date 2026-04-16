"""
Tool: fetch_jobs_from_linkedin

Calls the Apify LinkedIn Jobs Scraper actor and returns raw job dicts.
Uses async run + polling instead of run-sync to avoid the 300 s hard limit.
"""

import time

import httpx
from langchain_core.tools import tool

_ACTOR_ID = "curious_coder~linkedin-jobs-scraper"
_APIFY_BASE = "https://api.apify.com/v2"
# Total budget for the actor to finish (seconds).
_TOTAL_TIMEOUT_SEC = 900
# How long to wait between status polls.
_POLL_INTERVAL_SEC = 10


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
    """Start an Apify actor run, poll until finished, then fetch dataset items.

    Avoids the 300 s hard limit of run-sync-get-dataset-items by using the
    async run endpoint + status polling.
    """
    from apply_job.config import settings

    api_token = settings.apify_token
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "count": count,
        "scrapeCompany": True,
        "splitByLocation": False,
        "splitCountry": split_country,
        "urls": urls,
    }

    # 1. Start the actor run (async).
    run_resp = httpx.post(
        f"{_APIFY_BASE}/acts/{_ACTOR_ID}/runs",
        json=payload,
        headers=headers,
        timeout=30,
    )
    run_resp.raise_for_status()
    run_id = run_resp.json()["data"]["id"]

    # 2. Poll until the run reaches a terminal status.
    deadline = time.monotonic() + _TOTAL_TIMEOUT_SEC
    while True:
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"Apify run {run_id} did not finish within {_TOTAL_TIMEOUT_SEC} s"
            )
        time.sleep(_POLL_INTERVAL_SEC)
        status_resp = httpx.get(
            f"{_APIFY_BASE}/actor-runs/{run_id}",
            headers=headers,
            timeout=30,
        )
        status_resp.raise_for_status()
        run_data = status_resp.json()["data"]
        status = run_data["status"]
        if status == "SUCCEEDED":
            dataset_id = run_data["defaultDatasetId"]
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Apify run {run_id} ended with status: {status}")

    # 3. Fetch all items from the dataset.
    items_resp = httpx.get(
        f"{_APIFY_BASE}/datasets/{dataset_id}/items",
        params={"format": "json", "clean": "true"},
        headers=headers,
        timeout=60,
    )
    items_resp.raise_for_status()
    return items_resp.json()
