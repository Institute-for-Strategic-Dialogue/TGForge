# fetch_messages.py
import pandas as pd
import time
import re
from collections import Counter
from urllib.parse import urlparse
from telethon.errors import FloodWaitError
from telethon import functions
import streamlit as st
from tenacity import retry, stop_after_attempt, retry_if_exception_type
from typing import Optional, Dict, Any

# ==================== MESSAGE PROCESSOR CLASS ====================
class MessageProcessor:
    """Processes Telegram messages into structured data"""
    
    def __init__(self, channel):
        self.channel = channel
        self.channel_name = channel.title if hasattr(channel, 'title') else str(channel)
        self.channel_username = getattr(channel, 'username', None)
        self.participant_count = participant_count
    
    def extract_sender_info(self, message) -> Dict[str, Any]:
        """Extract sender user ID and username"""
        if message.sender:
            return {
                'user_id': getattr(message.sender, "id", "Not Available"),
                'username': getattr(message.sender, "username", "Not Available")
            }
        else:
            return {
                'user_id': getattr(self.channel, "id", "Not Available"),
                'username': getattr(self.channel, "username", "Not Available")
            }
    
    def extract_urls(self, text: Optional[str]) -> list:
        """Extract URLs from message text"""
        if not text:
            return []
        return re.findall(r"(https?://\S+)", text)
    
    def extract_hashtags(self, text: Optional[str]) -> list:
        """Extract hashtags from message text"""
        if not text:
            return []
        return [tag for tag in text.split() if tag.startswith("#")]
    
    def extract_reactions(self, message) -> int:
        """Count total reactions on a message"""
        if not message.reactions:
            return 0
        return sum([reaction.count for reaction in message.reactions.results])

    def calculate_total_engagement(self, message) -> int:
        """Calculate total engagement (reactions + replies + forwards)"""
        reactions = self.extract_reactions(message)
        replies = message.replies.replies if message.replies else 0
        forwards = message.forwards if message.forwards else 0
        return reactions + replies + forwards
        
    def extract_geo_location(self, message) -> str:
        """Extract geo-location if available"""
        if message.geo:
            return f"{message.geo.lat}, {message.geo.long}"
        return "None"
    
    def extract_forward_origin(self, message) -> str:
        """Extract original username for forwarded messages"""
        if not message.forward:
            return "Not Available"
        
        try:
            if message.forward.chat and hasattr(message.forward.chat, "username"):
                return message.forward.chat.username
        except AttributeError:
            pass
        
        return "Unknown"
    
    def build_message_url(self, message_id: int) -> str:
        """Construct message URL"""
        if self.channel_username:
            return f"https://t.me/{self.channel_username}/{message_id}"
        return "No URL available"
    
    def process_message(self, message, parent_id: Optional[int] = None) -> Dict[str, Any]:
        """Convert a Telegram message to a structured dictionary"""
        sender_info = self.extract_sender_info(message)
        
        return {
            "Channel": self.channel_name,
            "Subscribers": self.participant_count,
            "Message ID": message.id,
            "Parent Message ID": parent_id,
            "Sender User ID": sender_info['user_id'],
            "Sender Username": sender_info['username'],
            "Message DateTime (UTC)": message.date.replace(tzinfo=None) if message.date else "Not Available",
            "Text": message.text,
            "Message Type": type(message.media).__name__ if message.media else "Text",
            "Is Forward": bool(message.forward),
            "Origin Username": self.extract_forward_origin(message),
            "Geo-location": self.extract_geo_location(message),
            "Hashtags": self.extract_hashtags(message.text),
            "URLs Shared": self.extract_urls(message.text),
            "Reactions": self.extract_reactions(message),
            "Message URL": self.build_message_url(message.id),
            "Views": message.views if message.views else None,
            "Forwards": message.forwards if message.forwards else None,
            "Replies": message.replies.replies if message.replies else "No Replies",
            "Total Engagement": self.calculate_total_engagement(message),
            "Reply To Message Snippet": None,
            "Reply To Message Sender": None,
            "Grouped ID": str(message.grouped_id) if message.grouped_id else "Not Available",
            "Platform": "Telegram",
        }
    
    def process_reply(self, reply, parent_message) -> Dict[str, Any]:
        """Process a reply/comment with context from parent message"""
        reply_data = self.process_message(reply, parent_id=parent_message.id)
        
        # Add reply-specific fields
        reply_data["Reply To Message Snippet"] = (
            parent_message.text[:100] + "..." if parent_message.text else "No Text"
        )
        reply_data["Reply To Message Sender"] = (
            parent_message.sender.username 
            if parent_message.sender and hasattr(parent_message.sender, "username") 
            else "Not Available"
        )
        
        return reply_data


