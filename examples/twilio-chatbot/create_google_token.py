from google_auth_oauthlib.flow import InstalledAppFlow
import json

# Define the scopes we need
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # Access to files created by the app
    'https://www.googleapis.com/auth/drive.appdata'  # Access to app-specific folder
]

# Create the flow
flow = InstalledAppFlow.from_client_secrets_file(
    'F:\\Projects\\client_secret_kornevson.json',
    scopes=SCOPES
)

# Run the flow on a specific port
creds = flow.run_local_server(port=8090)

# Convert credentials to a token dictionary
token_dict = {
    'token': creds.token,
    'refresh_token': creds.refresh_token,
    'token_uri': creds.token_uri,
    'client_id': creds.client_id,
    'client_secret': creds.client_secret,
    'scopes': creds.scopes
}

# Convert to JSON string
token_json = json.dumps(token_dict)

print("Add this token to your .env file:")
print("GOOGLE_TOKEN='" + token_json + "'")