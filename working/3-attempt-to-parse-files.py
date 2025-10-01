import re

def parse_entries(filename):
    with open(filename, 'r') as f:
        text = f.read()
    
    # Find the start of the calendar entries using the header string.
    header_str = "SUN MON TUES WED THURS FRI SAT"
    start_index = text.find(header_str)
    if start_index != -1:
        content = text[start_index + len(header_str):]
    else:
        content = text  # fallback if header not found
    
    # Each entry is assumed to end at a closing parenthesis.
    entries = re.findall(r'(.*?\))', content, flags=re.DOTALL)
    
    # Clean up each entry (remove extra whitespace/newlines)
    cleaned_entries = [" ".join(entry.split()) for entry in entries if entry.strip()]
    return cleaned_entries

def parse_entry(entry):
    """
    Parses an individual entry into a dictionary with keys:
      - date: Everything between the end of any previous ')' and the first time token,
              with all letters removed.
      - time: The first time token found. If a range is present, only the first token is kept.
      - event: The text after the (optional) time range and before the attendance.
      - attendance: The number from inside the final parentheses (with commas removed).
    """
    pattern = re.compile(
        r"^(?:(?P<prefix>.*\))\s*)?"         # Optional leftover text ending with ')'
        r"(?P<date>.*?)\b"                   # Date: everything up to time token
        r"(?P<time>\d{1,2}(?::\d{2})?\s*(?:AM|PM))\b"  # Time token
        r"(?:\s*(?:-|–)\s*(?:\d{1,2}(?::\d{2})?\s*(?:AM|PM))\b)?"  # Optional time range (ignored)
        r"\s*(?P<event>.*?)\s*"              # Event text
        r"\((?P<attendance>[\d,]+)\)\s*$",   # Attendance in parentheses
        re.IGNORECASE
    )
    
    match = pattern.match(entry)
    if match:
        # Capture date from regex and remove all letters.
        date_str = match.group("date").strip()
        date_str = re.sub(r"[A-Za-z]", "", date_str).strip()
        if not date_str:
            date_str = "0"
        
        # Capture time.
        time_str = match.group("time").strip()
        
        # Capture event text.
        event_str = match.group("event").strip()
        
        # Capture attendance and remove commas.
        attendance_str = match.group("attendance").replace(",", "").strip()
        
        return {"date": date_str, "time": time_str, "event": event_str, "attendance": attendance_str}
    else:
        # Fallback: if regex fails, perform a simpler splitting approach.
        parts = entry.split()
        date_str = parts[0] if parts and parts[0].isdigit() else "0"
        time_str = ""
        event_str = entry
        attendance_str = ""
        return {"date": date_str, "time": time_str, "event": event_str, "attendance": attendance_str}

def print_table(entries):
    """
    Prints a table where each row is an event entry with columns:
      - Date, Time, Event, Attendance
    """
    header = f"{'Date':<15} {'Time':<10} {'Event':<50} {'Attendance':<12}"
    separator = "-" * len(header)
    print(header)
    print(separator)
    
    parsed_entries1 = []
    for entry in entries:
        details = parse_entry(entry)
        parsed_entries1.append(details)
        print(f"{details['date']:<15} {details['time']:<10} {details['event']:<50} {details['attendance']:<12}")
    #print(details)
    return parsed_entries1
    
def main():
    filename = "this-month.txt"
    raw_entries = parse_entries(filename)
    
    parsed_entries1 = print_table(raw_entries)


if __name__ == "__main__":
    main()