# ==================== MESSAGE ANALYTICS CLASS ====================
class MessageAnalytics:
    """Handles all analytics processing for messages"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
    
    def process_hashtags(self) -> pd.DataFrame:
        """Extract and count top hashtags"""
        self.df["Hashtags"] = self.df["Hashtags"].apply(lambda x: x if isinstance(x, list) else [])
        hashtags_list = self.df["Hashtags"].explode().dropna().tolist()
        hashtags_counter = Counter(hashtags_list)
        return pd.DataFrame(
            hashtags_counter.items(), 
            columns=["Hashtag", "Count"]
        ).sort_values(by="Count", ascending=False).head(50)
    
    def process_urls(self) -> pd.DataFrame:
        """Extract and count top URLs"""
        self.df["URLs Shared"] = self.df["URLs Shared"].apply(lambda x: x if isinstance(x, list) else [])
        
        # Flatten and normalize URLs
        urls_list = [
            re.sub(r"[),]+$", "", re.sub(r"^https?://(www\.)?", "", url)).rstrip(".,)").lower()
            for url in self.df["URLs Shared"].explode().dropna().tolist()
        ]
        
        urls_counter = Counter(urls_list)
        return pd.DataFrame(
            urls_counter.items(), 
            columns=["URL", "Count"]
        ).sort_values(by="Count", ascending=False).head(50)
    
    def process_domains(self) -> pd.DataFrame:
        """Extract and count top domains from URLs"""
        self.df["URLs Shared"] = self.df["URLs Shared"].apply(lambda x: x if isinstance(x, list) else [])
        
        domains_list = [
            re.sub(r"[^\w.-]+$", "", re.sub(r"^www\.", "", urlparse(url).netloc)).lower()
            for url in self.df["URLs Shared"].explode().dropna().tolist()
            if urlparse(url).netloc
        ]
        
        domains_counter = Counter(domains_list)
        return pd.DataFrame(
            domains_counter.items(), 
            columns=["Domain", "Count"]
        ).sort_values(by="Count", ascending=False).head(50)
    
    def process_forwards(self) -> pd.DataFrame:
        """Calculate forward counts by channel and origin"""
        fwd_df = self.df[self.df["Is Forward"] == True]
        fwd_df = fwd_df[~fwd_df["Origin Username"].isin(["Unknown", "Not Available"])]
        
        fwd_counts_df = fwd_df.groupby(["Channel", "Origin Username"]).size().reset_index(name="Count")
        fwd_counts_df = fwd_counts_df.pivot(index="Origin Username", columns="Channel", values="Count").fillna(0)
        
        fwd_counts_df["Total Forwards"] = fwd_counts_df.sum(axis=1)
        fwd_counts_df = fwd_counts_df.sort_values(by="Total Forwards", ascending=False).reset_index()
        
        return fwd_counts_df
    
    def generate_daily_volume(self, start_date=None, end_date=None) -> pd.DataFrame:
        """Generate daily message counts per channel"""
        self.df["Message DateTime (UTC)"] = pd.to_datetime(self.df["Message DateTime (UTC)"])
        self.df["Date"] = self.df["Message DateTime (UTC)"].dt.date
        
        daily_counts = self.df.groupby(["Date", "Channel"]).size().reset_index(name="Total")
        daily_counts["Date"] = pd.to_datetime(daily_counts["Date"])
        
        # Determine date range
        range_start = pd.Timestamp(start_date) if start_date else daily_counts["Date"].min()
        range_end = pd.Timestamp(end_date) if end_date else daily_counts["Date"].max()
        
        # Fill missing dates
        full_range = pd.date_range(start=range_start, end=range_end, freq="D")
        daily_counts_pivot = daily_counts.pivot(index="Date", columns="Channel", values="Total").fillna(0)
        daily_counts_pivot = daily_counts_pivot.reindex(full_range, fill_value=0)
        daily_counts_pivot = daily_counts_pivot.reset_index().rename(columns={"index": "Date"})
        
        return daily_counts_pivot
    
    def generate_weekly_volume(self, start_date=None, end_date=None) -> pd.DataFrame:
        """Generate weekly message counts per channel"""
        self.df["Message DateTime (UTC)"] = pd.to_datetime(self.df["Message DateTime (UTC)"])
        self.df["Week"] = self.df["Message DateTime (UTC)"].dt.to_period("W-MON").dt.start_time
        
        weekly_counts = self.df.groupby(["Week", "Channel"]).size().reset_index(name="Total")
        weekly_counts["Week"] = pd.to_datetime(weekly_counts["Week"])
        
        range_start = pd.Timestamp(start_date) if start_date else weekly_counts["Week"].min()
        range_end = pd.Timestamp(end_date) if end_date else weekly_counts["Week"].max()
        
        full_range = pd.date_range(start=range_start, end=range_end, freq="W-TUE")
        
        weekly_counts_pivot = weekly_counts.pivot(index="Week", columns="Channel", values="Total")
        weekly_counts_pivot = weekly_counts_pivot.reindex(full_range, fill_value=0)
        weekly_counts_pivot = weekly_counts_pivot.reset_index().rename(columns={"index": "Week"})
        
        return weekly_counts_pivot
    
    def generate_monthly_volume(self, start_date=None, end_date=None) -> pd.DataFrame:
        """Generate monthly message counts per channel"""
        self.df["Message DateTime (UTC)"] = pd.to_datetime(self.df["Message DateTime (UTC)"])
        self.df["Year-Month"] = self.df["Message DateTime (UTC)"].dt.to_period("M").dt.start_time
        
        monthly_counts = self.df.groupby(["Year-Month", "Channel"]).size().reset_index(name="Total")
        monthly_counts["Year-Month"] = pd.to_datetime(monthly_counts["Year-Month"])
        
        range_start = pd.Timestamp(start_date) if start_date else monthly_counts["Year-Month"].min()
        range_end = pd.Timestamp(end_date) if end_date else monthly_counts["Year-Month"].max()
        
        full_range = pd.date_range(start=range_start, end=range_end, freq="MS")
        
        monthly_counts_pivot = monthly_counts.pivot(index="Year-Month", columns="Channel", values="Total").fillna(0)
        monthly_counts_pivot = monthly_counts_pivot.reindex(full_range, fill_value=0)
        monthly_counts_pivot = monthly_counts_pivot.reset_index().rename(columns={"index": "Year-Month"})
        
        return monthly_counts_pivot
    
    def get_all_analytics(self, start_date=None, end_date=None) -> tuple:
        """Run all analytics and return results"""
        return (
            self.process_hashtags(),
            self.process_urls(),
            self.process_domains(),
            self.process_forwards(),
            self.generate_daily_volume(start_date, end_date),
            self.generate_weekly_volume(start_date, end_date),
            self.generate_monthly_volume(start_date, end_date)
        )


# ==================== MAIN FETCH FUNCTION ====================
@retry(
    retry=retry_if_exception_type(FloodWaitError),
    wait=lambda retry_state: retry_state.outcome.exception().seconds + 1 if isinstance(retry_state.outcome.exception(), FloodWaitError) else 1,
    stop=stop_after_attempt(5)
)
async def fetch_messages(client, channel_list, start_date=None, end_date=None, include_comments=True):
    """
    Fetch messages from Telegram channels with optional date filtering and comment inclusion
    
    Args:
        client: Telethon client instance
        channel_list: List of channel usernames to fetch from
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        include_comments: Whether to fetch comment/reply threads
        
    Returns:
        Tuple of (dataframe, hashtags, urls, domains, forwards, daily_vol, weekly_vol, monthly_vol)
    """
    all_messages_data = []
    limit = 1000
    
    for channel_name in channel_list:
        try:
            channel = await client.get_entity(channel_name)
            
            # Fetch follower count once per channel
            try:
                result = await client(functions.channels.GetFullChannelRequest(channel=channel))
                participant_count = result.full_chat.participants_count if hasattr(result.full_chat, "participants_count") else None
            except Exception as e:
                st.warning(f"Could not fetch follower count for {channel_name}: {e}")
                participant_count = None
            
            processor = MessageProcessor(channel, participant_count)
            
            progress_text = st.empty()
            progress_text.write(f"Processing channel: **{channel_name}** ({participant_count:,} followers)" if participant_count else f"Processing channel: **{channel_name}**")
            offset_id = 0
            total_messages = []
        except ValueError:
            st.error(f"Channel '**{channel_name}**' does not exist. Skipping.")
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
                progress_text.write(f"Processing messages for **{channel_name}** from {first_date.date()} to {last_date.date()}")
                
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

            progress_text.write(f"Collected {len(total_messages)} messages for channel **{channel_name}**")
            
            # Process all collected messages
            messages_data = []
            for message in total_messages:
                # Process main message using the class
                message_data = processor.process_message(message)
                messages_data.append(message_data)
                
                # Fetch and process replies if enabled
                if include_comments and message.replies and message.replies.replies > 0:
                    try:
                        replies = await client.get_messages(channel, reply_to=message.id, limit=100)
                        progress_text.write(f" Processing replies for message ID {message.id}")
                        
                        for reply in replies:
                            reply_data = processor.process_reply(reply, message)
                            messages_data.append(reply_data)
                            
                    except Exception as e:
                        progress_text.write(f"Error fetching replies for message {message.id}: {e}")
            
            all_messages_data.extend(messages_data)

        except Exception as e:
            progress_text.write(f"Error fetching messages for {channel_name}: {e}")

    # Convert to DataFrame
    df = pd.DataFrame(all_messages_data)
    
    # Deduplicate based on Grouped ID
    dedup_df = df[df["Grouped ID"] != "Not Available"].drop_duplicates(subset=["Grouped ID"], keep="first")
    df = pd.concat([
        df[df["Grouped ID"] == "Not Available"], 
        dedup_df
    ]).sort_values(by=["Channel", "Message DateTime (UTC)"]).reset_index(drop=True)
    
    # Run all analytics using the class
    analytics = MessageAnalytics(df)
    top_hashtags, top_urls, top_domains, forward_counts, daily_volume, weekly_volume, monthly_volume = \
        analytics.get_all_analytics(start_date, end_date)
    
    return df, top_hashtags, top_urls, top_domains, forward_counts, daily_volume, weekly_volume, monthly_volume
