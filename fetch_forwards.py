# fetch_forwards.py
import pandas as pd
import time
import streamlit as st
from telethon.errors import FloodWaitError, RpcCallFailError
from typing import Dict, Any

# ==================== FORWARD PROCESSOR CLASS ====================
class ForwardProcessor:
    """Processes forwarded messages into structured data"""
    
    def __init__(self, channel):
        self.channel = channel
        self.channel_name = channel.title if hasattr(channel, 'title') else str(channel)
        self.channel_username = getattr(channel, 'username', None)
    
    def extract_forward_info(self, message) -> Dict[str, Any]:
        """Extract information about the forward origin"""
        if not message.forward:
            return None
        
        original_url = "No URL available"
        original_username = "Unknown"
        original_chat_name = "Unknown"
        
        if message.forward.chat:
            original_chat_name = message.forward.chat.title or "Unknown"
            if hasattr(message.forward.chat, "username"):
                original_username = message.forward.chat.username or "Unknown"
                if message.forward.channel_post:
                    original_url = f"https://t.me/{original_username}/{message.forward.channel_post}"
        
        return {
            'username': original_username,
            'chat_name': original_chat_name,
            'url': original_url,
            'chat_id': message.forward.chat_id if message.forward else "Unknown"
        }
    
    def build_forward_url(self, message_id: int) -> str:
        """Construct URL for the forwarded message"""
        if self.channel_username:
            return f"https://t.me/{self.channel_username}/{message_id}"
        return "No URL available"
    
    def process_forward(self, message) -> Dict[str, Any]:
        """Convert a forwarded message to structured data"""
        if not message.forward:
            return None
        
        forward_info = self.extract_forward_info(message)
        
        return {
            "Channel": self.channel_name,
            "Message DateTime (UTC)": (
                message.forward.date.replace(tzinfo=None) 
                if message.forward and message.forward.date 
                else "Not Available"
            ),
            "Forward Datetime (UTC)": (
                message.date.replace(tzinfo=None) 
                if message.date 
                else "Not Available"
            ),
            "Origin Username": forward_info['username'],
            "Origin Chat Name": forward_info['chat_name'],
            "Text": message.text,
            "Forwarded Chat ID": forward_info['chat_id'],
            "Reply To": message.reply_to_msg_id if message.reply_to_msg_id else "No Reply",
            "Replies": message.replies.replies if message.replies else "No Replies",
            "Views": message.views if message.views else "Not Available",
            "Forwards": message.forwards if message.forwards else "Not Available",
            "Message Type": type(message.media).__name__ if message.media else "Text",
            "Forwarded URL": self.build_forward_url(message.id),
            "Origin URL": forward_info['url'],
            "Grouped ID": str(message.grouped_id) if message.grouped_id else "Not Available",
        }


# ==================== MAIN FETCH FUNCTION ====================
async def fetch_forwards(client, channel_list, start_date=None, end_date=None):
    """Fetches forwarded messages from a list of channels, with optional date range filtering."""
    all_messages_data = []
    limit = 1000

    for channel_name in channel_list:
        try:
            channel = await client.get_entity(channel_name)
            processor = ForwardProcessor(channel)  # Create processor for this channel
            
            progress_text = st.empty()
            progress_text.write(f"Processing channel: **{channel_name}**")
            offset_id = 0
            total_messages = []
        except ValueError:
            st.error(f"Channel '{channel_name}' does not exist. Skipping.")
            continue

        try:
            # Fetch messages in batches
            while True:
                messages = await client.get_messages(channel, limit=limit, offset_id=offset_id)
                if not messages:
                    progress_text.write("No more messages in this batch.")
                    break

                # Update progress
                first_date = messages[0].date.replace(tzinfo=None) if messages[0].date else "Unknown"
                last_date = messages[-1].date.replace(tzinfo=None) if messages[-1].date else "Unknown"
                progress_text.write(f"Processing messages from {first_date.date()} to {last_date.date()}")
                
                stop_fetching = False
                
                # Filter messages by date range
                for message in messages:
                    message_datetime = message.date.replace(tzinfo=None) if message.date else None
                    
                    # Stop if we've gone past the start date
                    if start_date and message_datetime and message_datetime.date() < start_date:
                        progress_text.write("Reached messages older than the start date.")
                        stop_fetching = True
                        break

                    # Add messages within date range
                    if ((not start_date or (message_datetime and message_datetime.date() >= start_date)) and 
                        (not end_date or (message_datetime and message_datetime.date() <= end_date))):
                        total_messages.append(message)

                if stop_fetching:
                    break

                offset_id = messages[-1].id if messages else offset_id
                time.sleep(1)

                # Check for cancellation
                if st.session_state.get("cancel_fetch", False):
                    progress_text.write("Canceled by user.")
                    break

            # Process messages using the class - MUCH CLEANER!
            messages_data = []
            for message in total_messages:
                if message.forward:
                    forward_data = processor.process_forward(message)
                    if forward_data:
                        messages_data.append(forward_data)

            progress_text.write(f"Collected {len(messages_data)} forwards (out of {len(total_messages)} messages) for channel {channel_name}.")
            all_messages_data.extend(messages_data)

        except Exception as e:
            progress_text.write(f"Error fetching forwards for {channel_name}: {e}")

    # Convert to DataFrame
    df = pd.DataFrame(all_messages_data)

    # Deduplicate based on Grouped ID
    dedup_df = df[df["Grouped ID"] != "Not Available"].drop_duplicates(subset=["Grouped ID"], keep="first")
    df = pd.concat([
        df[df["Grouped ID"] == "Not Available"], 
        dedup_df
    ]).sort_values(by=["Channel", "Message DateTime (UTC)"]).reset_index(drop=True)

    # Generate forward counts
    fwd_counts_df = df.groupby(["Channel", "Origin Username"]).size().reset_index(name="Count")
    fwd_counts_df = fwd_counts_df.pivot(index="Origin Username", columns="Channel", values="Count").fillna(0)
    fwd_counts_df["Total Forwards"] = fwd_counts_df.sum(axis=1)
    fwd_counts_df = fwd_counts_df.sort_values(by="Total Forwards", ascending=False).reset_index()
    return df, fwd_counts_df
