"""Quick test to check if chat is working"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from junior.services.conversational_chat import ConversationalChat

async def test():
    chat = ConversationalChat()
    print("Testing conversational chat...")
    print("Sending: hi")
    
    response = ""
    async for chunk in chat.stream_response("hi", [], use_research=False):
        response += chunk
        print(chunk, end="", flush=True)
    
    print(f"\n\nFull response: {response}")

if __name__ == "__main__":
    asyncio.run(test())
