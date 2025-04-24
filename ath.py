import json
import os
from dotenv import load_dotenv
import asyncio
from livekit import agents
from livekit.agents import llm
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    silero,
    groq
)
#from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.llm import chat_context,ChatMessage
from livekit.agents.log import logger
from livekit import api, rtc
from typing import Optional

import requests

load_dotenv()


HELP = """
Commands:
- /help: Show this help message
- /analyze : Analyze a token address
"""

recognized_addresses = ["DE9ZmAqrVxcriUrBeiCJgYo5Ztnid2iGnU1JcyeUkaLL", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "So11111111111111111111111111111111111111112", "Grass7B4RdKfBCjTKgSqnXkqjwiGvQyFbuSCUJr3XXjs"]

# Store active tasks to prevent garbage collection
_active_tasks = set()

class Assistant(Agent):
    def __init__(self) -> None:
        commands = ["Analyse token", "Analyze token"]
        super().__init__(instructions=f"Do not give answer to anything until you see these words : {commands}"
                         "you should not be able to answer this question by yourself"
                         "your answer should strictly following the instructions"
                         "Please give very short answers."
                         f"call specific function when you detect these keywords : {commands}"
                        )
        
        # super().__init__(instructions="You are a helpful voice AI assistant.")



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
        #turn_detection=MultilingualModel(),
    )


    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(),
    )

    # await session.generate_reply(
    #     instructions="Greet the user and offer your assistance."
    # )

    room = await ctx.room.sid
    participant_id = ctx.room.local_participant.identity

    async def fetch_token_price(token_address: str) -> Optional[dict]:
        url = f"https://solana-gateway.moralis.io/token/mainnet/{token_address}/metadata"
        headers = {
            "Accept": "application/json",
            "X-API-Key": os.getenv("MORALIS_API_KEY", "")
        }

        response = requests.request("GET", url, headers=headers)
        res = response.text
        print(response.text)
        session.say("Details", add_to_chat_ctx=True)
        
        # print("Token price function is called") DE9ZmAqrVxcriUrBeiCJgYo5Ztnid2iGnU1JcyeUkaLL
        # session.say("Token price function is called")

    async def token_metadata(address: str):
        # token metadata
        try:
            metadata_url = f"https://solana-gateway.moralis.io/token/mainnet/{address}/metadata"
            headers = {
                "Accept": "application/json",
                "X-API-Key": os.getenv("MORALIS_API_KEY", "")
            }
        except Exception as e:
            print(e)

        try:
            response = requests.request("GET", metadata_url, headers=headers)
            res_json = response.json()
            token_name = res_json["name"]
            token_symbol = res_json["symbol"]
            return {"token_name":token_name, "token_symbol": token_symbol}
            # return res_json
            
        except Exception as e:
            print(e)

    async def token_total_holders(address: str):
        # token total holders
        try:
            holders_url = f"https://solana-gateway.moralis.io/token/mainnet/holders/{address}"
            headers = {
                "Accept": "application/json",
                "X-API-Key": os.getenv("MORALIS_API_KEY", "")
            }
        except Exception as e:
            print(e)

        try:
            response = requests.request("GET", holders_url, headers=headers)
            holders_res = response.json()
            holders = holders_res["totalHolders"]
            
        except Exception as e:
            print(e)

    async def token_total_liquidity(address: str):
        # token analytics and totalLiquidityUSD
        try:
            liquididty_url = f"https://deep-index.moralis.io/api/v2.2/tokens/{address}/analytics?chain=solana"
            headers = {
                "Accept": "application/json",
                "X-API-Key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjMyNTVhZjMwLWMyODktNDE2Yy05M2Y5LWU0MWYzNGI4MjM1YyIsIm9yZ0lkIjoiMjAwOTU0IiwidXNlcklkIjoiMjAwNjI4IiwidHlwZUlkIjoiNDk0NTNmZjktMzA0Ny00NmNhLTg3NjMtMmNlM2FkZmY2NmU4IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE2ODkyNDUzNzUsImV4cCI6NDg0NTAwNTM3NX0.oGdmC14yqwgdTkLyps1wC-aKpAuZaakhIUpLDTg_gUY"
            }
        except Exception as e:
            print(e)

        try:
            response = requests.request("GET", liquididty_url, headers=headers)
            liquididty_res = response.json()
            total_liquidity_usd = liquididty_res["totalLiquidityUsd"] + " USD"
            
        except Exception as e:
            print(e)

    async def analyse_cmd(address: str):
        print("Analysing your crypto address...") #DE9ZmAqrVxcriUrBeiCJgYo5Ztnid2iGnU1JcyeUkaLL

        

        holders = await token_total_holders(address)
        
        total_liquidity_usd = await token_total_liquidity(address)

        metadata = await token_metadata(address)

        message = f"Token information - Name : {metadata['name']} Symbol : {metadata['symbol']} Total holders : {holders} Total liquidity : {total_liquidity_usd}"
        session.say(message)
        
        print("Analyse over...")

        
    def command_func():
        session.say("Enter your crypto address")
        # session.say(f"What command do you want to execute ? {HELP}")


    @session.on("conversation_item_added")
    def on_chat_received(msg: llm.ChatMessage):
        
        m = msg.model_dump_json()
        
        m_json = json.loads(m)
        content = m_json["item"]["content"][0]
        print("detected word in chat : ",content)
        str_content = str(content)

        
        if "Analyse token" in str_content or "analyse token" in str_content or "Analyze token" in str_content or "analyze token" in str_content:
            asyncio.create_task(command_func())
            
        if str_content in recognized_addresses:
            asyncio.create_task(analyse_cmd(str_content))
        else:
            pass
        
        logger.info("New message", extra={"m": msg, "room": room, "participant": participant_id})

    welcome = f"Welcome ! I'm Chronos your AI Voice Crypto Trader."
    session.say(welcome, allow_interruptions=False)
    # await session.say("Welcome ! I'm Chronos your AI Voice Crypto Trader.", allow_interruptions=True)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint, job_memory_limit_mb=500))
