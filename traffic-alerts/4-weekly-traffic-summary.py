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
DISCORD_TOKEN = 'XXXXXXXXXXXXX'  # <-- Replace this

CHANNEL_ID = XXXXXXXXXXXXX # Main traffic notification channel ID
#CHANNEL_ID = XXXXXXXXXXXXX # Alterate channel ID for testing
CHANNEL_ID_debugging = XXXXXXXXXXXXX  # Channel for debbuging


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

# Date range: tomorrow through five days from now
today = datetime.now()
start_date = today + timedelta(days=1)
end_date = today + timedelta(days=5)

def clean_event_name(name):
    name = name.replace("PHILLIES", "Phillies")
    name = name.replace("FLYERS", "Flyers")
    name = name.replace("EAGLES", "Eagles")
    name = name.replace("SIXERS", "Sixers")
    return name.split(">>>")[0].strip()

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


# Collect events
events_by_date = defaultdict(list)
required_months = set()
date_to_month = {}
current = start_date
while current <= end_date:
    required_months.add((current.year, current.month))
    date_to_month[current.date()] = (current.year, current.month)
    current += timedelta(days=1)

month_files = {}
for file in Path(CSV_FOLDER).glob("*.csv"):
    match = FILENAME_PATTERN.match(file.name)
    if not match:
        continue
    year, month = int(match.group(1)), int(match.group(2))
    month_files[(year, month)] = file

missing_months = set()
for (year, month) in required_months:
    if (year, month) not in month_files:
        missing_months.add((year, month))
        continue
    file = month_files[(year, month)]
    with open(file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                event_date = datetime(year, month, int(row['Date']))
            except ValueError:
                continue
            if start_date.date() <= event_date.date() <= end_date.date():
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

# Generate summary
summary_lines = []
disruptive_event_found = False

summary_lines.append(f"## Welcome to your weekly Navy Yard traffic disruptions summary for {start_date.strftime('%-m/%-d')}-{end_date.strftime('%-m/%-d')}")
summary_lines.append("")

for event_date in sorted(events_by_date.keys()):
    weekday = event_date.strftime("%a")
    formatted_date = event_date.strftime("%-m/%-d")
    day_events = events_by_date[event_date]

    combined_warning = ""
    if len(day_events) > 1:
        total_attendance = sum(ev["attendance"] for ev in day_events)
        if total_attendance > 50000:
            sorted_times = sorted([ev["time_dt"] for ev in day_events if ev["time_dt"]])
            for i in range(len(sorted_times) - 1):
                delta = abs((sorted_times[i + 1] - sorted_times[i]).total_seconds()) / 3600
                if delta <= 2:
                    combined_warning = "\t*📣📣 Large combined events 📣📣*"
                    disruptive_event_found = True
                    break

    if len(day_events) == 1:
        ev = day_events[0]
        line = f"* **{weekday}, {formatted_date} at {ev['time_str']}:** {ev['event']} at {ev['location']}"
        if ev["time_dt"] and ev["time_dt"].hour < 18:
            line += "\t*☀️ Early event warning ☀️*"
            disruptive_event_found = True
        if ev["attendance"] > 50000:
            line += "\t*🚨 Large event 🚨*"
            disruptive_event_found = True
        summary_lines.append(line)
    else:
        if combined_warning:
            summary_lines.append(f"* **{weekday}, {formatted_date}**, there are {len(day_events)} events:\t{combined_warning}")
        else:
            summary_lines.append(f"* **{weekday}, {formatted_date}**, there are {len(day_events)} events:")
        for ev in day_events:
            line = f"   * **at {ev['time_str']}:** {ev['event']} at {ev['location']}"
            if ev["time_dt"] and ev["time_dt"].hour < 18:
                line += "\t*☀️ Early event warning ☀️*"
                disruptive_event_found = True
            if ev["attendance"] > 50000:
                line += "\t*🚨 Large event 🚨*"
                disruptive_event_found = True
            summary_lines.append(line)

summary_lines.append("")
summary_lines.append("")


# Handle no disruptive events
if not disruptive_event_found:
    if 3 <= today.month <= 8:
        message = "## There are no disruptive events at the stadiums this week. Go Phils!"
    else:
        message = "## There are no disruptive events at the stadiums this week. Go Birds!"
    print(message)
    summary_lines = [message]  # Overwrite Discord message too

# Add warning for missing months
if missing_months:
    # Find the earliest and latest date in the summary range that is missing
    missing_dates = [d for d, ym in date_to_month.items() if ym in missing_months]
    if missing_dates:
        min_date = min(missing_dates)
        max_date = max(missing_dates)
        summary_lines.append(f"Warning: events for dates {min_date.strftime('%-m/%-d')}-{max_date.strftime('%-m/%-d')} have not yet been uploaded.")


# Print to terminal
for line in summary_lines:
    print(line)

# Send to Discord
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

    await client.start(DISCORD_TOKEN)

if DISCORD_TOKEN != "YOUR_DISCORD_BOT_TOKEN":
    asyncio.run(send_to_discord())
