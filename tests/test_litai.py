import warnings
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
import asyncio

from google.genai import types

from src.config.settings import LLMConfig
from src.services.llm_services import LLMServices

# Define a simple tool
def get_weather(city: str) -> str:
    """Returns mock weather for a city."""
    return f"The weather in {city} is sunny, 28°C."

def build_agent() -> LlmAgent:
    """Create the agent, pointing LiteLlm at LitAI's endpoint."""
    return LlmAgent(
        model=LLMServices(config=LLMConfig(provider="litai")).get_model(),
        name="litai_agent",
        instruction="You are a helpful assistant. Use tools when needed.",
        tools=[get_weather],
    )

async def main():
    agent = build_agent()
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="litai_demo", user_id="user1"
    )
    runner = Runner(
        agent=agent,
        app_name="litai_demo",
        session_service=session_service,
    )
    async for event in runner.run_async(
        user_id="user1",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="What's the weather in Hyderabad?")]
        ),
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)

if __name__ == "__main__":
    asyncio.run(main())
