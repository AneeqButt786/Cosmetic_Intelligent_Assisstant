"""Cosmetic Intelligence Agent - Chainlit App. Run with: chainlit run app.py"""

import asyncio
import chainlit as cl
from agents import Runner, set_default_openai_key
from openai.types.responses import ResponseTextDeltaEvent

from config import get_config
from agent_defs import cosmetic_agent
from utils.logging import get_logger

logger = get_logger(__name__)

def _ensure_config():
    cfg = get_config()
    set_default_openai_key(cfg["openai_api_key"])
    return cfg

@cl.on_chat_start
async def on_chat_start():
    try:
        _ensure_config()
        cl.user_session.set("chat_history", None)
        await cl.Message(content="**Cosmetic Intelligence Agent** - Discover beauty trends, ingredient safety, FDA compliance, product ideas. Ask anything about cosmetics and skincare.", author="Cosmetic Agent").send()
    except ValueError as e:
        await cl.Message(content="Configuration Error: " + str(e), author="System").send()
        raise

@cl.on_message
async def on_message(message: cl.Message):
    user_content = message.content.strip()
    chat_history = cl.user_session.get("chat_history")
    if not user_content:
        await cl.Message(content="Please ask a question about cosmetics or skincare.", author="Cosmetic Agent").send()
        return
    try:
        _ensure_config()
        logger.info("Processing: %s", user_content[:80])
        if chat_history is None:
            result = Runner.run_streamed(cosmetic_agent, user_content)
        else:
            new_input = chat_history.to_input_list() + [{"role": "user", "content": user_content}]
            result = Runner.run_streamed(cosmetic_agent, new_input)
        msg = cl.Message(content="", author="Cosmetic Agent")
        await msg.send()
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                if event.data.delta:
                    await msg.stream_token(event.data.delta)
            await asyncio.sleep(0.01)
        await msg.update()
        cl.user_session.set("chat_history", result)
        logger.info("Response streamed")
    except Exception:
        logger.exception("Cosmetic query failed")
        await cl.Message(content="Something went wrong. Please try again.", author="Cosmetic Agent").send()
