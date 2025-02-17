"""
Storage module for managing audio recordings using fsspec.
"""
import os
import io
import wave
import datetime
import logging
from typing import Optional
import fsspec
import aiofiles
from fsspec.asyn import AsyncFileSystem

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages storage of audio recordings using fsspec."""
    
    def __init__(self, protocol: str = "gdrive", root_path: str = "recordings"):
        """Initialize storage manager.
        
        Args:
            protocol: Storage protocol to use ('gdrive', 'file', 's3', etc.)
            root_path: Root path in the storage where files will be saved
        """
        self.protocol = protocol
        self.root_path = root_path
        self._fs: Optional[AsyncFileSystem] = None
        
        # Ensure we have required credentials
        if protocol == "gdrive":
            if not os.getenv("GOOGLE_TOKEN"):
                raise ValueError("GOOGLE_TOKEN environment variable required for Google Drive storage")
        
    async def _get_filesystem(self) -> AsyncFileSystem:
        """Get or create filesystem instance."""
        if self._fs is None:
            if self.protocol == "gdrive":
                self._fs = fsspec.filesystem(
                    "gdrive",
                    token=os.getenv("GOOGLE_TOKEN"),
                    asynchronous=True
                )
            else:
                self._fs = fsspec.filesystem(self.protocol, asynchronous=True)
            
            # Ensure root path exists
            if not await self._fs.exists(self.root_path):
                await self._fs.makedirs(self.root_path)
        
        return self._fs
    
    async def save_audio(self, name: str, audio: bytes, sample_rate: int, num_channels: int) -> str:
        """Save audio data to storage.
        
        Args:
            name: Base name for the file
            audio: Raw audio data
            sample_rate: Audio sample rate
            num_channels: Number of audio channels
            
        Returns:
            str: Path where the file was saved
        """
        if not audio:
            logger.info("No audio data to save")
            return ""
            
        try:
            # Create WAV file in memory
            with io.BytesIO() as buffer:
                with wave.open(buffer, "wb") as wf:
                    wf.setsampwidth(2)
                    wf.setnchannels(num_channels)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio)
                
                # Generate filename and full path
                filename = f"{name}_recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                full_path = f"{self.root_path}/{filename}"
                
                # Save to cloud storage
                fs = await self._get_filesystem()
                async with await fs.open(full_path, "wb") as f:
                    await f.write(buffer.getvalue())
                
                logger.info(f"Audio saved to {full_path}")
                return full_path
                
        except Exception as e:
            logger.error(f"Error saving audio: {e}")
            return ""
            
    async def list_recordings(self, name: Optional[str] = None) -> list[str]:
        """List available recordings.
        
        Args:
            name: Optional name filter
            
        Returns:
            list[str]: List of recording paths
        """
        try:
            fs = await self._get_filesystem()
            files = await fs.ls(self.root_path)
            
            if name:
                files = [f for f in files if name in f]
                
            return sorted(files)
            
        except Exception as e:
            logger.error(f"Error listing recordings: {e}")
            return []
