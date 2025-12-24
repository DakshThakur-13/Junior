"""
Quick test for the conversational chat system
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from junior.services.conversational_chat import conversational_chat

async def test_chat():
    print("Testing conversational chat...")
    print("=" * 60)
    
    # Test 1: Simple greeting
    print("\n🧪 Test 1: Simple greeting")
    print("User: Hi, I need help with a legal issue")
    print("Assistant: ", end="", flush=True)
    
    async for chunk in conversational_chat.stream_response(
        "Hi, I need help with a legal issue",
        [],
        use_research=False
    ):
        print(chunk, end="", flush=True)
    
    print("\n" + "=" * 60)
    
    # Test 2: Smart detection
    print("\n🧪 Test 2: Query type detection")
    queries = [
        "Hello",
        "What is Section 302 IPC?",
        "I need help with a bail application",
        "Can you explain anticipatory bail?"
    ]
    
    for query in queries:
        should_research = conversational_chat.should_use_deep_research(query)
        print(f"'{query}' → {'🔍 Deep Research' if should_research else '💬 Quick Chat'}")
    
    print("\n✅ Tests complete!")

if __name__ == "__main__":
    asyncio.run(test_chat())
