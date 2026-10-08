import asyncio
from agent import think

async def test():
    print("Testing question...")
    response = await think("Play Creep by Radiohead")
    print(f"Final response 1: {response}")

asyncio.run(test())
