# TGForge

**[TGForge](https://isd-tgforge.streamlit.app/)** is an interactive data extraction and analysis tool built using Streamlit and Telegram's official API. It allows users to collect, analyze, and export data from one or more public Telegram channels or groups. With TGForge, you can:

- **Retrieve Channel Information:** Get basic details about channels—including alternative names, channel type, creation date, and reported member counts.
- **Collect Messages:** Fetch all messages from selected channels or groups, with an option to filter by specific date ranges and include or exclude comment threads. Download the data as CSV, Excel, or Markdown for further analysis.
- **Extract Forwards:** Focus on forwarded messages, with similar date filtering and download options.
- **Fetch Participants:** Gather group or channel member information either directly via the API or by extracting active participants from messages. This is ideal for analyzing community engagement and social network interactions.
- **Lookup Users:** Retrieve detailed information about specific users by their ID or username.
- **View Your Subscriptions:** See all channels and groups you're subscribed to on your Telegram account.

This tool was created by and for the Institute for Strategic Dialogue.

Special thanks to Streamlit and Telethon for their support.

---

## Guide

### Prerequisites

**Telegram API Credentials:**
- Obtain your API ID and API Hash from Telegram's official [page](https://core.telegram.org/api/obtaining_api_id)
- For guidance, watch this [overview video](https://www.youtube.com/watch?v=tzYTLjdr7rI) on how to access your API ID and API hash

**Account Considerations:**
- You may use a burner account; however, note that new accounts sometimes cannot obtain API credentials.

---

### Step 1: Enter Telegram API Credentials

**Input Credentials:**
- Enter your API ID, API Hash, and phone number (with country code, e.g., +1234567890) in the provided fields.
- Click the **"Send Verification Code"** button.

**Issues:**
- If you encounter errors (e.g., "database is locked"), click **"Reset Session"** and try again. If issues persist, contact the DAU.
- Note: A successful submission will automatically move you to Step 2 after a few seconds.

---

### Step 2: Authentication

**Check Your Telegram App:**
- Open Telegram on the account associated with your API credentials. You should receive a login code as if you were signing in on a new device.

**Enter the Code:**
- Input the received 5-digit verification code in the app.
- A notification may appear on your phone indicating an attempted login. Rest assured, this is only for authentication purposes and cannot be used to access your account.

**Authenticate:**
- Note: Once authenticated, the app will automatically advance to Step 3.

---

### Step 3: Using TGForge

Once authenticated, you'll have access to several data collection features:

#### **Channel Info**
- **What It Does:** Retrieves basic channel details such as alternative names, type (group/channel), creation date, participant count, verification status, and access information.
- **How to Use:** Enter channel usernames (e.g., `durov, washingtonpost`) and click **"Fetch Channel Data"**.

#### **Messages**
- **What It Does:** Collects all messages from the selected channel(s) or group(s), including text content, media types, engagement metrics (views, forwards, replies), URLs, hashtags, and reactions.
- **How to Use:** 
  - Enter channel usernames separated by commas (e.g., `durov, washingtonpost`).
  - Optionally filter by a specific date range using the date pickers.
  - Choose whether to include comment threads (replies to posts) using the checkbox.
  - Click **"Fetch Messages"**.
- **Output:** 
  - Raw message data available in CSV, Excel, or Markdown format.
  - Analytics workbook (Excel) containing:
    - Top 50 most-viewed posts
    - Top 25 shared domains
    - Top 25 shared URLs
    - Forward counts by origin channel
    - Top 25 hashtags
    - Daily, weekly, and monthly volume charts

#### **Forwards**
- **What It Does:** Similar to message collection but focuses specifically on forwarded messages, including origin channel information and forward timestamps.
- **How to Use:** 
  - Enter channel usernames separated by commas.
  - Optionally filter by date range.
  - Click **"Fetch Forwards"**.
- **Output:** 
  - CSV, Excel, or Markdown export options.
  - Excel includes both raw forwards data and aggregated forward counts by origin channel.

#### **Participants**
- **What It Does:** Retrieves group/channel members and their profile information (username, verification status, premium status, bot status, last seen, etc.).
- **Methods:**
  - **Default:** Pulls participants directly from the Telegram API (fastest, but may not capture all active users in large channels).
  - **Via Messages:** Collects participants based on message activity within an optional date range, supplementing API data. This method also captures users who reply to posts (commenters).
- **How to Use:**
  - Enter group/channel usernames.
  - Select fetch method (Default or Via Messages).
  - If using "Via Messages," optionally specify a date range.
  - Click **"Fetch Participants"**.
- **Output:** 
  - CSV, Excel, or Markdown export options.
  - Excel includes both raw participant data and aggregated view showing which groups each user belongs to.
- **Note:** Large or highly active groups might take longer to process. For extensive data pulls, consider scanning groups one at a time or contact the DAU.

#### **Users**
- **What It Does:** Looks up detailed information about specific Telegram users by their User ID or username.
- **How to Use:**
  - Enter one or more User IDs (numeric) or usernames (with or without @) in the text area, one per line.
  - Click **"Fetch User Data"**.
- **Output:** Displays user profile information including name, username, verification status, premium status, phone number (if available), account status, and more.

#### **Your Subscriptions**
- **What It Does:** Fetches a list of all channels and groups your authenticated account is subscribed to.
- **How to Use:** Click **"Fetch My Subscriptions"**.
- **Output:** 
  - Displays two tables: one for channels you follow, one for groups you're in.
  - Shows channel/group name, username, URL, participant count, and verification status.

---

### Running a Scan

- **Initiate Scan:** After selecting your scan type (Channel Info, Messages, Forwards, Participants, Users, or Subscriptions) and entering the required information, click the respective fetch button.
- **Interrupting a Scan:** Press **"Refresh / Cancel"** to stop an ongoing data pull.
- **Monitoring Progress:** The app displays real-time progress updates showing which date ranges are being processed.

---

### Export Options

After successfully fetching data, you'll see download buttons for exporting in multiple formats:

- **CSV:** Raw data in comma-separated values format (best for large datasets and importing into other tools).
- **Excel (.xlsx):** Formatted spreadsheets with multiple sheets for analytics data. Messages and forwards include comprehensive analytics workbooks.
- **Markdown:** Formatted text tables (limited to first 1,000 rows for readability).

---

### Additional Notes

- **Processing Time:** TGForge is efficient but may take significant time for large data sets. Make sure your computer stays awake and connected to the internet. Loss of internet or going to sleep mode will interrupt a download and you will need to start over. Make sure to save CSV/Excel files if desired, as even once a scan has been completed you may similarly lose your data. For large-scale collection, contact the DAU.
- **Security:** The API credentials you enter are solely for data extraction. They cannot be used to access your account beyond reading public information.
- **Privacy:** Channels or groups do not receive any indication that they have been scanned.
- **Limitations:** TGForge currently works only on public channels and groups. Private channels require you to be a member.
- **Rate Limiting:** The app includes built-in delays to avoid hitting Telegram's rate limits. If you encounter FloodWait errors, the app will automatically retry.
- **Comment Collection:** When enabled for message fetching, the app retrieves up to 100 replies per post. This captures discussion threads and community engagement.
- **Data Deduplication:** Messages with the same "Grouped ID" (media albums) are automatically deduplicated to prevent counting the same content multiple times.
- **Support:** For bugs or feature requests, contact Nathan or a member of the DAU.

---

### Troubleshooting

**"Database is locked" error:**
- Click **"Reset Session"** and try authenticating again.
- Make sure no other instances of TGForge are running on your account.

**Channel not found:**
- Verify the channel username is correct (without the @ symbol).
- Ensure the channel is public.
- Check that you haven't been blocked from viewing the channel.

**Authentication failures:**
- Verify your phone number includes the country code (e.g., +1 for US).
- Make sure you're entering the code from the correct Telegram account.
- API credentials must be from the same account you're authenticating with.

**Long processing times:**
- Large channels with thousands of messages may take several minutes or longer.
- The app shows progress updates—watch for date ranges being processed.
- Consider using date filters to scan specific time periods rather than entire channel history.

**Missing participants:**
- Some large channels may not expose their full member list via the API.
- Try the "Via Messages" method to capture active participants based on posting activity.
- Note that "Via Messages" is slower but more comprehensive for identifying active users.




















