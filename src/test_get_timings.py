import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

restaurant_name_map_reversed = {
    "Bella Union": "Bella Union",
    "Beyu Blue Coffee": "Beyu Blue Coffee",
    "Bseisu Coffee Bar": "Bseisu Coffee Bar",
    "Cafe": "Cafe",
    "Cafe' 300": "Café 300",
    "Freeman Center for Jewish Life": "Freeman Café",
    "Ginger & Soy": "Ginger + Soy",
    "Gothic Grill": "Gothic Grill",
    "Gyotaku": "Gyotaku",
    "Il Forno": "Il Forno",
    "It's Thyme": "It's Thyme",
    "JB's Roasts and Chops": "J.B.'s Roast & Chops",
    "Marketplace": "Marketplace",
    "Nasher Museum Cafe": "Nasher Museum Café",
    "Red Mango Cafe": "Red Mango",
    "Saladelia Cafe at Perkins": "Saladalia @ The Perk",
    "Saladelia Cafe at Sanford": "Sanford Deli",
    "Sazon": "Sazon",
    "Sprout": "Sprout",
    "Tandoor": "Tandoor Indian Cuisine",
    "The Devil's Krafthouse": "The Devils Krafthouse",
    "Farmstead": "The Farmstead",
    "Pitchfork's": "The PitchFork",
    "The Skillet": "The Skillet",
    "Trinity Cafe": "Trinity Cafe",
    "Twinnie's": "Twinnie's",
    "Zweli's Cafe at Duke Divinity": "Zweli's Café at Duke Divinity",
}

# Use today's date
today_str = datetime.today().strftime('%Y-%m-%d')
url = f"https://campushours.oit.duke.edu/places/dining?start_date={today_str}"

response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

rows = soup.find_all("div", role="row")

for row in rows[1:]:  # Skip header row
    location_div = row.find("div", role="rowheader")
    today_cell = row.find_all("div", role="cell")[0] if row.find_all("div", role="cell") else None

    if location_div and today_cell:
        internal_name = location_div.get_text(strip=True)
        display_name = restaurant_name_map_reversed.get(internal_name, internal_name)
        raw_hours = today_cell.get_text(strip=True)

        # Add commas before:
        # 1. Time ranges that start immediately after am/pm (e.g., "7 am9 am" → "7 am, 9 am")
        # 2. The word "Noon" or "Midnight"
        formatted_hours = re.sub(r'(?<=[ap]m)(?=\d)', ', ', raw_hours)
        formatted_hours = re.sub(r'(?<=[ap]m)(?=Noon|Midnight)', ', ', formatted_hours)

        print(f"{display_name}: {formatted_hours}")