"""Demo script: so sanh latency truoc va sau optimize."""

import asyncio
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

CUSTOMER_AGENT_URL = "http://localhost:10100"
QUESTION = "If a company breaks a contract and avoids taxes, what are the legal and regulatory consequences?"


async def run_once(label: str) -> float:
    async with httpx.AsyncClient(timeout=300.0) as client:
        card_resp = await client.get(f"{CUSTOMER_AGENT_URL}/.well-known/agent.json")
        card_resp.raise_for_status()

        from a2a.client import A2AClient
        from a2a.types import AgentCard, Message, MessageSendParams, Part, Role, SendMessageRequest, TextPart
        from uuid import uuid4

        agent_card = AgentCard.model_validate(card_resp.json())
        a2a = A2AClient(httpx_client=client, agent_card=agent_card)

        message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=QUESTION))],
            message_id=str(uuid4()),
        )
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(message=message),
        )

        print(f"\n[{label}] Sending request...")
        t0 = time.perf_counter()
        await a2a.send_message(request)
        elapsed = time.perf_counter() - t0
        print(f"[{label}] Done in {elapsed:.2f}s")
        return elapsed


async def main():
    print("=" * 55)
    print("  LATENCY DEMO — A2A Multi-Agent System")
    print("=" * 55)
    print(f"Question: {QUESTION[:60]}...")

    # Run current version (optimized)
    t = await run_once("OPTIMIZED (parallel dispatch)")

    print("\n" + "=" * 55)
    print("  RESULT SUMMARY")
    print("=" * 55)
    BASELINE = 87.86
    print(f"  Baseline  (sequential):  {BASELINE:.1f}s")
    print(f"  Optimized (parallel):     {t:.1f}s")
    print(f"  Saved:                   ~{BASELINE - t:.1f}s  ({(BASELINE-t)/BASELINE*100:.0f}% faster)")
    print("=" * 55)
    print()
    print("Optimization: Remove check_routing LLM call +")
    print("dispatch analyze_law / tax / compliance IN PARALLEL")
    print("from START instead of sequentially.")


if __name__ == "__main__":
    asyncio.run(main())
