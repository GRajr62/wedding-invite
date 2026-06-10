# WhatsApp Wedding Invite Sender

This reads guests from two Google Sheet tabs, sends different WhatsApp invitation templates and attachments using WhatsApp Web through Playwright, then updates a `Status` column after a successful send.

## Files

- `send_invites.py` - main script
- `config.example.json` - copy this to `config.json` and edit your values
- `attachments/` - put the wedding and reception invitation files here
- `credentials/` - put your Google service account JSON here

## Setup

1. Create a Google Cloud service account and enable the Google Sheets API.
2. Download the service account key JSON.
3. Share your Google Sheet with the service account email as an editor.
4. Copy `config.example.json` to `config.json`.
5. Put the service account JSON at `credentials/service-account.json`.
6. Put your invitation files in `attachments/` and update the attachment paths in `config.json`.
7. Confirm your tab names. The config uses `Wedding` and `Reception`; change them if your tabs are lowercase `wedding` and `reception`.
8. Install dependencies:

```powershell
cd wedding_invite_sender_whatsapp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

## Run

First do a dry run:

```powershell
python send_invites.py --config config.json --dry-run
```

Then send:

```powershell
python send_invites.py --config config.json
```

WhatsApp Web will open. Scan the QR code the first time. The script stores that login in `.chrome-profile`.

## Google Sheet Format

Each tab should have a header row. These column names are supported:

- name: `Name`, `Full Name`, or `Guest Name`
- phone: `Phone`, `Phone Number`, `Mobile`, `Mobile Number`, or `WhatsApp`
- status: `Status`

If `Status` does not exist, the script creates it. Rows whose status starts with `Sent` are skipped.

Templates can use column names inside braces, for example `{Name}` or `{Phone Number}`.

## Notes

WhatsApp Web UI changes from time to time. If sending starts failing at the attach or send step, the selectors in `send_invites.py` may need a small update.
