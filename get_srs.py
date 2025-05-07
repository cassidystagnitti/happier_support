import requests
import pandas as pd
import sys
import csv
import time
import os
import json

# Get bearer token from arguments
if len(sys.argv) < 2:
    print("Usage: python get_saved_replies.py BEARER_TOKEN")
    sys.exit(1)

BEARER_TOKEN = sys.argv[1]
BATCH_SIZE = 10  # Number of items to process per batch
RATE_LIMIT_PAUSE = 3  # Seconds to wait between API calls
CHECKPOINT_FILE = "saved_replies_checkpoint.json"

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {
        "mailboxes_fetched": False,
        "processed_mailboxes": [],
        "processed_replies": [],
        "all_replies": []
    }

def save_checkpoint(checkpoint):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f)

def get_all_mailboxes():
    url = "https://api.helpscout.net/v2/mailboxes"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    time.sleep(RATE_LIMIT_PAUSE)  # Avoid rate limiting
    
    if response.status_code != 200:
        print(f"Error fetching mailboxes: {response.status_code}")
        print(response.text)
        return []
    
    data = response.json()
    return data.get('_embedded', {}).get('mailboxes', [])

def get_saved_reply_ids_for_mailbox(mailbox_id):
    url = f"https://api.helpscout.net/v2/mailboxes/{mailbox_id}/saved-replies"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    time.sleep(RATE_LIMIT_PAUSE)  # Avoid rate limiting
    
    if response.status_code != 200:
        print(f"Error listing saved replies for mailbox {mailbox_id}: {response.status_code}")
        print(response.text)
        return []
    
    # Parse response based on format
    if isinstance(response.json(), list):
        return [(item['id'], mailbox_id) for item in response.json()]
    else:
        embedded = response.json().get('_embedded', {}).get('savedReplies', [])
        return [(item['id'], mailbox_id) for item in embedded]

def get_saved_reply_detail(mailbox_id, reply_id):
    url = f"https://api.helpscout.net/v2/mailboxes/{mailbox_id}/saved-replies/{reply_id}"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    time.sleep(RATE_LIMIT_PAUSE)  # Avoid rate limiting
    
    if response.status_code != 200:
        print(f"Error fetching saved reply {reply_id}: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

# Load checkpoint to resume if interrupted
checkpoint = load_checkpoint()

# Get all mailboxes if not already fetched
mailboxes = []
if not checkpoint["mailboxes_fetched"]:
    print("Fetching all mailboxes...")
    mailboxes = get_all_mailboxes()
    if mailboxes:
        checkpoint["mailboxes_fetched"] = True
        save_checkpoint(checkpoint)

if not mailboxes and checkpoint["mailboxes_fetched"]:
    # Load mailboxes from existing data
    for reply in checkpoint["all_replies"]:
        mailbox_info = {
            "id": reply["mailboxId"],
            "name": reply["mailboxName"]
        }
        if mailbox_info not in mailboxes:
            mailboxes.append(mailbox_info)

if not mailboxes:
    print("No mailboxes found or error occurred.")
    sys.exit(1)

# Get all saved reply IDs from all mailboxes
all_reply_ids = []
for mailbox in mailboxes:
    mailbox_id = mailbox['id']
    
    # Skip if we've already processed this mailbox
    if mailbox_id in checkpoint["processed_mailboxes"]:
        print(f"Skipping already processed mailbox: {mailbox['name']} (ID: {mailbox_id})")
        continue
        
    print(f"Fetching saved reply IDs for mailbox: {mailbox['name']} (ID: {mailbox_id})")
    reply_ids = get_saved_reply_ids_for_mailbox(mailbox_id)
    all_reply_ids.extend(reply_ids)
    
    # Mark this mailbox as processed
    checkpoint["processed_mailboxes"].append(mailbox_id)
    save_checkpoint(checkpoint)

# Filter out reply IDs we've already processed
all_reply_ids = [
    (reply_id, mailbox_id) for reply_id, mailbox_id in all_reply_ids 
    if (reply_id, mailbox_id) not in checkpoint["processed_replies"]
]

# Load already processed replies
all_replies = checkpoint["all_replies"]

# Process in batches
for i in range(0, len(all_reply_ids), BATCH_SIZE):
    batch = all_reply_ids[i:i+BATCH_SIZE]
    print(f"Processing batch {i//BATCH_SIZE + 1}/{(len(all_reply_ids) + BATCH_SIZE - 1)//BATCH_SIZE}: " +
          f"replies {i+1}-{min(i+BATCH_SIZE, len(all_reply_ids))}")
    
    for reply_id, mailbox_id in batch:
        print(f"Fetching details for saved reply ID: {reply_id}")
        
        try:
            reply = get_saved_reply_detail(mailbox_id, reply_id)
            if reply:
                # Add mailbox ID to the reply data
                reply['mailboxId'] = mailbox_id
                # Find mailbox name
                mailbox_name = next((mb['name'] for mb in mailboxes if mb['id'] == mailbox_id), 'Unknown')
                reply['mailboxName'] = mailbox_name
                all_replies.append(reply)
        except Exception as e:
            print(f"Error processing reply {reply_id}: {str(e)}")
        
        # Mark this reply as processed
        checkpoint["processed_replies"].append((reply_id, mailbox_id))
        checkpoint["all_replies"] = all_replies
        save_checkpoint(checkpoint)

if not all_replies:
    print("Failed to fetch details for any saved replies.")
    sys.exit(1)

# Save to CSV
df = pd.DataFrame(all_replies)
df.to_csv('saved_replies.csv', index=False, quoting=csv.QUOTE_ALL)
df.to_csv('saved_replies.tsv', index=False, sep='\t', quoting=csv.QUOTE_ALL)

print(f"Successfully exported {len(all_replies)} saved replies to CSV and TSV files.")

# Cleanup checkpoint if successful
if os.path.exists(CHECKPOINT_FILE):
    os.remove(CHECKPOINT_FILE)