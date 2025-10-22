import streamlit as st
import asyncio
import pandas as pd
import io
from telegram_client import create_client, delete_session_file
from fetch_channel import fetch_channel_data
from fetch_forwards import fetch_forwards
from fetch_messages import fetch_messages
from fetch_participants import fetch_participants
from fetch_subscriptions import fetch_user_subscriptions
from fetch_users import fetch_user_data
from telethon import functions, types
from telethon.errors import PhoneNumberInvalidError, PhoneCodeInvalidError, SessionPasswordNeededError
import nest_asyncio
import re


nest_asyncio.apply()

# --- Ensure an Event Loop Exists ---
import sys
if "event_loop" not in st.session_state:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # Windows fix
    st.session_state.event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.event_loop)
else:
    asyncio.set_event_loop(st.session_state.event_loop)  # Keep the same event loop

def clean_column_name(name):
    name = str(name)
    # Step 1: Remove everything up to and including 't.me/'
    name = re.sub(r'^.*t\.me/', '', name)
    # Step 2: Replace disallowed characters with underscores (allow letters, numbers, _ and -)
    name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    return name

# --- Streamlit UI ---
st.title("TGForge")
st.logo("logo.png", size='large')  # Official app logo

# Ensure session state variables are initialized
if "auth_step" not in st.session_state:
    st.session_state.auth_step = 1
    st.session_state.authenticated = False
    st.session_state.client = None

# --- Step 1: Enter API Credentials --- 
if st.session_state.auth_step == 1:
    st.subheader("Enter Telegram API Credentials")
    
    api_id = st.text_input("API ID", value=st.session_state.get("api_id", ""))
    api_hash = st.text_input("API Hash", value=st.session_state.get("api_hash", ""))
    phone_number = st.text_input("Phone Number (with country code, e.g., +1234567890)", 
                                placeholder="+1234567890")
    
    # Add phone number validation
    if phone_number and not phone_number.startswith('+'):
        st.warning("⚠️ Phone number should include country code starting with '+'")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("Send Verification Code"):
            if api_id and api_hash and phone_number:
                try:
                    # Validate inputs
                    if not phone_number.startswith('+'):
                        st.error("Phone number must start with '+' followed by country code")
                        st.stop()
                    
                    if not api_id.isdigit():
                        st.error("API ID should be numeric")
                        st.stop()
                    
                    # Store credentials
                    st.session_state.api_id = api_id
                    st.session_state.api_hash = api_hash  
                    st.session_state.phone_number = phone_number
                    
                    # Create client if it doesn't exist
                    if st.session_state.client is None:
                        st.session_state.client = create_client(int(api_id), api_hash)
                    
                    async def connect_and_send_code():
                        try:
                            # Ensure we're connected
                            if not st.session_state.client.is_connected():
                                await st.session_state.client.connect()
                            
                            # Check if already authorized
                            if await st.session_state.client.is_user_authorized():
                                st.success("Already authenticated! Proceeding...")
                                st.session_state.auth_step = 3
                                st.session_state.authenticated = True
                                return
                            
                            # Send code request with error handling
                            st.info("📤 Sending verification code...")
                            result = await st.session_state.client.send_code_request(phone_number)
                            
                            # Store the phone_code_hash for later use
                            st.session_state.phone_code_hash = result.phone_code_hash
                            
                            st.success("✅ Verification code sent! Check your Telegram app or SMS.")
                            st.info(f"📱 Code sent via: {result.type}")
                            
                        except Exception as e:
                            st.error(f"Failed to send code: {str(e)}")
                            # Try to disconnect and clean up
                            try:
                                await st.session_state.client.disconnect()
                                st.session_state.client = None
                            except:
                                pass
                            raise e
                    
                    with st.spinner("Connecting to Telegram..."):
                        st.session_state.event_loop.run_until_complete(connect_and_send_code())
                        st.session_state.auth_step = 2
                        st.rerun()
                        
                except PhoneNumberInvalidError:
                    st.error("❌ Invalid phone number. Please check the format and try again.")
                    st.info("Make sure to include the country code (e.g., +1 for US, +44 for UK)")
                except Exception as e:
                    st.error(f"❌ Connection error: {e}")
                    st.info("Check your internet connection and API credentials")
            else:
                st.warning("Please fill in all fields")
    
    with col2:
        if st.button("Reset Session"):
            # Clean up client connection
            if st.session_state.client and st.session_state.client.is_connected():
                try:
                    st.session_state.event_loop.run_until_complete(
                        st.session_state.client.disconnect()
                    )
                except:
                    pass
            st.session_state.client = None
            delete_session_file()
            st.success("Session reset successfully")
            st.rerun()

