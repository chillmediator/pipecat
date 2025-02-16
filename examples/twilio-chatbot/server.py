#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import argparse
import json

import uvicorn
from bot import run_bot
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

app = FastAPI()

# Initialize app state
app.state.testing = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/")
async def start_call():
    print("POST TwiML")
    return HTMLResponse(content=open("templates/streams.xml").read(), media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("WebSocket connection attempt", flush=True)
    await websocket.accept()
    print("WebSocket accepted", flush=True)
    start_data = websocket.iter_text()
    print("Getting first message", flush=True)
    await start_data.__anext__()
    print("Getting second message", flush=True)
    call_data = json.loads(await start_data.__anext__())
    print(f"Call data received: {call_data}", flush=True)
    stream_sid = call_data["start"]["streamSid"]
    print(f"Stream SID: {stream_sid}", flush=True)
    print("Starting bot", flush=True)
    try:
        await run_bot(websocket, stream_sid, app.state.testing)
    except Exception as e:
        print(f"Error in run_bot: {e}", flush=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipecat Twilio Chatbot Server")
    parser.add_argument(
        "-t", "--test", action="store_true", default=False, help="set the server in testing mode"
    )
    args, _ = parser.parse_known_args()

    app.state.testing = args.test

    uvicorn.run(app, host="0.0.0.0", port=8765)
