"""
Unit tests for nodes/fetch_jobs_from_linkedin.py

LangChain tools are Pydantic frozen models — patch.object cannot replace
their inherited methods.  Instead we patch the name in the node's own
module namespace, replacing the whole tool object with a MagicMock.
"""

from unittest.mock import MagicMock, patch

from apply_job.nodes.fetch_jobs_from_linkedin import fetch_jobs_from_linkedin_node

_FAKE_JOBS = [
    {"id": "1", "title": "Backend Engineer", "companyName": "Acme"},
    {"id": "2", "title": "Java Developer",   "companyName": "Corp"},
]


def _state(**overrides):
    base = {
        "search_url": "https://linkedin.com/jobs/search/?keywords=Java",
        "country": "ES",
        "data_dir": "data",
    }
    return {**base, **overrides}


def _mock_tool(return_value):
    """Return a MagicMock that behaves like a LangChain tool."""
    m = MagicMock()
    m.invoke.return_value = return_value
    return m


class TestFetchJobsFromLinkedinNode:

    def test_returns_raw_jobs_from_tool(self):
        """Node stores the tool's return value under raw_jobs."""
        with patch(
            "apply_job.nodes.fetch_jobs_from_linkedin.fetch_jobs_from_linkedin",
            new=_mock_tool(_FAKE_JOBS),
        ):
            result = fetch_jobs_from_linkedin_node(_state())

        assert result["raw_jobs"] == _FAKE_JOBS

    def test_passes_search_url_to_tool(self):
        """Node forwards search_url from state to the tool."""
        mock_tool = _mock_tool([])
        with patch(
            "apply_job.nodes.fetch_jobs_from_linkedin.fetch_jobs_from_linkedin",
            new=mock_tool,
        ):
            fetch_jobs_from_linkedin_node(_state(search_url="https://example.com"))

        call_args = mock_tool.invoke.call_args[0][0]
        assert call_args["search_url"] == "https://example.com"

    def test_passes_country_to_tool(self):
        """Node forwards country from state to the tool."""
        mock_tool = _mock_tool([])
        with patch(
            "apply_job.nodes.fetch_jobs_from_linkedin.fetch_jobs_from_linkedin",
            new=mock_tool,
        ):
            fetch_jobs_from_linkedin_node(_state(country="NL"))

        call_args = mock_tool.invoke.call_args[0][0]
        assert call_args["country"] == "NL"

    def test_empty_apify_response(self):
        """Node handles an empty list from the tool without errors."""
        with patch(
            "apply_job.nodes.fetch_jobs_from_linkedin.fetch_jobs_from_linkedin",
            new=_mock_tool([]),
        ):
            result = fetch_jobs_from_linkedin_node(_state())

        assert result["raw_jobs"] == []
