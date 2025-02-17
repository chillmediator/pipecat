#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import datetime
import io
import os
import sys
import wave

import aiofiles
from dotenv import load_dotenv
from fastapi import WebSocket
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from storage import StorageManager

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# Initialize storage manager
storage = StorageManager(protocol="gdrive", root_path="twilio_recordings")

async def save_audio(server_name: str, audio: bytes, sample_rate: int, num_channels: int):
    """Save audio data using the storage manager."""
    await storage.save_audio(server_name, audio, sample_rate, num_channels)


async def run_bot(websocket_client: WebSocket, stream_sid: str, testing: bool):
    print("Initializing bot components", flush=True)
    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            serializer=TwilioFrameSerializer(stream_sid),
        ),
    )
    print("Transport initialized", flush=True)

    print("Initializing OpenAI LLM", flush=True)
    openai_key = os.getenv("OPENAI_API_KEY")
    print(f"OpenAI key present: {bool(openai_key)}", flush=True)
    llm = OpenAILLMService(api_key=openai_key, model="gpt-4o-mini")
    print("LLM initialized", flush=True)

    print("Initializing Deepgram", flush=True)
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    print(f"Deepgram key present: {bool(deepgram_key)}", flush=True)
    stt = DeepgramSTTService(api_key=deepgram_key, audio_passthrough=True)
    print("Deepgram initialized", flush=True)

    print("Initializing Cartesia", flush=True)
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    print(f"Cartesia key present: {bool(cartesia_key)}", flush=True)
    tts = CartesiaTTSService(
        api_key=cartesia_key,
        voice_id="b7187e84-fe22-4344-ba4a-bc013fcb533e",  # German voice
        model_id="sonic",
        push_silence_after_stop=testing,
    )
    
    # Set the model and language properly
    await tts.set_model("sonic")
    service_lang = tts.language_to_service_language("de")
    await tts.update_setting("language", service_lang)
    await tts.update_setting("output_format", {
        "container": "raw",
        "encoding": "pcm_s16le",
        "sample_rate": 24000
    })
    
    # Debug prints to verify settings after all settings are applied
    print("Cartesia initialized", flush=True)
    print(f"\nTTS Service Configuration:", flush=True)
    print(f"Voice ID: {tts._voice_id}", flush=True)
    print(f"Model: {tts._model_name}", flush=True)
    print(f"Settings: {tts._settings}", flush=True)
    messages = [
        {
            "role": "system",
            "content": "Du bist ein sehr ausführlich antwortender Bot. Du machst gerne Witze.",
        },
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # NOTE: Watch out! This will save all the conversation in memory. You can
    # pass `buffer_size` to get periodic callbacks.
    audiobuffer = AudioBufferProcessor(user_continuous_stream=not testing)

    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            stt,  # Speech-To-Text
            context_aggregator.user(),
            llm,  # LLM
            tts,  # Text-To-Speech
            transport.output(),  # Websocket output to client
            audiobuffer,  # Used to buffer the audio in the pipeline
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000, audio_out_sample_rate=8000, allow_interruptions=True
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Start recording.
        await audiobuffer.start_recording()
        # Kick off the conversation.
        messages.append({"role": "system", "content": "Stelle dich sehr ausführlich vor."})
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()

    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        server_name = f"server_{websocket_client.client.port}"
        await save_audio(server_name, audio, sample_rate, num_channels)

    # We use `handle_sigint=False` because `uvicorn` is controlling keyboard
    # interruptions. We use `force_gc=True` to force garbage collection after
    # the runner finishes running a task which could be useful for long running
    # applications with multiple clients connecting.
    runner = PipelineRunner(handle_sigint=False, force_gc=True)

    await runner.run(task)
