# Cloud Storage Setup

This application uses Google Cloud Storage to save call recordings. The implementation uses `gcsfs`, which provides a simple interface to Google Cloud Storage.

## Setting up Google Storage

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the token generation script:
   ```bash
   python create_google_token.py
   ```
   This will:
   - Open your browser for Google authentication
   - Generate a token after you authorize the application
   - Print the token to add to your .env file

3. Add the token to your .env file:
   ```
   GOOGLE_TOKEN={"token": "your_token_here", ...}
   ```
   Make sure to copy the entire JSON object as shown in the script output.

## Accessing Stored Recordings

You can list and access your recordings programmatically:

```python
from storage import StorageManager

storage = StorageManager()
recordings = await storage.list_recordings()
print("Available recordings:", recordings)

# Filter by name
user_recordings = await storage.list_recordings(name="user123")
print("User recordings:", user_recordings)
```

## Storage Location

Recordings are stored in a `recordings` directory in your Google Cloud Storage. Each recording is named with the format:
```
recordings/{name}_recording_{timestamp}.wav
```

You can access these files through:
1. The Google Cloud Console
2. The Google Drive web interface
3. Programmatically using the StorageManager class
