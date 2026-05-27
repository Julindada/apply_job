from contextlib import asynccontextmanager

from langchain_openai import ChatOpenAI

from apply_job.config import settings


def make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.llm_base_url,
        temperature=0,
    )


@asynccontextmanager
async def browser_session():
    from browser_use import Browser, BrowserConfig

    browser = Browser(config=BrowserConfig(cdp_url=settings.cdp_url))
    ctx = await browser.new_context()
    try:
        yield ctx
    finally:
        await ctx.close()
        await browser.close()
