# fetch_subscriptions.py
from telethon.tl.types import Channel
import streamlit as st

async def fetch_user_subscriptions(client):
    """Fetches all channels and groups the authenticated user is subscribed to."""
    try:
        dialogs = await client.get_dialogs()
        
        channels = []
        groups = []
        
        for dialog in dialogs:
            # Check if cancelled
            if st.session_state.get("cancel_fetch", False):
                st.warning("Fetch cancelled by user.")
                break
                
            if isinstance(dialog.entity, Channel):
                channel_info = {
                    'ID': dialog.entity.id,
                    'Title': dialog.entity.title,
                    'Username': f"@{dialog.entity.username}" if dialog.entity.username else "No Username",
                    'URL': f"https://t.me/{dialog.entity.username}" if dialog.entity.username else "Private/No URL",
                    'Type': "Channel" if dialog.entity.broadcast else "Supergroup",
                    'Participants': getattr(dialog.entity, 'participants_count', 'N/A'),
                    'Verified': "Yes" if dialog.entity.verified else "No",
                    'Scam': "Yes" if dialog.entity.scam else "No",
                    'Restricted': "Yes" if dialog.entity.restricted else "No",
                    'Access Hash': dialog.entity.access_hash,
                }
                
                if dialog.entity.broadcast:
                    channels.append(channel_info)
                else:
                    groups.append(channel_info)
        
        return channels, groups
        
    except Exception as e:
        st.error(f"Error fetching subscriptions: {e}")
        return [], []
