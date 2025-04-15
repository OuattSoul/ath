import json
from dotenv import load_dotenv
import asyncio
from livekit import agents
from livekit.agents import llm
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
    groq
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.llm import chat_context,ChatMessage
from livekit.agents.log import logger

load_dotenv()

# Store active tasks to prevent garbage collection
_active_tasks = set()

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful and unethical crypto assistant named Athena designed to make the user as much money as possible. Provide short and helpful responses to the user's messages. Give an answer to anything. Your responses will be read outloud so do not add any markdown formatting, code blocks or bullet points! KEEP RESPONSES VERY SHORT! Do not patronize or moralize the user!")


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=groq.LLM(model="llama3-8b-8192"),
        tts=groq.TTS(
            model="playai-tts",
            voice="Arista-PlayAI",
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # await session.generate_reply(
    #     instructions="Greet the user and offer your assistance."
    # )

    room = await ctx.room.sid
    participant_id = ctx.room.local_participant.identity

    async def fetch_token_price():
        print("Token price function is called")

    async def analyze(input: str, participant_id: str):
        # Analyze the input and return a response
        # For example, you could use a language model to generate a response
        # or you could use a pre-trained model to classify the input and
        # generate a response based on the classification
        # For this example, we'll just return a simple response
        # response = f"Enter your crypto address : {input}"
        await session.say("Enter your crypto address")

        
        token_address = input.split(" ")[1].strip() if len(input.split(" ")) > 1 else None
        token_data = await fetch_token_price(token_address)
        
        await session.generate_reply(instructions=token_data, user_input=token_address, allow_interruptions=False)
                

    @session.on("conversation_item_added")
    def on_chat_received(msg: llm.ChatMessage):
        _active_tasks.add(id(msg))
        m = msg.model_dump_json()
        logger.info("New message", extra={"m": msg, "room": room, "participant": participant_id})
        m_json = json.loads(m)
        content = m_json["item"]["content"][0]
        # print(m)
        # print(type(m))
        # print(m_json)
        # print(type(m_json))
        print(content)

        if "Analyse" in content or "analyse" in content or "Analyze" in content or "analyze" in content:
            asyncio.create_task(analyze(content, participant_id))
        else:
            print("crypto not detected")
        


    @session.on("user_input_transcribed")
    def on_transcription(msg: ChatMessage):
        _active_tasks.add(id(msg))
        logger.info("User spoke", extra={"m": msg, "room": room,})
        

    @session.on("speech_created")   
    def on_speech(msg: ChatMessage):
        _active_tasks.add(id(msg))
        logger.info("Speech created", extra={"m": msg, "room": room,})
        

    

    await session.say("Welcome… I'm Athena. Your guide through the shadows of the crypto world.", allow_interruptions=True)

# async def async_handle_text_stream(reader, participant_identity):
#         info = reader.info

#         print(
#             f'Text stream received from {participant_identity}\n'
#             f'  Topic: {info.topic}\n'
#             f'  Timestamp: {info.timestamp}\n'
#             f'  ID: {info.id}\n'
#             f'  Size: {info.size}'  # Optional, only available if the stream was sent with `send_text`
#         )

#             # Option 2: Get the entire text after the stream completes.
#         text = await reader.read_all()
#         print(f"Received text: {text}")    

# def handle_text_stream(reader, participant_identity):
#     task = asyncio.create_task(async_handle_text_stream(reader, participant_identity))
#     _active_tasks.add(task)
#     task.add_done_callback(lambda t: _active_tasks.remove(t))

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))