"""
Storage module for managing audio recordings using fsspec and gcsfs.
"""
import os
import io
import wave
import datetime
import logging
import json
from typing import Optional
import fsspec
from gcsfs import GCSFileSystem
import aiofiles

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages storage of audio recordings using fsspec and gcsfs."""
    
    def __init__(self, protocol: str = "gcs", root_path: str = "recordings"):
        """Initialize storage manager.
        
        Args:
            protocol: Storage protocol to use ('gcs' for Google Cloud Storage/Drive)
            root_path: Root path in the storage where files will be saved
        """
        self.protocol = protocol
        self.root_path = root_path
        self._fs: Optional[GCSFileSystem] = None
        
        # Ensure we have required credentials
        if protocol == "gcs":
            token = os.getenv("GOOGLE_TOKEN")
            if not token:
                raise ValueError("GOOGLE_TOKEN environment variable required for Google storage")
            try:
                # Validate token is proper JSON
                self.token_dict = json.loads(token)
            except json.JSONDecodeError:
                raise ValueError("GOOGLE_TOKEN must be a valid JSON string")
        
    async def _get_filesystem(self) -> GCSFileSystem:
        """Get or create filesystem instance."""
        if self._fs is None:
            if self.protocol == "gcs":
                self._fs = GCSFileSystem(token=self.token_dict)
            else:
                self._fs = fsspec.filesystem(self.protocol)
            
            # Ensure root path exists
            if not self._fs.exists(self.root_path):
                self._fs.makedirs(self.root_path)
        
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
                with fs.open(full_path, "wb") as f:
                    f.write(buffer.getvalue())
                
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
            files = fs.ls(self.root_path)
            
            if name:
                files = [f for f in files if name in f]
                
            return sorted(files)
            
        except Exception as e:
            logger.error(f"Error listing recordings: {e}")
            return []
