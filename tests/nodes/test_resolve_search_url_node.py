"""
Unit tests for nodes/resolve_search_url.py
"""

import pytest
from urllib.parse import urlparse, parse_qs

from apply_job.nodes.resolve_search_url import resolve_search_url_node


def test_known_country_returns_search_url():
    result = resolve_search_url_node({"country": "DE"})
    assert result["search_url"].startswith("https://www.linkedin.com/jobs/search/")


def test_geo_id_matches_country():
    result = resolve_search_url_node({"country": "NL"})
    params = parse_qs(urlparse(result["search_url"]).query)
    assert params["geoId"] == ["102890719"]


def test_country_code_is_case_insensitive():
    lower = resolve_search_url_node({"country": "de"})
    upper = resolve_search_url_node({"country": "DE"})
    assert lower["search_url"] == upper["search_url"]


def test_unsupported_country_raises():
    with pytest.raises(ValueError, match="Unsupported country"):
        resolve_search_url_node({"country": "ZZ"})
