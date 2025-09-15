import asyncio
import json
import random
import time
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repository.AiRunRepository import AiRunRepository
from app.domain.requests.airun_requests import AiRunCreateRequest, AiRunUpdateRequest
from app.domain.responses.uri_response import UriResponse


class AiRunService:
    @staticmethod
    async def create_run(
        db: AsyncIOMotorDatabase, thread_id: str, request_data: AiRunCreateRequest
    ):
        response = await AiRunRepository.create_run(db, thread_id, request_data)
        return UriResponse.create_response("run", response)

    @staticmethod
    async def get_run(db: AsyncIOMotorDatabase, thread_id: str, run_id: str):
        response = await AiRunRepository.get_run(thread_id, run_id)
        return UriResponse.get_single_data_response("run", response)

    @staticmethod
    async def get_all_runs(
        db: AsyncIOMotorDatabase, thread_id: str, limit: int, order: str
    ):
        response = await AiRunRepository.get_all_runs(thread_id, limit, order)
        return response

    @staticmethod
    async def update_run(
        db: AsyncIOMotorDatabase,
        thread_id: str,
        run_id: str,
        request_data: AiRunUpdateRequest,
    ):
        response = await AiRunRepository.update_run(thread_id, run_id, request_data)
        return UriResponse.update_response("run", response)

    @staticmethod
    async def cancel_run(db: AsyncIOMotorDatabase, thread_id: str, run_id: str):
        response = await AiRunRepository.cancel_run(thread_id, run_id)
        return UriResponse.delete_response("run", response)

    @staticmethod
    async def get_run_status(thread_id: str, run_id: str):
        response = await AiRunRepository.get_run_status(thread_id, run_id)
        return response

    # @staticmethod
    # def wait_for_run_completion(thread_id: str, run_id: str):
    #     import time

    #     max_retries = 5  # Prevent infinite loops
    #     for _ in range(max_retries):

    #         print("🔄 Checking AI run status...")
    #         run_data = AiRunRepository.get_run_response(
    #             thread_id, run_id
    #         )  # ✅ Fetch full response

    #         run_status = run_data.get("status", "")  # ✅ Extract status

    #         print("🟡 Current AI run status: ", run_status)

    #         if run_status == "completed":
    #             return run_data  # ✅ Return full run response

    #         elif run_status == "requires_action":
    #             print("🟢 AI requires action! Processing tool call...")
    #             return (
    #                 run_data  # ✅ Return full response so `tool_calls` can be checked
    #             )

    #         elif run_status in ["failed", "cancelled", "expired"]:
    #             raise ValueError(f"❌ AI Run failed with status: {run_status}")

    #         time.sleep(5)  # Wait before retrying

    #     raise TimeoutError("⏳ AI Run did not complete in time.")

    @staticmethod
    async def wait_for_run_completion(
        thread_id: str, run_id: str, max_retries: int = 12, retry_delay: int = 2
    ):
        """Waits for an AI run to complete, with adjustable retries and delay."""
        for attempt in range(max_retries):
            print("🔄 Checking AI run status...")
            run_data = await AiRunRepository.get_run_response(thread_id, run_id)

            run_status = run_data.get("status", "")
            print("🟡 Current AI run status: ", run_status)

            if run_status == "requires_action":
                tool_calls = (
                    run_data.get("required_action", {})
                    .get("submit_tool_outputs", {})
                    .get("tool_calls", [])
                )
                if tool_calls:
                    print("🛠 Tool call detected!")
                    return run_data
                else:
                    print("⏳ Tool call pending, retrying...")
            elif run_status == "completed":
                print("✅ AI run completed!")
                return run_data

            if run_status in ["failed", "cancelled", "expired"]:
                if "rate_limit_exceeded" in run_data.get("last_error", {}).get(
                    "code", ""
                ):
                    backoff = retry_delay * (2**attempt) + random.uniform(0, 1)
                    print(
                        f"⏳ Rate limit exceeded. Retrying in {backoff:.2f} seconds..."
                    )
                    await asyncio.sleep(backoff)
                    continue
                await AiRunRepository.cancel_run(thread_id, run_id)
                raise ValueError(f"❌ AI Run failed with status: {run_status}")

            await asyncio.sleep(retry_delay)

        raise TimeoutError("⏳ AI Run did not complete in time.")

    @staticmethod
    async def process_function_response(
        thread_id: str, run_id: str, function_result: dict
    ):
        """
        Injects function response back into OpenAI's conversation and continues processing.
        """
        print("🚀 Submitting function response to OpenAI...")

        print("Now processing function response : ", function_result)
        # ✅ Ensure tool output is properly formatted as a string
        tool_outputs = {
            "tool_outputs": [
                {
                    "tool_call_id": function_result.get(
                        "id"
                    ),  # Tool call ID from AI response
                    "output": json.dumps(function_result),  # Convert to JSON string
                }
            ]
        }

        print("Tools Output : ", tool_outputs)

        # ✅ Send the function result back to OpenAI
        response = await AiRunRepository.update_function_run(
            thread_id, run_id, tool_outputs
        )

        print("Update Function Response : ", response)

        print("✅ Tool output submitted successfully!")

        # ✅ Wait for OpenAI to generate a response
        final_ai_response = await AiRunService.wait_for_run_completion(
            thread_id, run_id
        )
        print("Final AI Response : ", final_ai_response)
        return UriResponse.create_response("message", final_ai_response)
