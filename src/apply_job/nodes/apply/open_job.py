from apply_job.nodes.apply._shared import browser_session, make_agent_kwargs
from apply_job.nodes.apply.state import ApplyState


async def open_job_node(state: ApplyState) -> dict:
    from browser_use import Agent

    job = state["jobs"][state["current_job_index"]]
    idx = state["current_job_index"]
    total = len(state["jobs"])
    print(f"\n[{idx + 1}/{total}] Opening: {job.get('title')} @ {job.get('companyName')}")

    async with browser_session() as session:
        await Agent(
            task=f"Open a new browser tab and navigate to this URL, then stop: {job['link']}",
            browser_session=session,
            **make_agent_kwargs(),
        ).run()
    return {}
