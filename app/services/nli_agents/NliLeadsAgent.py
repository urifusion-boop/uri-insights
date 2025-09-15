from typing import Any
from agents import Agent, RunContextWrapper

from app.domain.enums.nliagents_enum import NliAgentsInstructionsEnum, NliAgentsNameEnum
from app.services.nli_agents.LeadsAgentTools import get_leads_by_filters_tool


class NilLeadsAgent:
    agent = Agent(
        name=NliAgentsNameEnum.LEAD_AGENT.value,
        instructions=NliAgentsInstructionsEnum.LEAD_AGENT.value,
        tools=[get_leads_by_filters_tool],
    )

    @staticmethod
    def on_handoff(
        ctx: RunContextWrapper[dict[str, Any]],
    ):
        print("Handed off to LeadsAgent with context: ", ctx.context)