# --- Step 2: Enter Verification Code ---
elif st.session_state.auth_step == 2:
    st.subheader("Enter Verification Code")
    
    st.info("📱 Check your Telegram app for the verification code")
    
    verification_code = st.text_input("Enter the 5-digit verification code", 
                                     max_chars=5, 
                                     placeholder="12345")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("Verify Code"):
            if verification_code and len(verification_code) >= 5:
                try:
                    async def sign_in():
                        try:
                            # Use the stored phone_code_hash if available
                            if hasattr(st.session_state, 'phone_code_hash'):
                                await st.session_state.client.sign_in(
                                    st.session_state.phone_number, 
                                    verification_code,
                                    phone_code_hash=st.session_state.phone_code_hash
                                )
                            else:
                                await st.session_state.client.sign_in(
                                    st.session_state.phone_number, 
                                    verification_code
                                )
                                
                        except Exception as e:
                            st.error(f"Sign-in failed: {str(e)}")
                            raise e
                    
                    with st.spinner("Verifying code..."):
                        st.session_state.event_loop.run_until_complete(sign_in())
                        st.session_state.auth_step = 3
                        st.session_state.authenticated = True
                        st.success("🎉 Authentication successful!")
                        st.rerun()
                        
                except PhoneCodeInvalidError:
                    st.error("❌ Invalid verification code. Please check and try again.")
                except SessionPasswordNeededError:
                    st.error("❌ Two-step verification is enabled. Please disable it temporarily or implement 2FA handling.")
                    st.info("You can disable 2FA in Telegram Settings > Privacy and Security > Two-Step Verification")
                except Exception as e:
                    st.error(f"❌ Authentication error: {e}")
            else:
                st.warning("Please enter a valid 5-digit code")
    
    with col2:
        if st.button("Resend Code"):
            try:
                async def resend_code():
                    result = await st.session_state.client.send_code_request(st.session_state.phone_number)
                    st.session_state.phone_code_hash = result.phone_code_hash
                
                st.session_state.event_loop.run_until_complete(resend_code())
                st.success("🔄 New code sent!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to resend code: {e}")
    
    with col3:
        if st.button("Back"):
            st.session_state.auth_step = 1
            st.rerun()

