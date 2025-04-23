from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.styles import ParagraphStyle

# Restaurant name mapping (Duke Campus Hours -> NetNutrition)
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

# Create reverse mapping (NetNutrition -> Duke Campus Hours)
restaurant_name_map = {v: k for k, v in restaurant_name_map_reversed.items()}

# Function to fetch dining hours
def get_dining_hours():
    print("\n[Step 0] Fetching dining hours...")
    today_str = datetime.today().strftime('%Y-%m-%d')
    url = f"https://campushours.oit.duke.edu/places/dining?start_date={today_str}"
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all rows for locations
        rows = soup.find_all("div", role="row")
        
        hours_dict = {}
        # Extract dining hours
        for row in rows[1:]:  # Skip header row
            location_div = row.find("div", role="rowheader")
            today_cell = row.find_all("div", role="cell")[0] if row.find_all("div", role="cell") else None
            
            if location_div and today_cell:
                internal_name = location_div.get_text(strip=True)
                raw_hours = today_cell.get_text(strip=True)
                
                # Add commas between joined times and special labels
                formatted_hours = re.sub(r'(?<=[ap]m)(?=\d)', ', ', raw_hours)
                formatted_hours = re.sub(r'(?<=[ap]m)(?=Noon|Midnight)', ', ', formatted_hours)
                
                # Find the matching NetNutrition name
                netnutrition_name = restaurant_name_map_reversed.get(internal_name, internal_name)
                hours_dict[netnutrition_name] = formatted_hours
                
        print(f"[✓] Found hours for {len(hours_dict)} dining locations")
        return hours_dict
    except Exception as e:
        print(f"[X] Error fetching dining hours: {e}")
        return {}
    
# Get dining hours before starting the scraping process
dining_hours = get_dining_hours()

options = Options()
options.add_argument("--headless=new")            # Run in headless mode
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")
options.add_argument("--disable-default-apps")
options.add_argument("--no-sandbox")               # Needed for GitHub Actions
options.add_argument("--disable-dev-shm-usage")      # Prevents issues with limited /dev/shm space
options.add_argument("--window-size=1920,1080")

SECONDS_TO_WAIT = 1

# Initialize driver
print("Initializing Chrome driver...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://netnutrition.cbord.com/nn-prod/Duke")
print("Page loaded.")

def safe_click(by, selector, desc="element", delay=SECONDS_TO_WAIT):
    try:
        elem = driver.find_element(by, selector)
        driver.execute_script("arguments[0].click();", elem)
        print(f"[✓] Clicked {desc}")
        time.sleep(delay)
        return True
    except Exception as e:
        print(f"[X] Could not click {desc}: {e}")
        return False

# Step 1: Dismiss modal
print("\n[Step 1] Dismissing modal...")
time.sleep(SECONDS_TO_WAIT)
safe_click(By.XPATH, '//button[contains(@onclick, "setIgnoreMobileDisc")]', "Continue button")

# Step 2: Click "Only show Halal" in traitsPanel
print("\n[Step 2] Applying Halal filter...")
time.sleep(SECONDS_TO_WAIT)
safe_click(By.ID, "pref_-99", "Halal filter")

# Step 3: Iterate through open dining units
print("\n[Step 3] Iterating through dining units...")
halal_data = {}
units = driver.find_elements(By.CSS_SELECTOR, ".card.unit")
print(f"Found {len(units)} total units.")

