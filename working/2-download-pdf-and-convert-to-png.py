import os
import json
import requests
from pdf2image import convert_from_path
from urllib.parse import urlparse
import asyncio
import discord

# Your Discord credentials
DISCORD_TOKEN = 'XXXXXXXXXXXXXXXXXX'

CHANNEL_ID_debugging = XXXXXXXXXXXXXX  # BB debugging channel

# Constants
JSON_FILE = "0-cal-urls.json"
OUTPUT_DIR = "calendars"
POPPLER_PATH = "/usr/bin"  # Adjust if poppler is installed elsewhere

# Ensure output folder exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load URLs from JSON
with open(JSON_FILE, 'r') as f:
    data = json.load(f)

async def send_message(base_name):
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready():
        channel = client.get_channel(CHANNEL_ID_debugging)
        if channel:
            await channel.send(f"A new calendar version {base_name} was found and downloaded.")
        await client.close()

    try:
        await client.start(DISCORD_TOKEN)
    finally:
        await client.close()  # Ensure the client is properly closed

# Loop through all entries
for entry in data:
    month = entry.get("month", "").replace("/", "-")
    url = entry.get("url", "").replace("\\", "")
    if not url.lower().endswith(".pdf"):
        continue

    # Extract base filename from URL
    url_path = urlparse(url).path
    base_filename = os.path.basename(url_path)  # Example: May2024_v2.pdf
    base_name, _ = os.path.splitext(base_filename)  # Example: May2024_v2

    # Check if a PNG file already exists for this download
    png_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(base_name) and f.endswith(".png")]
    if png_files:
        print(f"Skipping download for {url}, PNG file already exists.")
        continue

    print(f"Downloading: {url}")
    pdf_path = os.path.join(OUTPUT_DIR, base_filename)

    # Download PDF
    response = requests.get(url)
    with open(pdf_path, 'wb') as f:
        f.write(response.content)

    print(f"Converting {base_filename} to PNG...")
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
        for i, img in enumerate(images):
            # Naming PNG file the same as the PDF's name
            img_filename = f"{base_name}.png"
            img.save(os.path.join(OUTPUT_DIR, img_filename), "PNG")
        print(f"Saved PNG file {base_name}.png")

    except Exception as e:
        print(f"Error converting {base_filename}: {e}")

    # Remove the downloaded PDF file after conversion
    os.remove(pdf_path)
    print(f"Removed {pdf_path} after conversion")

    # Send the message after the file is processed
    # this currently serves to let me know that there's a new version of the calendar and I should manually update my csv version
    # if the automatic conversion worked this would not be necessary
    asyncio.run(send_message(base_name))