# --- Step 3: Fetch Channel Info UI ---
elif st.session_state.auth_step == 3 and st.session_state.authenticated:
    st.subheader("Fetch Telegram Channel Data")

    # Choose what to fetch
    fetch_option = st.radio("Select Data to Fetch:", 
                            ["Channel Info", "Messages", "Forwards", "Participants", "My Subscriptions", "User Lookup"])
    
    # Channel usernames input (only show if not fetching subscriptions or user lookup)
    if fetch_option not in ["My Subscriptions", "User Lookup"]:
        channel_input = st.text_area("Enter Telegram channel usernames (comma-separated):", "")
    else:
        channel_input = ""

    # User IDs input (only show if fetching user lookup)
    if fetch_option == "User Lookup":
        user_ids_input = st.text_area(
            "Enter Usernames or user IDs (comma-separated):", 
            placeholder="420478278418, exampleuser_name, @username",
            help="Enter numeric user IDs or usernames separated by commas"
        )

    # For Messages, Forwards, and Participants, allow optional date range filtering
    participant_method = "Default"
    start_date = end_date = None
    include_comments = True  # Default to including comments
    if fetch_option in ["Messages", "Forwards", "Participants"]:
        if fetch_option == "Messages":
            msg_mode = st.radio("Message Mode", [
                "Original posts only",
                "Original posts + comments (may take significantly longer to load)"
            ])
            include_comments = "comments" in msg_mode.lower()
        if fetch_option == "Participants":
            participant_method = st.radio("Select Participant Fetch Method:", ["Default", "Via Messages"])
        use_date_range = st.checkbox("Optional: Filter by Date Range", value=False)
        if use_date_range:
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
    else:
        start_date = end_date = None

    # Fetch buttons for each option
    if fetch_option == "Channel Info":
        if st.button("Fetch Channel Info"):
            st.session_state.channel_data = st.session_state.event_loop.run_until_complete(
                fetch_channel_data(st.session_state.client, channel_input.split(","))
            )
    elif fetch_option == "Messages":
        if st.button("Fetch Messages"):
            st.session_state.messages_data, st.session_state.top_hashtags, st.session_state.top_urls, \
            st.session_state.top_domains, st.session_state.forward_counts, st.session_state.daily_volume, \
            st.session_state.weekly_volume, st.session_state.monthly_volume = \
                st.session_state.event_loop.run_until_complete(
                    fetch_messages(st.session_state.client, channel_input.split(","), start_date, end_date, include_comments=include_comments)
                )
    elif fetch_option == "Forwards":
        if st.button("Fetch Forwards"):
            st.session_state.forwards_data, st.session_state.forward_counts = \
                st.session_state.event_loop.run_until_complete(
                    fetch_forwards(st.session_state.client, channel_input.split(","), start_date, end_date)
                )
    elif fetch_option == "Participants":
        if st.button("Fetch Participants"):
            groups = [g.strip() for g in channel_input.split(",") if g.strip()]
            if not groups:
                st.error("Please enter at least one valid group name.")
            else:
                if participant_method == "Default":
                    (st.session_state.participants_data,
                     st.session_state.participants_reported,
                     st.session_state.participants_fetched,
                     st.session_state.participants_group_counts) = st.session_state.event_loop.run_until_complete(
                        fetch_participants(st.session_state.client, groups, method="default")
                    )
                else:
                    (st.session_state.participants_data,
                     st.session_state.participants_reported,
                     st.session_state.participants_fetched,
                     st.session_state.participants_group_counts) = st.session_state.event_loop.run_until_complete(
                        fetch_participants(st.session_state.client, groups, method="messages", start_date=start_date, end_date=end_date)
                    )
    elif fetch_option == "My Subscriptions":
        if st.button("Fetch My Subscriptions"):
            st.session_state.subscription_channels, st.session_state.subscription_groups = \
                st.session_state.event_loop.run_until_complete(
                    fetch_user_subscriptions(st.session_state.client)
                )

    elif fetch_option == "User Lookup":
        if st.button("Fetch User Data"):
            if user_ids_input:
                # Parse user IDs from input
                user_ids = [uid.strip() for uid in user_ids_input.split(",") if uid.strip()]
                st.session_state.user_data = st.session_state.event_loop.run_until_complete(
                    fetch_user_data(st.session_state.client, user_ids)
                )
            else:
                st.warning("Please enter at least one user ID")

    # --- Refresh Button (Clears Display But Keeps Data) ---
    if st.button("🔄 Refresh / Cancel"):
        # Signal cancellation to any running fetch tasks
        st.session_state.cancel_fetch = True
        # Clear all keys—including those for participants—in session state
        for key in ["channel_data", "forwards_data", "messages_data", "top_hashtags",
                    "top_urls", "top_domains", "forward_counts", "daily_volume",
                    "weekly_volume", "monthly_volume", "participants_data",
                    "participants_reported", "participants_fetched", "participants_group_counts",
                    "subscription_channels", "subscription_groups", "user_data"]:
        
            if key in st.session_state:
                del st.session_state[key]
        # Clear the cancellation flag for the next run
        st.session_state.cancel_fetch = False
        st.rerun()

    # ✅ Restore original printing format for channel info
    if "channel_data" in st.session_state and st.session_state.channel_data:
        for info in st.session_state.channel_data:
            if "Error" in info:
                st.error(info["Error"])
            else:
                st.markdown("### 📌 Channel Information")
                for key, value in info.items():
                    st.write(f"**{key}:** {value}")
                st.markdown("---")

    # ✅ Show first 25 rows of forwards data in a table
    if "forwards_data" in st.session_state and st.session_state.forwards_data is not None:
        df_fwd = pd.DataFrame(st.session_state.forwards_data)
        st.write("### Forwarded Messages Preview (First 25 Rows)")
        st.dataframe(df_fwd.head(25))

        # ✅ Fix CSV Download (use BytesIO)
        csv_output = io.BytesIO()
        df_fwd.to_csv(csv_output, index=False)
        csv_output.seek(0)
        st.download_button(
            "📥 Download Forwards (CSV)",
            data=csv_output.getvalue(),
            file_name="forwards.csv",
            mime="text/csv",
        )

    # ✅ Show top 25 most viewed posts
    if "messages_data" in st.session_state:
        df_messages = pd.DataFrame(st.session_state.messages_data)

        if "Views" in df_messages.columns:
            df_top_views = df_messages.sort_values(by="Views", ascending=False).head(25)
            st.write("### Top 25 Most Viewed Posts")
            st.data_editor(
                df_top_views,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Description": st.column_config.TextColumn(
                        width="large",
                        max_chars=None,
                        help="Full text shown when hovered."
                    )
                }
            )
        else:
            st.write("### Messages Data Preview (First 25 Rows)")
            st.data_editor(
                df_messages.head(25),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Description": st.column_config.TextColumn(
                        width="large",
                        max_chars=None,
                        help="Full text shown when hovered."
                    )
                }
            )

    # ✅ Show first 25 rows of forward counts in a table
    if "forward_counts" in st.session_state and st.session_state.forward_counts is not None:
        df_counts = pd.DataFrame(st.session_state.forward_counts)
        st.write("### Top Forwarded Channels")
        st.data_editor(df_counts.head(25))

    # ✅ Show top shared domains
    if "top_domains" in st.session_state:
        st.write("### Top Domains")
        st.data_editor(pd.DataFrame(st.session_state.top_domains).head(25))

    # ✅ Show first 25 rows of top URLs
    if "top_urls" in st.session_state and st.session_state.top_urls is not None:
        df_urls = pd.DataFrame(st.session_state.top_urls)
        st.write("### Top URLs")
        st.data_editor(df_urls.head(25))

    # ✅ Show first 25 rows of top hashtags
    if "top_hashtags" in st.session_state and st.session_state.top_hashtags is not None:
        df_hashtags = pd.DataFrame(st.session_state.top_hashtags)
        st.write("### Top Hashtags")
        st.data_editor(df_hashtags.head(25))

    if "participants_data" in st.session_state and not pd.DataFrame(st.session_state.participants_data).empty:
        st.write("### Participants (Aggregated by User)")
        df_participants = pd.DataFrame(st.session_state.participants_data)

        # Explicitly define known user info columns.
        user_cols = [
            "User ID", "Deleted", "Is Bot", "Verified", "Restricted", "Scam", "Fake",
            "Premium", "Access Hash", "First Name", "Last Name", "Username", "Phone",
            "Status", "Timezone Info", "Restriction Reason", "Language Code", "Last Seen",
            "Profile Picture DC ID", "Profile Picture Photo ID"
        ]
        # Assume that any column not in user_cols is a group membership flag.
        group_cols = [col for col in df_participants.columns if col not in user_cols]

        # Group by "User ID": for user info take the first value; for group flags, take max.
        aggregated = df_participants.groupby("User ID").agg({
            "Username": "first",
            "First Name": "first",
            "Last Name": "first",
            "Status": "first",
            **{col: "max" for col in group_cols}
        }).reset_index()

        # Convert group membership columns to numeric (if they aren't already)
        if group_cols:
            aggregated[group_cols] = aggregated[group_cols].fillna(0).apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
            # Calculate the number of groups for each user.
            aggregated["Group Count"] = aggregated[group_cols].sum(axis=1)
            # Build a comma-separated list of groups for each user.
            aggregated["Groups"] = aggregated[group_cols].apply(
                lambda row: ", ".join([col for col in group_cols if row[col] == 1]), axis=1
            )
        else:
            aggregated["Group Count"] = 0
            aggregated["Groups"] = ""

        # Create two tabs: one with all aggregated participants and one for those in 2 or more groups.
        tabs = st.tabs(["All Participants", "Active in ≥ 2 Chats"])
        with tabs[0]:
            st.dataframe(aggregated)
        with tabs[1]:
            multi = aggregated[aggregated["Group Count"] >= 2]
            st.dataframe(multi[["User ID", "Username", "Group Count", "Groups"]])

        if "participants_group_counts" in st.session_state:
            st.write("#### Participant Count Comparison:")
            for group, counts in st.session_state.participants_group_counts.items():
                st.write(f"{group}: {counts[0]} (reported by channel info) | {counts[1]} collected")
        # Optionally, write a summary below the tabs
        st.write("Total unique participants collected:", len(aggregated))

    # Display Subscriptions
    if "subscription_channels" in st.session_state and st.session_state.subscription_channels:
        st.write(f"### Channels ({len(st.session_state.subscription_channels)})")
        df_channels = pd.DataFrame(st.session_state.subscription_channels)
        st.dataframe(df_channels)
        
        # Download option
        csv_output = io.BytesIO()
        df_channels.to_csv(csv_output, index=False)
        csv_output.seek(0)
        st.download_button(
            "📥 Download Channels (CSV)",
            data=csv_output.getvalue(),
            file_name="my_channels.csv",
            mime="text/csv",
        )
    
    if "subscription_groups" in st.session_state and st.session_state.subscription_groups:
        st.write(f"### Groups/Supergroups ({len(st.session_state.subscription_groups)})")
        df_groups = pd.DataFrame(st.session_state.subscription_groups)
        st.dataframe(df_groups)
        
        # Download option
        csv_output = io.BytesIO()
        df_groups.to_csv(csv_output, index=False)
        csv_output.seek(0)
        st.download_button(
            "📥 Download Groups (CSV)",
            data=csv_output.getvalue(),
            file_name="my_groups.csv",
            mime="text/csv",
        )

    # Display User Lookup Data
    if "user_data" in st.session_state and st.session_state.user_data:
        st.write(f"### User Information ({len(st.session_state.user_data)} users)")
        df_users = pd.DataFrame(st.session_state.user_data)
        st.dataframe(df_users)
        
        # Download options
        st.subheader("📤 Export User Data")
        format_option = st.selectbox("Choose export format:", ["CSV", "Excel"], key="user_export_format")
        
        if format_option == "CSV":
            csv_output = io.BytesIO()
            df_users.to_csv(csv_output, index=False)
            csv_output.seek(0)
            st.download_button(
                "📥 Download as CSV",
                data=csv_output.getvalue(),
                file_name="user_data.csv",
                mime="text/csv",
            )
        
        elif format_option == "Excel":
            output_xlsx = io.BytesIO()
            with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
                df_users.to_excel(writer, sheet_name="User Data", index=False)
            output_xlsx.seek(0)
            st.download_button(
                "📥 Download as Excel",
                data=output_xlsx.getvalue(),
                file_name="user_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    
    # ✅ Define color palette
    COLOR_PALETTE = ["#C7074D", "#B4B2B1", "#4C4193", "#0068B2", "#E76863", "#5C6771"]

    def convert_df_to_markdown(df):
        return df.to_markdown(index=False, tablefmt="github")

    def plot_vot_chart(df, index_col, title, freq="D"):
        st.subheader(title)

        if df.empty:
            st.warning("No data available.")
            return

        df[index_col] = pd.to_datetime(df[index_col], errors="coerce")
        df = df.set_index(index_col)

        full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq=freq)
        df = df.reindex(full_range, fill_value=0)
        df.index.name = index_col
        df.reset_index(inplace=True)

        show_total = st.toggle(f"Show aggregated total for {title}", value=False)

        if show_total:
            df["Total"] = df.select_dtypes(include=["number"]).iloc[:, 1:].sum(axis=1)
            df = df[[index_col, "Total"]]
            colors = ["#C7074D"]
        else:
            num_lines = df.shape[1] - 1
            colors = COLOR_PALETTE[:num_lines] if num_lines <= len(COLOR_PALETTE) else None

        df_plot = df.set_index(index_col)
        df_plot = df_plot.select_dtypes(include=["number"])
        df_plot.columns = [clean_column_name(c) for c in df_plot.columns]

        st.line_chart(df_plot, color=colors)

    # ✅ Show Volume Over Time Charts with Missing Dates Filled
    if "daily_volume" in st.session_state:
        df_daily = pd.DataFrame(st.session_state.daily_volume)
        df_daily = df_daily.fillna(0)
        plot_vot_chart(df_daily, "Date", "Daily Message Volume", freq="D")

    if "weekly_volume" in st.session_state:
        df_weekly = pd.DataFrame(st.session_state.weekly_volume)
        df_weekly = df_weekly.fillna(0)
        plot_vot_chart(df_weekly, "Week", "Weekly Message Volume", freq="W-TUE")

    if "monthly_volume" in st.session_state:
        df_monthly = pd.DataFrame(st.session_state.monthly_volume)
        df_monthly = df_monthly.fillna(0)
        plot_vot_chart(df_monthly, "Year-Month", "Monthly Message Volume", freq="MS")

    # CSV Download
    if "messages_data" in st.session_state and st.session_state.messages_data is not None:
        df_messages = pd.DataFrame(st.session_state.messages_data)

        st.subheader("Export Raw Data")
        format_option = st.selectbox("Choose export format for raw Telegram data:", ["CSV", "Markdown", "Excel"], key="messages_export_format")

        if format_option == "CSV":
            csv_output = io.BytesIO()
            df_messages.to_csv(csv_output, index=False)
            csv_output.seek(0)
            st.download_button(
                "📥 Download as CSV",
                data=csv_output.getvalue(),
                file_name="messages.csv",
                mime="text/csv",
            )

        elif format_option == "Markdown":
            markdown_output = convert_df_to_markdown(df_messages.head(1000))  # Limit size if needed
            st.download_button(
                "📥 Download as Markdown",
                data=markdown_output,
                file_name="messages.md",
                mime="text/markdown",
            )

        elif format_option == "Excel":
            output_xlsx = io.BytesIO()
            with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
                df_messages.to_excel(writer, sheet_name="Messages", index=False)
            output_xlsx.seek(0)
            st.download_button(
                "📥 Download as Excel",
                data=output_xlsx.getvalue(),
                file_name="messages.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # XLSX Download
    if "messages_data" in st.session_state and st.session_state.messages_data is not None:
        st.subheader("Export Channel(s) Analytics")
        # Build XLSX for message analytics
        df_messages = pd.DataFrame(st.session_state.messages_data).nlargest(50, "Views")  # Top 50 most viewed messages
        df_top_domains = pd.DataFrame(st.session_state.top_domains).head(25)               # Top 25 shared domains
        df_top_urls = pd.DataFrame(st.session_state.top_urls).head(25)                     # Top 25 shared URLs
        df_forward_counts = pd.DataFrame(st.session_state.forward_counts)                  # Forward counts
        df_top_hashtags = pd.DataFrame(st.session_state.top_hashtags).head(25)             # Top 25 hashtags
        df_daily_volume = pd.DataFrame(st.session_state.daily_volume)                      # Daily volume
        df_weekly_volume = pd.DataFrame(st.session_state.weekly_volume)                    # Weekly volume
        df_monthly_volume = pd.DataFrame(st.session_state.monthly_volume)                  # Monthly volume

        output_xlsx = io.BytesIO()
        with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
            df_messages.to_excel(writer, sheet_name="Top 50 Viewed Posts", index=False)
            df_top_domains.to_excel(writer, sheet_name="Top 25 Shared Domains", index=False)
            df_top_urls.to_excel(writer, sheet_name="Top 25 Shared URLs", index=False)
            df_forward_counts.to_excel(writer, sheet_name="Forward Counts", index=False)
            df_top_hashtags.to_excel(writer, sheet_name="Top 25 Hashtags", index=False)
            df_daily_volume.to_excel(writer, sheet_name="Daily Volume", index=False)
            df_weekly_volume.to_excel(writer, sheet_name="Weekly Volume", index=False)
            df_monthly_volume.to_excel(writer, sheet_name="Monthly Volume", index=False)
        output_xlsx.seek(0)

        st.download_button(
            "📥 Download Analytics",
            data=output_xlsx.getvalue(),
            file_name="messages_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    elif "forwards_data" in st.session_state and st.session_state.forwards_data is not None:
        st.subheader("Export Channel(s) Analytics")
        df_forwards = pd.DataFrame(st.session_state.forwards_data)
        df_forward_counts = pd.DataFrame(st.session_state.forward_counts)

        st.subheader("📤 Export Forwards Data")
        format_option = st.selectbox("Choose export format:", ["CSV", "Markdown", "Excel"], key="forwards_export_format")

        if format_option == "CSV":
            csv_output = io.BytesIO()
            df_forwards.to_csv(csv_output, index=False)
            csv_output.seek(0)
            st.download_button(
                "📥 Download as CSV",
                data=csv_output.getvalue(),
                file_name="forwards.csv",
                mime="text/csv",
            )

        elif format_option == "Markdown":
            markdown_output = convert_df_to_markdown(df_forwards.head(1000))
            st.download_button(
                "📥 Download as Markdown",
                data=markdown_output,
                file_name="forwards.md",
                mime="text/markdown",
            )

        elif format_option == "Excel":
            output_xlsx = io.BytesIO()
            with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
                df_forwards.to_excel(writer, sheet_name="Forwarded Messages", index=False)
                df_forward_counts.to_excel(writer, sheet_name="Forward Counts", index=False)
            output_xlsx.seek(0)
            st.download_button(
                "📥 Download as Excel",
                data=output_xlsx.getvalue(),
                file_name="forwards_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    elif "participants_data" in st.session_state and not pd.DataFrame(st.session_state.participants_data).empty:
        st.subheader("Export Channel(s) Analytics")
        df_participants = pd.DataFrame(st.session_state.participants_data)

        user_cols = [
            "User ID", "Deleted", "Is Bot", "Verified", "Restricted", "Scam", "Fake",
            "Premium", "Access Hash", "First Name", "Last Name", "Username", "Phone",
            "Status", "Timezone Info", "Restriction Reason", "Language Code", "Last Seen",
            "Profile Picture DC ID", "Profile Picture Photo ID"
        ]
        group_cols = [col for col in df_participants.columns if col not in user_cols]
        aggregated = df_participants.groupby("User ID").agg({
            "Username": "first",
            "First Name": "first",
            "Last Name": "first",
            "Status": "first",
            **{col: "max" for col in group_cols}
        }).reset_index()
        if group_cols:
            aggregated[group_cols] = aggregated[group_cols].fillna(0).apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
            aggregated["Group Count"] = aggregated[group_cols].sum(axis=1)
            aggregated["Groups"] = aggregated[group_cols].apply(
                lambda row: ", ".join([col for col in group_cols if row[col] == 1]), axis=1
            )
        else:
            aggregated["Group Count"] = 0
            aggregated["Groups"] = ""

        st.subheader("📤 Export Participants Data")
        format_option = st.selectbox("Choose export format:", ["CSV", "Markdown", "Excel"], key="participants_export_format")

        if format_option == "CSV":
            csv_output = io.BytesIO()
            aggregated.to_csv(csv_output, index=False)
            csv_output.seek(0)
            st.download_button(
                "📥 Download as CSV",
                data=csv_output.getvalue(),
                file_name="participants.csv",
                mime="text/csv",
            )

        elif format_option == "Markdown":
            markdown_output = convert_df_to_markdown(aggregated.head(1000))
            st.download_button(
                "📥 Download as Markdown",
                data=markdown_output,
                file_name="participants.md",
                mime="text/markdown",
            )

        elif format_option == "Excel":
            output_xlsx_participants = io.BytesIO()
            with pd.ExcelWriter(output_xlsx_participants, engine="openpyxl") as writer:
                df_participants.to_excel(writer, sheet_name="Raw Participants", index=False)
                aggregated.to_excel(writer, sheet_name="Aggregated Participants", index=False)
            output_xlsx_participants.seek(0)
            st.download_button(
                "📥 Download as Excel",
                data=output_xlsx_participants.getvalue(),
                file_name="participants_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

st.markdown(
    """
    <div style="text-align: center; margin-top: 50px;">
        Need help? <a href="https://github.com/eNDO9/TGForge/blob/main/README.md" target="_blank">View the User Guide</a>
    </div>
    """,
    unsafe_allow_html=True,
)
