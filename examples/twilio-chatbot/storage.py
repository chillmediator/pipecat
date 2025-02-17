import os
from datetime import datetime
from typing import Optional
import io
import wave
from loguru import logger
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase: Optional[Client] = None

def init_supabase():
    """Initialize Supabase client with credentials from environment variables"""
    global supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.warning("Supabase credentials not found. Storage features will be disabled.")
        return False
    
    try:
        supabase = create_client(url, key)
        logger.info("Supabase client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return False

async def store_conversation(
    call_sid: str,
    audio_data: bytes,
    sample_rate: int,
    num_channels: int,
    conversation_text: list,
    metadata: dict = None
):
    """Store conversation data and audio in Supabase
    
    Args:
        call_sid: Unique identifier for the call
        audio_data: Raw audio bytes
        sample_rate: Audio sample rate
        num_channels: Number of audio channels
        conversation_text: List of conversation messages
        metadata: Additional metadata about the conversation
    """
    if not supabase:
        logger.warning("Supabase client not initialized. Cannot store conversation.")
        return
    
    try:
        # Convert audio to WAV format
        wav_data = io.BytesIO()
        with wave.open(wav_data, "wb") as wf:
            wf.setsampwidth(2)
            wf.setnchannels(num_channels)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)
        
        # Upload audio file to Supabase Storage
        filename = f"{call_sid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        storage_path = f"audio/{filename}"
        
        result = supabase.storage.from_("conversations").upload(
            storage_path,
            wav_data.getvalue(),
            {"content-type": "audio/wav"}
        )
        
        # Store conversation data in the database
        conversation_data = {
            "call_sid": call_sid,
            "timestamp": datetime.now().isoformat(),
            "audio_path": storage_path,
            "conversation": conversation_text,
            "metadata": metadata or {}
        }
        
        result = supabase.table("conversations").insert(conversation_data).execute()
        logger.info(f"Stored conversation data for call {call_sid}")
        
    except Exception as e:
        logger.error(f"Failed to store conversation: {e}")

async def get_conversation(call_sid: str):
    """Retrieve conversation data and audio from Supabase
    
    Args:
        call_sid: Unique identifier for the call
    
    Returns:
        dict: Conversation data including audio URL and messages
    """
    if not supabase:
        logger.warning("Supabase client not initialized. Cannot retrieve conversation.")
        return None
    
    try:
        result = supabase.table("conversations").select("*").eq("call_sid", call_sid).execute()
        if not result.data:
            return None
            
        conversation = result.data[0]
        
        # Get temporary URL for audio file
        audio_url = supabase.storage.from_("conversations").get_public_url(conversation["audio_path"])
        conversation["audio_url"] = audio_url
        
        return conversation
        
    except Exception as e:
        logger.error(f"Failed to retrieve conversation: {e}")
        return None
