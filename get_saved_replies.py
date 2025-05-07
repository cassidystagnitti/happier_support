import requests
import pandas as pd
import sys
import csv

# Get bearer token from arguments
if len(sys.argv) < 2:
    print("Usage: python get_saved_replies.py BEARER_TOKEN")
    sys.exit(1)

BEARER_TOKEN = sys.argv[1]

def get_all_mailboxes():
    url = "https://api.helpscout.net/v2/mailboxes"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching mailboxes: {response.status_code}")
        print(response.text)
        return []
    
    data = response.json()
    return data.get('_embedded', {}).get('mailboxes', [])

def get_saved_replies_for_mailbox(mailbox_id):
    url = f"https://api.helpscout.net/v2/mailboxes/{mailbox_id}/saved-replies"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching saved replies for mailbox {mailbox_id}: {response.status_code}")
        print(response.text)
        return []
    
    return response.json()

# First get all mailboxes
mailboxes = get_all_mailboxes()

if not mailboxes:
    print("No mailboxes found or error occurred.")
    sys.exit(1)

# Get saved replies for each mailbox
all_replies = []
for mailbox in mailboxes:
    mailbox_id = mailbox['id']
    mailbox_name = mailbox['name']
    print(f"Fetching saved replies for mailbox: {mailbox_name} (ID: {mailbox_id})")
    
    replies = get_saved_replies_for_mailbox(mailbox_id)
    
    # If the response directly contains a list instead of _embedded
    if isinstance(replies, list):
        for reply in replies:
            reply['mailboxId'] = mailbox_id
            reply['mailboxName'] = mailbox_name
        all_replies.extend(replies)
    else:
        # Handle standard _embedded format if present
        embedded_replies = replies.get('_embedded', {}).get('savedReplies', [])
        for reply in embedded_replies:
            reply['mailboxId'] = mailbox_id
            reply['mailboxName'] = mailbox_name
        all_replies.extend(embedded_replies)

if not all_replies:
    print("No saved replies found across any mailboxes.")
    sys.exit(1)

# Save to CSV
df = pd.DataFrame(all_replies)
df.to_csv('saved_replies.csv', index=False, quoting=csv.QUOTE_ALL)
df.to_csv('saved_replies.tsv', index=False, sep='\t', quoting=csv.QUOTE_ALL)

print(f"Successfully exported {len(all_replies)} saved replies to CSV and TSV files.")