#!/usr/bin/env python3
"""Stands in for the Android phone so you can test the Ubuntu app without a
real phone connected. This is a developer tool only - it is not installed
by the .deb package.

Examples:
  Ring, then wait for you to click Answer/Decline in the popup and print
  whatever command comes back:
    python3 fake_phone_client.py --number "+15551234567" --name "Jordan"

  Fully scripted run (ring -> active -> ended), useful for smoke-testing
  the whole app end to end without clicking anything:
    python3 fake_phone_client.py --auto
"""

from __future__ import annotations

import argparse
import asyncio
import json

import websockets


async def _print_incoming_commands(connection) -> None:
    async for raw in connection:
        print(f"<- received from app: {raw}")


async def run(
    host: str,
    port: int,
    number: str,
    name: str,
    auto: bool,
    active_after: float,
    end_after: float,
) -> None:
    uri = f"ws://{host}:{port}"
    print(f"Connecting to {uri} ...")
    async with websockets.connect(uri) as connection:
        print("Connected. Sending CALL_RINGING ...")
        await connection.send(json.dumps({"type": "CALL_RINGING", "number": number, "name": name}))

        listener = asyncio.ensure_future(_print_incoming_commands(connection))

        if auto:
            await asyncio.sleep(active_after)
            print("Sending CALL_ACTIVE ...")
            await connection.send(json.dumps({"type": "CALL_ACTIVE"}))

            await asyncio.sleep(end_after)
            print("Sending CALL_ENDED ...")
            await connection.send(json.dumps({"type": "CALL_ENDED"}))

            await asyncio.sleep(0.5)
            listener.cancel()
        else:
            print("Waiting for ANSWER/REJECT from the app (Ctrl+C to stop) ...")
            await listener


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--number", default="+15551234567")
    parser.add_argument("--name", default="Jordan Test")
    parser.add_argument("--auto", action="store_true", help="also send CALL_ACTIVE/CALL_ENDED automatically")
    parser.add_argument("--active-after", type=float, default=3.0, help="seconds before CALL_ACTIVE in --auto mode")
    parser.add_argument("--end-after", type=float, default=3.0, help="seconds before CALL_ENDED in --auto mode")
    args = parser.parse_args()

    asyncio.run(
        run(args.host, args.port, args.number, args.name, args.auto, args.active_after, args.end_after)
    )


if __name__ == "__main__":
    main()