for unit in units:
    try:
        status = unit.find_element(By.CLASS_NAME, "badge").text.lower()
        if "open" not in status:
            print("Skipping closed unit.")
            continue

        name = unit.find_element(By.TAG_NAME, "a").text.strip()
        print(f"\n[Unit] Opening: {name}")
        driver.execute_script("arguments[0].click();", unit.find_element(By.TAG_NAME, "a"))
        time.sleep(SECONDS_TO_WAIT)

        # Locate menu panel
        menu_links = []
        try:
            menu_data_list = driver.find_element(By.ID, "cbo_nn_menuDataList")
            card_blocks = menu_data_list.find_elements(By.CSS_SELECTOR, "div.card-block")
            print(f"  Found {len(card_blocks)} card blocks in menu panel.")
            if card_blocks:
                first_block = card_blocks[0]
                menu_links = first_block.find_elements(By.CSS_SELECTOR, "a.cbo_nn_menuLink")
                print(f"  Found {len(menu_links)} menu links.")
        except NoSuchElementException:
            print(f"  No menu panel found for {name} — checking if menu is already displayed...")

        # If no menu links, check if already inside itemPanel directly
        if not menu_links:
            try:
                item_panel = driver.find_element(By.ID, "itemPanel")
                panel_text = item_panel.text
                if "There are no items available" in panel_text:
                    print("  No items available.")
                else:
                    print("  ✔ Menu has items (auto-loaded)!")
                    if name not in halal_data:
                        halal_data[name] = {}

                    rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
                    print(f"  Found {len(rows)} rows in menu table.")

                    current_category = None

                    for idx, row in enumerate(rows):
                        row_class = row.get_attribute("class")
                        print(f"    Row {idx} class: {row_class}")

                        if "itemGroupRow" in row_class:
                            try:
                                category_text = row.find_element(By.CSS_SELECTOR, "div[role='button']").text.strip()
                                current_category = category_text
                                print(f"\n    [Category] {current_category}")
                                if current_category and current_category not in halal_data[name]:
                                    halal_data[name][current_category] = []
                            except NoSuchElementException as e:
                                print(f"    [X] Failed to extract category: {e}")
                                current_category = "Uncategorized"
                                if current_category not in halal_data[name]:
                                    halal_data[name][current_category] = []

                        elif "itemPrimaryRow" in row_class or "itemAlternateRow" in row_class:
                            if not current_category:
                                current_category = "Uncategorized"
                                if current_category not in halal_data[name]:
                                    halal_data[name][current_category] = []
                            try:
                                meal_elem = row.find_element(By.CSS_SELECTOR, "td a.cbo_nn_itemHover")
                                meal_full_text = meal_elem.get_attribute("innerText").strip()
                                meal_name = meal_full_text.split("\n")[0]
                                if meal_name:
                                    print(f"      [Meal] {meal_name}")
                                    if meal_name not in halal_data[name][current_category]:
                                        halal_data[name][current_category].append(meal_name)
                            except NoSuchElementException:
                                print("      [!] Meal link not found in row.")

                # Go back to restaurant list
                safe_click(By.XPATH, '//a[contains(text(), "Back")]', "Back to restaurant list")
                continue  # Skip normal menu loop
            except NoSuchElementException:
                print(f"  [X] Neither menu panel nor item panel found for {name}. Skipping.")
                continue

        for i in range(len(menu_links)):
            try:
                # Refresh elements to avoid stale reference
                menu_data_list = driver.find_element(By.ID, "cbo_nn_menuDataList")
                card_blocks = menu_data_list.find_elements(By.CSS_SELECTOR, "div.card-block")
                first_block = card_blocks[0]
                menu_links = first_block.find_elements(By.CSS_SELECTOR, "a.cbo_nn_menuLink")

                menu_link = menu_links[i]
                label = menu_link.text.strip()
                print(f"\n[Menu] Clicking: {label}")
                driver.execute_script("arguments[0].click();", menu_link)
                time.sleep(SECONDS_TO_WAIT)

                item_panel = driver.find_element(By.ID, "itemPanel")
                panel_text = item_panel.text
                if "There are no items available" in panel_text:
                    print("  No items available — skipping menu.")
                else:
                    print("  ✔ Menu has items!")
                    if name not in halal_data:
                        halal_data[name] = {}

                    rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
                    print(f"  Found {len(rows)} rows in menu table.")

                    current_category = None

                    for idx, row in enumerate(rows):
                        row_class = row.get_attribute("class")
                        print(f"    Row {idx} class: {row_class}")

                        if "itemGroupRow" in row_class:
                            try:
                                category_text = row.find_element(By.CSS_SELECTOR, "div[role='button']").text.strip()
                                current_category = category_text
                                print(f"\n    [Category] {current_category}")
                                if current_category and current_category not in halal_data[name]:
                                    halal_data[name][current_category] = []
                            except NoSuchElementException as e:
                                print(f"    [X] Failed to extract category: {e}")
                                current_category = None

                        elif "itemPrimaryRow" in row_class or "itemAlternateRow" in row_class:
                            if current_category:
                                try:
                                    meal_elem = row.find_element(By.CSS_SELECTOR, "td a.cbo_nn_itemHover")
                                    meal_full_text = meal_elem.get_attribute("innerText").strip()
                                    meal_name = meal_full_text.split("\n")[0]  # Get only the first line
                                    if meal_name:
                                        print(f"      [Meal] {meal_name}")
                                        if meal_name not in halal_data[name][current_category]:
                                            halal_data[name][current_category].append(meal_name)
                                except NoSuchElementException:
                                    print("      [!] Meal link not found in row.")

                safe_click(By.XPATH, '//a[contains(text(), "Back")]', "Back to menu list")
            except Exception as e:
                print(f"[X] Error in menu loop for '{name}' - {label}: {e}")
                break

        safe_click(By.XPATH, '//a[contains(text(), "Back")]', "Back to restaurant list")

    except Exception as e:
        print(f"[X] Error with restaurant: {e}")
        safe_click(By.XPATH, '//a[contains(text(), "Back")]', "Back (error recovery)")
        continue

