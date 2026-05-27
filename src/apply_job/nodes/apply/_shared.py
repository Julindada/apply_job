from contextlib import asynccontextmanager

from langchain_openai import ChatOpenAI

from apply_job.config import settings


def make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.apply_model,
        api_key=settings.apply_api_key,
        base_url=settings.apply_base_url,
        temperature=0,
    )


@asynccontextmanager
async def browser_session():
    """Yield a BrowserSession connected to the host Chrome via CDP.

    keep_alive=True tells Agent.close() not to kill the browser after each
    run, so Chrome stays open and tabs persist between node calls.
    """
    from browser_use import BrowserProfile, BrowserSession

    session = BrowserSession(
        cdp_url=settings.cdp_url,
        browser_profile=BrowserProfile(keep_alive=True),
    )
    yield session
