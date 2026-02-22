"""Start the calendar agent from the project root."""
import asyncio
import warnings

import speech_recognition as sr
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types  # For creating message Content/Parts

from src.agents.calenderAgent.agent import root_agent

warnings.filterwarnings("ignore", category=UserWarning)

APP_NAME = "weather_tutorial_app"
USER_ID = "user_1"
SESSION_ID = "session_001"  # Using a fixed ID for simplicity


async def call_agent_async(query: str, runner, user_id, session_id):
    """Sends a query to the agent and prints the final response."""
    print(f"\n>>> User Query: {query}")

    content = types.Content(role="user", parts=[types.Part(text=query)])
    final_response_text = "Agent did not produce a final response."

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = (
                    f"Agent escalated: {event.error_message or 'No specific message.'}"
                )
            break

    print(f"<<< Agent Response: {final_response_text}")


async def main():
    print("Starting calendar agent (root_agent) from main.py...")

    # Create session service
    session_service = InMemorySessionService()

    # Create session
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    print(
        f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'"
    )

    # Create runner
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    async def listen_and_send():
        recognizer = sr.Recognizer()

        while True:
            with sr.Microphone() as source:
                print("Speak now... (say 'end' to stop)")
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source)

            try:
                text = recognizer.recognize_google(audio)
                print("You said:", text)

                if text.strip().lower() == "end":
                    print("Ending voice loop.")
                    break

                await call_agent_async(
                    text,
                    runner=runner,
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                )
            except Exception as e:
                print("Could not understand audio:", e)

    await listen_and_send()


if __name__ == "__main__":
    asyncio.run(main())