driver.quit()

print("\n[✔] Scraping complete. Writing to file...")

# Filter out restaurants with no menu items
non_empty_halal_data = {
    r: cats for r, cats in halal_data.items()
    if any(meals for meals in cats.values())
}

with open("outputs/halal_menus.txt", "w", encoding="utf-8") as f:
    for restaurant, categories in non_empty_halal_data.items():
        # Add the hours if available
        hours = dining_hours.get(restaurant, "Hours not available")
        f.write(f"{restaurant} - {hours}\n")
        
        for category, meals in categories.items():
            if not meals:
                continue
            f.write(f"  {category}:\n")
            for meal in meals:
                f.write(f"    - {meal}\n")
        f.write("\n")
print("[✓] Data written to halal_menus.txt")

print("\n[✔] Generating colorful PDF...")

doc = SimpleDocTemplate("outputs/halal_menus.pdf", pagesize=letter)
elements = []
styles = getSampleStyleSheet()
title_style = styles['Title']
subtitle_style = ParagraphStyle(
    'Subtitle',
    parent=styles['Normal'],
    fontName='Helvetica-Oblique',
    fontSize=10,
    textColor=colors.HexColor("#444444"),
    alignment=TA_CENTER,
    spaceAfter=12
)
normal_style = styles['Normal']

table_header_style = ParagraphStyle(
    'TableHeader',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    fontSize=10,
    textColor=colors.white,
    alignment=TA_LEFT,
    spaceAfter=6
)

date_today = datetime.today().strftime('%A, %B %d, %Y')
elements.append(Paragraph(f"Halal @ Duke - {date_today}", title_style))
elements.append(Spacer(1, 12))

for idx, (restaurant, categories) in enumerate(non_empty_halal_data.items()):
    section_elements = []

    # Add restaurant name and hours if available
    section_elements.append(Paragraph(restaurant, title_style))
    
    # Add hours information
    hours = dining_hours.get(restaurant, "Hours not available")
    section_elements.append(Paragraph(f"{hours}", subtitle_style))
    section_elements.append(Spacer(0, 6))

    for category, meals in categories.items():
        if not meals:
            continue

        data = [[Paragraph(category, table_header_style)]] + [
            [Paragraph(meal, normal_style)] for meal in meals
        ]

        t = Table(data, colWidths=[500])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f0f4f7")),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ]))

        section_elements.append(t)
        section_elements.append(Spacer(1, 10))

    section_elements.append(Spacer(1, 10))

    elements.extend(section_elements)

doc.build(elements)
print("[✓] PDF saved as 'halal_menus.pdf'")
