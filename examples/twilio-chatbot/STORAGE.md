# Cloud Storage Setup

This application uses cloud storage to save call recordings. By default, it uses Google Drive, but you can easily switch to other providers supported by `fsspec`.

## Setting up Google Drive Storage

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop Application"
   - Download the client configuration file

5. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

6. Generate your token:
   ```python
   import fsspec
   fs = fsspec.filesystem("gdrive", client_secret="path/to/your/client_secrets.json")
   # This will open a browser window for authentication
   # After authenticating, the token will be saved
   ```

7. Add the token to your .env file:
   ```
   GOOGLE_TOKEN=your_token_here
   ```

## Using Other Storage Providers

The storage system uses `fsspec`, which supports many storage providers. To use a different provider:

1. Install the required dependencies for your chosen provider
2. Update the `StorageManager` initialization in `bot.py`:

```python
# For AWS S3
storage = StorageManager(protocol="s3", root_path="your-bucket/recordings")

# For Azure Blob Storage
storage = StorageManager(protocol="abfs", root_path="your-container/recordings")

# For Dropbox
storage = StorageManager(protocol="dropbox", root_path="/recordings")
```

3. Set up the appropriate environment variables for your chosen provider.

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
