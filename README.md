# Hotel Ratanakiri — Maintenance Bot

## Deploy on Railway (free)

### 1. Create Railway account
Go to railway.app and sign up with GitHub.

### 2. Upload this folder to GitHub
- Create a new repo on github.com
- Upload bot.py, requirements.txt, Procfile

### 3. Deploy on Railway
- New Project → Deploy from GitHub repo
- Select your repo

### 4. Set environment variables on Railway
Go to your project → Variables → Add:

| Variable | Value |
|---|---|
| BOT_TOKEN | Your token from @BotFather |
| MANAGER_CHAT_ID | Your Telegram ID (get from @userinfobot) |
| SPREADSHEET_ID | ID from your Google Sheet URL |
| GOOGLE_CREDS_JSON | Service account JSON (see step 5) |

### 5. Google Service Account (to write to Sheets)
1. Go to console.cloud.google.com
2. Create a project
3. Enable Google Sheets API
4. Create a Service Account → download JSON key
5. Copy the entire JSON content → paste as GOOGLE_CREDS_JSON variable
6. In your Google Sheet → Share → add the service account email (from JSON) as Editor

### 6. Test
Send /start to your bot on Telegram.
