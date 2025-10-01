import requests
import re
import json
import datetime
import calendar

def parse_month_str(month_str):
    """
    Parses a month string into a datetime object set to the first day of that month.
    The month_str can be in two formats:
    - "MM/YYYY" (e.g. "08/2003")
    - "jan2024" using a three-letter abbreviation for the month (e.g. "jan2024")
    Returns a datetime object or None on failure.
    """
    try:
        # Remove any escape characters (backslashes)
        month_str = month_str.replace("\\", "")
        if "/" in month_str:
            # Format example: "08/2003"
            parts = month_str.split("/")
            month = int(parts[0])
            year = int(parts[1])
            return datetime.datetime(year, month, 1)
        else:
            # Format example: "jan2024"
            month_abbr = month_str[:3].capitalize()  # "Jan", "Feb", etc.
            if month_abbr in calendar.month_abbr:
                month = list(calendar.month_abbr).index(month_abbr)
            else:
                return None
            year = int(month_str[3:])
            return datetime.datetime(year, month, 1)
    except Exception as e:
        print(f"Error parsing month string '{month_str}': {e}")
        return None

def fetch_calendar_links(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        page_content = response.text
    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        return None

    # Regular expression to capture entries with a "month" field and a "pdf_file" block.
    entry_pattern = re.compile(
        r'"month"\s*:\s*"([^"]+)"\s*,\s*"pdf_file"\s*:\s*\{(.*?)\}', re.DOTALL
    )

    # Find all matches
    entries = entry_pattern.findall(page_content)
    if not entries:
        print("No matching calendar entries found.")
        return []

    # Get today's month and year as a datetime for comparison (set to the first of the month)
    today = datetime.datetime.today()
    reference_date = datetime.datetime(today.year, today.month, 1)
    
    # Get the date for 6 days from today to determine if the next month should be included
    six_days_later = today + datetime.timedelta(days=6)
    next_month_date = datetime.datetime(six_days_later.year, six_days_later.month, 1)

    results = []
    for month_str, pdf_block in entries:
        entry_date = parse_month_str(month_str)
        if entry_date is None:
            continue  # Skip entries with unparseable month format

        # Only include calendars for the current month or later, but also include next month if it's within the next 6 days
        if entry_date >= reference_date and (entry_date < next_month_date or entry_date == next_month_date):
            # Look inside the pdf_file block for a "url" property.
            url_match = re.search(r'"url"\s*:\s*"([^"]+)"', pdf_block)
            if url_match:
                # Remove any backslashes from the extracted URL before storing
                calendar_url = url_match.group(1).replace("\\", "")
                results.append({"month": month_str.replace("\\", ""), "url": calendar_url})
            else:
                results.append({"month": month_str.replace("\\", ""), "pdf_file": pdf_block})
    return results

if __name__ == '__main__':
    url = "https://scssd.org/sports-complex-info/"
    calendar_links = fetch_calendar_links(url)
    if calendar_links:
        # Save the results to a JSON file named cal-urls.json
        with open("0-cal-urls.json", "w") as outfile:
            json.dump(calendar_links, outfile, indent=2)
        print("Calendar links saved to cal-urls.json")
    else:
        print("No calendar links found for this month or later.")
