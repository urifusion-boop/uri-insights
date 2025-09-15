from agents import Agent, Runner, handoff

from app.domain.enums.nliagents_enum import NliAgentsInstructionsEnum, NliAgentsNameEnum
from app.domain.responses.uri_response import UriResponse
from .NliLeadsAgent import NilLeadsAgent


class NliAgentOrchestrator:
    agent = Agent(
        name=NliAgentsNameEnum.ORCHESTRATOR_AGENT.value,
        instructions=NliAgentsInstructionsEnum.ORCHESTRATOR_AGENT.value,
        handoffs=[handoff(NilLeadsAgent.agent, on_handoff=NilLeadsAgent.on_handoff)],
    )

    @staticmethod
    async def process_user_prompt(prompt: str, user_id):
        context = {"user_id": user_id}
        print("Triggering agent run.....")
        result = await Runner.run(
            NliAgentOrchestrator.agent,
            prompt,
            context=context,
        )
        print("Result: ", result.final_output)
        return UriResponse.get_single_data_response(
            "NLI agent response", result.final_output
        )
