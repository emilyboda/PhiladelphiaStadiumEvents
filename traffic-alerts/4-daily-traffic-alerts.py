import os
import subprocess
import csv
import re
import asyncio
import discord
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


# Folder containing the CSV files from the GitHub repo
CSV_FOLDER = "./calendars-git"  # Path to the cloned/downloaded repo

# Ensure the repo is cloned or updated
REPO_URL = "https://github.com/emilyboda/PhiladelphiaStadiumEvents.git"
if not os.path.isdir(CSV_FOLDER):
    print(f"Cloning {REPO_URL} into {CSV_FOLDER}...")
    subprocess.run(["git", "clone", REPO_URL, CSV_FOLDER], check=True)
else:
    print(f"Updating {CSV_FOLDER} with latest changes (force overwrite)...")
    subprocess.run(["git", "-C", CSV_FOLDER, "fetch", "origin"], check=True)
    subprocess.run(["git", "-C", CSV_FOLDER, "reset", "--hard", "origin/main"], check=True)

# Your Discord credentials
DISCORD_TOKEN = 'XXXXXXXXXXXXXXXXXXX'

CHANNEL_ID = XXXXXXXXXXXX # The discord channel ID that you want to send traffic notifications to
#CHANNEL_ID = XXXXXXXXXXXX # An alternate discord channel ID for testing
CHANNEL_ID_debugging = XXXXXXXXXXXX  # A third discord channel ID for sending a message when no events are found, just so you still know it's working


# Pattern to extract year and month from filenames like "2025-10.csv"
FILENAME_PATTERN = re.compile(r"(\d{4})-(\d{2})\.csv")

# Location conversion map
LOCATION_MAP = {
    "CBP": "the Bank",
    "LFF": "the Linc",
    "WFC": "the Wells Fargo Center",
    "XF!": "Xfinity Live",
    "XMA": "Xfinity Mobile Arena (fka the Wells Fargo Center)",
    "SL!": "Stateside Live! (fka Xfinity Live!)"
}

# Date range: today only
today = datetime.now()

# Function to clean and adjust event name
def clean_event_name(name):
    name = name.replace("PHILLIES", "Phillies")
    name = name.replace("FLYERS", "Flyers")
    name = name.replace("EAGLES", "Eagles")
    name = name.replace("SIXERS", "Sixers")
    return name.split(">>>")[0].strip()

# Parse and normalize time string
def parse_event_time(date, time_str):
    try:
        return datetime.strptime(f"{date.strftime('%Y-%m-%d')} {time_str}", "%Y-%m-%d %I:%M%p")
    except ValueError:
        try:
            return datetime.strptime(f"{date.strftime('%Y-%m-%d')} {time_str}", "%Y-%m-%d %I%p")
        except ValueError:
            return None

def normalize_time_display(time_str):
    return time_str.lower().replace(" ", "")


# --- Step 1: Parse events from the correct CSV file ---
events_by_date = defaultdict(list)

# Find the correct file for today
month_file = None
for file in Path(CSV_FOLDER).glob("*.csv"):
    match = FILENAME_PATTERN.match(file.name)
    if not match:
        continue
    year, month = int(match.group(1)), int(match.group(2))
    if year == today.year and month == today.month:
        month_file = file
        break

if month_file:
    with open(month_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                event_date = datetime(today.year, today.month, int(row['Date']))
            except ValueError:
                continue
            if event_date.date() == today.date():  # Only check for today's events
                location = LOCATION_MAP.get(row["Location"], row["Location"])
                event_name = clean_event_name(row["Event Name"])
                time_raw = row["Time"]
                time_clean = normalize_time_display(time_raw)
                attendance = int(row["Attendance"])
                time_dt = parse_event_time(event_date, time_clean)
                events_by_date[event_date].append({
                    "time_str": time_clean,
                    "time_dt": time_dt,
                    "event": event_name,
                    "location": location,
                    "attendance": attendance
                })

# --- Step 3: Format summary ---
summary_lines = []

for event_date in sorted(events_by_date.keys()):
    weekday = event_date.strftime("%a")
    formatted_date = event_date.strftime("%-m/%-d")
    day_events = events_by_date[event_date]

    for ev in day_events:
        line = f"* **{weekday}, {formatted_date} at {ev['time_str']}:** {ev['event']} at {ev['location']}"
        
        # Early event check
        if ev["time_dt"] and ev["time_dt"].hour < 18:
            line += "\t*☀️ Early event warning ☀️*"
        
        # Large event check
        if ev["attendance"] > 50000:
            line += "\t*🚨 Large event 🚨*"
        
        # Only add event if it's early or large
        if ev["time_dt"] and ev["time_dt"].hour < 18 or ev["attendance"] > 50000:
            summary_lines.append(line)

if summary_lines != []:
    summary_lines.insert(0, "")
    summary_lines.insert(0, f"## Reminder! There are potentially disruptive events today.")
else:
    # Send message to debugging channel if no events today
    async def send_no_events_message():
        client = discord.Client(intents=discord.Intents.default())

        @client.event
        async def on_ready():
            channel = client.get_channel(CHANNEL_ID_debugging)
            if channel:
                await channel.send("daily alert script ran, no events today")
            await client.close()

        try:
            await client.start(DISCORD_TOKEN)
        finally:
            await client.close()

    if DISCORD_TOKEN != "YOUR_DISCORD_BOT_TOKEN":
        asyncio.run(send_no_events_message())

# Print to terminal
for line in summary_lines:
    print(line)

# --- Step 4: Send to Discord ---
async def send_to_discord():
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            message_chunks = []
            chunk = ""
            for line in summary_lines:
                if len(chunk) + len(line) + 1 > 1900:
                    message_chunks.append(chunk)
                    chunk = ""
                chunk += line + "\n"
            if chunk:
                message_chunks.append(chunk)

            for part in message_chunks:
                await channel.send(f"{part}")

        await client.close()

    try:
        await client.start(DISCORD_TOKEN)
    finally:
        await client.close()

if DISCORD_TOKEN != "YOUR_DISCORD_BOT_TOKEN":
    asyncio.run(send_to_discord())
