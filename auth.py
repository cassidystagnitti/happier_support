import requests
import base64
import sys

# Get credentials from arguments
if len(sys.argv) < 3:
    print("Usage: python script.py API_ID API_SECRET")
    sys.exit(1)

API_ID = sys.argv[1]
API_SECRET = sys.argv[2]

# Base64 encode credentials
credentials = f"{API_ID}:{API_SECRET}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()

# Get token using client credentials flow
token_url = "https://api.helpscout.net/v2/oauth2/token"
token_payload = {
    "grant_type": "client_credentials"
}
token_headers = {
    "Authorization": f"Basic {encoded_credentials}"
}

response = requests.post(token_url, data=token_payload, headers=token_headers)

if response.status_code == 200:
    access_token = response.json().get("access_token")
    print(f"Bearer {access_token}")
else:
    print("Error:", response.text)