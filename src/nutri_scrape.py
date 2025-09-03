from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json

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


SECONDS_TO_WAIT = 0.5  # Reduced wait time for faster scraping

# Initialize driver
print("Initializing Chrome driver...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://netnutrition.cbord.com/nn-prod/Duke")
print("Page loaded.")

def safe_click(by, selector, desc="element", delay=SECONDS_TO_WAIT):
    try:
        elem = driver.find_element(by, selector)
        driver.execute_script("arguments[0].click();", elem)
        # print(f"[✓] Clicked {desc}")
        time.sleep(delay)
        return True
    except Exception as e:
        # print(f"[X] Could not click {desc}: {e}")
        return False

def scrape_nutrition_modal():
    """Scrape nutrition information from the modal dialog"""
    try:
        # Wait for modal to appear and find the nutrition dialog
        time.sleep(SECONDS_TO_WAIT * 0.5)  # Shorter wait for modal
        nutrition_dialog = driver.find_element(By.ID, "cbo_nn_nutritionDialogInner")
        
        nutrition_data = {}
        
        # Get the food item name
        try:
            name_elem = nutrition_dialog.find_element(By.CSS_SELECTOR, ".cbo_nn_LabelHeader")
            nutrition_data["item_name"] = name_elem.text.strip()
        except:
            nutrition_data["item_name"] = None
            
        # Get serving information
        try:
            serving_elem = nutrition_dialog.find_element(By.CSS_SELECTOR, ".cbo_nn_LabelBottomBorderLabel")
            serving_text = serving_elem.text.strip()
            
            # Parse serving information
            serving_info = {}
            lines = serving_text.split('\n')
            
            # Extract servings per container
            for line in lines:
                if 'Servings per container' in line:
                    servings_match = re.search(r'(\d+)\s*Servings per container', line)
                    if servings_match:
                        serving_info["servings_per_container"] = int(servings_match.group(1))
                    break
            
            # Extract serving size - look for the line that contains serving size info
            for line in lines:
                if 'Serving Size' in line:
                    # Extract everything after "Serving Size" (with or without space)
                    serving_size_match = re.search(r'Serving Size\s*(.+)', line)
                    if serving_size_match:
                        serving_info["serving_size"] = serving_size_match.group(1).strip()
                    else:
                        # Handle cases like "Serving Size1 lb Portion (453g)"
                        serving_size_match = re.search(r'Serving Size(.+)', line)
                        if serving_size_match:
                            serving_info["serving_size"] = serving_size_match.group(1).strip()
                elif line.strip() and 'Servings per container' not in line and 'Serving Size' not in line:
                    # This might be a serving size line without the "Serving Size" label
                    # Check if it looks like a serving size (contains units like oz, g, lb, etc.)
                    if re.search(r'\b\d+.*(?:oz|g|ml|cup|piece|slice|tbsp|tsp|fl oz|lb|lbs|portion)\b', line, re.IGNORECASE):
                        if "serving_size" not in serving_info:  # Only set if we haven't found one yet
                            serving_info["serving_size"] = line.strip()
            
            nutrition_data["serving_info"] = serving_info
        except:
            nutrition_data["serving_info"] = None
            
        # Get calories
        try:
            calories_elem = nutrition_dialog.find_element(By.CSS_SELECTOR, ".cbo_nn_LabelSubHeader .font-22")
            nutrition_data["calories"] = calories_elem.text.strip()
        except:
            nutrition_data["calories"] = None
            
        # Get main nutrition facts
        nutrition_facts = {}
        try:
            bordered_headers = nutrition_dialog.find_elements(By.CSS_SELECTOR, ".cbo_nn_LabelBorderedSubHeader")
            for header in bordered_headers:
                try:
                    left_div = header.find_element(By.CSS_SELECTOR, ".inline-div-left")
                    right_div = header.find_element(By.CSS_SELECTOR, ".inline-div-right")
                    
                    # Extract nutrient name and amount
                    left_text = left_div.text.strip()
                    right_text = right_div.text.strip()
                    
                    # Skip if it's the added sugars row with "Include NA"
                    if "Include NA" in left_text:
                        continue
                    
                    # Extract nutrient name and amount using regex
                    # Pattern matches things like "Total Fat 25g", "Saturated Fat 9g", "Trans Fat NA"
                    match = re.match(r'(.+?)\s+([\d.]+(?:\.\d+)?[a-zA-Z]*|NA)$', left_text)
                    if match:
                        nutrient_name = match.group(1).strip()
                        amount_str = match.group(2).strip()
                        
                        nutrient_info = {}
                        
                        # Parse amount and unit
                        if amount_str == "NA":
                            nutrient_info["amount"] = None
                            nutrient_info["unit"] = None
                        else:
                            amount_match = re.match(r'([\d.]+)(.*)', amount_str)
                            if amount_match:
                                try:
                                    nutrient_info["amount"] = float(amount_match.group(1))
                                except:
                                    nutrient_info["amount"] = amount_match.group(1)
                                nutrient_info["unit"] = amount_match.group(2) if amount_match.group(2) else None
                            else:
                                nutrient_info["amount"] = amount_str
                                nutrient_info["unit"] = None
                        
                        # Parse daily value percentage
                        if right_text and right_text.strip() and right_text.strip() != "%":
                            try:
                                # Remove % sign and convert to float
                                daily_value_str = right_text.replace('%', '').strip()
                                if daily_value_str:
                                    nutrient_info["daily_value_percent"] = float(daily_value_str)
                                else:
                                    nutrient_info["daily_value_percent"] = None
                            except:
                                nutrient_info["daily_value_percent"] = None
                        else:
                            nutrient_info["daily_value_percent"] = None
                        
                        nutrition_facts[nutrient_name] = nutrient_info
                    else:
                        # Fallback for cases that don't match the pattern
                        nutrition_facts[left_text] = {
                            "amount": None,
                            "unit": None,
                            "daily_value_percent": None
                        }
                except:
                    continue
        except:
            pass
            
        nutrition_data["nutrition_facts"] = nutrition_facts
        
        # Get secondary nutrients (vitamins/minerals)
        secondary_nutrients = {}
        try:
            secondary_table = nutrition_dialog.find_element(By.CSS_SELECTOR, ".cbo_nn_LabelSecondaryTable")
            secondary_rows = secondary_table.find_elements(By.CSS_SELECTOR, ".cbo_nn_LabelBorderedSubHeader, .cbo_nn_LabelNoBorderSubHeader")
            for row in secondary_rows:
                try:
                    left_div = row.find_element(By.CSS_SELECTOR, ".inline-div-left")
                    right_div = row.find_element(By.CSS_SELECTOR, ".inline-div-right")
                    
                    left_text = left_div.text.strip()
                    right_text = right_div.text.strip()
                    
                    # Extract nutrient name and amount using regex
                    match = re.match(r'(.+?)\s+([\d.]+(?:\.\d+)?[a-zA-Z]*|NA)$', left_text)
                    if match:
                        nutrient_name = match.group(1).strip()
                        amount_str = match.group(2).strip()
                        
                        # Skip if this nutrient is already in nutrition_facts to avoid duplicates
                        if nutrient_name in nutrition_facts:
                            continue
                        
                        nutrient_info = {}
                        
                        # Parse amount and unit
                        if amount_str == "NA":
                            nutrient_info["amount"] = None
                            nutrient_info["unit"] = None
                        else:
                            amount_match = re.match(r'([\d.]+)(.*)', amount_str)
                            if amount_match:
                                try:
                                    nutrient_info["amount"] = float(amount_match.group(1))
                                except:
                                    nutrient_info["amount"] = amount_match.group(1)
                                nutrient_info["unit"] = amount_match.group(2) if amount_match.group(2) else None
                            else:
                                nutrient_info["amount"] = amount_str
                                nutrient_info["unit"] = None
                        
                        # Parse daily value percentage
                        if right_text and right_text.strip() and right_text.strip() != "%":
                            try:
                                # Remove % sign and convert to float
                                daily_value_str = right_text.replace('%', '').strip()
                                if daily_value_str:
                                    nutrient_info["daily_value_percent"] = float(daily_value_str)
                                else:
                                    nutrient_info["daily_value_percent"] = None
                            except:
                                nutrient_info["daily_value_percent"] = None
                        else:
                            nutrient_info["daily_value_percent"] = None
                        
                        secondary_nutrients[nutrient_name] = nutrient_info
                    else:
                        # Fallback for cases that don't match the pattern
                        # Only add if not already in nutrition_facts
                        if left_text not in nutrition_facts:
                            secondary_nutrients[left_text] = {
                                "amount": None,
                                "unit": None,
                                "daily_value_percent": None
                            }
                except:
                    continue
        except:
            pass
            
        nutrition_data["secondary_nutrients"] = secondary_nutrients
        
        # Get ingredients
        try:
            ingredients_elem = nutrition_dialog.find_element(By.CSS_SELECTOR, ".cbo_nn_LabelIngredients")
            nutrition_data["ingredients"] = ingredients_elem.text.strip()
        except:
            nutrition_data["ingredients"] = None
            
        # Get allergens
        try:
            allergens_elem = nutrition_dialog.find_element(By.CSS_SELECTOR, ".cbo_nn_LabelAllergens")
            nutrition_data["allergens"] = allergens_elem.text.strip()
        except:
            nutrition_data["allergens"] = None
            
        # Close the modal using the specific close button
        try:
            close_button = driver.find_element(By.ID, "btn_nn_nutrition_close")
            driver.execute_script("arguments[0].click();", close_button)
            time.sleep(SECONDS_TO_WAIT * 0.3)  # Shorter wait after closing
            # print(f"      [Nutrition] Modal closed successfully")  # Reduced logging
        except Exception as close_error:
            # print(f"      [Nutrition] Error closing modal: {close_error}")  # Reduced logging
            # Fallback: try pressing Escape key
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(SECONDS_TO_WAIT * 0.3)
            except:
                pass
        
        return nutrition_data
        
    except Exception as e:
        # print(f"      [X] Error scraping nutrition modal: {e}")
        # Try to close modal even if scraping failed
        try:
            close_button = driver.find_element(By.ID, "btn_nn_nutrition_close")
            driver.execute_script("arguments[0].click();", close_button)
            time.sleep(SECONDS_TO_WAIT * 0.3)  # Shorter wait
        except:
            # Fallback to Escape key if close button not found
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(SECONDS_TO_WAIT * 0.2)  # Very short wait
            except:
                pass
        return None

# Step 1: Dismiss modal
# print("\n[Step 1] Dismissing modal...")
time.sleep(SECONDS_TO_WAIT)
safe_click(By.XPATH, '//button[contains(@onclick, "setIgnoreMobileDisc")]', "Continue button")

# Step 3: Iterate through open dining units
# print("\n[Step 3] Iterating through dining units...")
halal_data = {}
units = driver.find_elements(By.CSS_SELECTOR, ".card.unit")
# print(f"Found {len(units)} total units.")

for unit in units:
    try:
        status = unit.find_element(By.CLASS_NAME, "badge").text.lower()

        name = unit.find_element(By.TAG_NAME, "a").text.strip()
        # print(f"\n[Unit] Opening: {name}")
        driver.execute_script("arguments[0].click();", unit.find_element(By.TAG_NAME, "a"))
        time.sleep(SECONDS_TO_WAIT)

        # Locate menu panel
        menu_links = []
        try:
            menu_data_list = driver.find_element(By.ID, "cbo_nn_menuDataList")
            card_blocks = menu_data_list.find_elements(By.CSS_SELECTOR, "div.card-block")
            # print(f"  Found {len(card_blocks)} card blocks in menu panel.")
            if card_blocks:
                first_block = card_blocks[0]
                menu_links = first_block.find_elements(By.CSS_SELECTOR, "a.cbo_nn_menuLink")
                # print(f"  Found {len(menu_links)} menu links.")
        except NoSuchElementException:
            # print(f"  No menu panel found for {name} — checking if menu is already displayed...")
            pass

        # If no menu links, check if already inside itemPanel directly
        if not menu_links:
            try:
                item_panel = driver.find_element(By.ID, "itemPanel")
                panel_text = item_panel.text
                if "There are no items available" in panel_text:
                    # print("  No items available.")
                    pass
                else:
                    # print("  ✔ Menu has items (auto-loaded)!")
                    if name not in halal_data:
                        halal_data[name] = {}

                    rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
                    # print(f"  Found {len(rows)} rows in menu table.")

                    current_category = None

                    for idx, row in enumerate(rows):
                        row_class = row.get_attribute("class")
                        # print(f"    Row {idx} class: {row_class}")

                        if "itemGroupRow" in row_class:
                            try:
                                category_text = row.find_element(By.CSS_SELECTOR, "div[role='button']").text.strip()
                                current_category = category_text
                                # print(f"\n    [Category] {current_category}")
                                if current_category and current_category not in halal_data[name]:
                                    halal_data[name][current_category] = []
                            except NoSuchElementException as e:
                                # print(f"    [X] Failed to extract category: {e}")
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
                                    # Check if the meal has a halal image
                                    is_halal = False
                                    try:
                                        imgs = meal_elem.find_elements(By.TAG_NAME, "img")
                                        for img in imgs:
                                            if "halal" in img.get_attribute("alt").strip().lower():
                                                is_halal = True
                                                break
                                    except Exception:
                                        pass

                                    # Click nutrition label link if it exists
                                    nutrition_data = None
                                    try:
                                        nutrition_link = row.find_element(By.CSS_SELECTOR, "a[id^='showNutrition_'].cbo_nn_itemHover")
                                        nutrition_id = nutrition_link.get_attribute("id")
                                        # print(f"      [Nutrition] Found nutrition link: {nutrition_id}")
                                        driver.execute_script("arguments[0].click();", nutrition_link)
                                        time.sleep(SECONDS_TO_WAIT)
                                        
                                        # Scrape nutrition data from modal
                                        nutrition_data = scrape_nutrition_modal()
                                        if nutrition_data:
                                            pass
                                            # print(f"      [Nutrition] Successfully scraped nutrition data for {meal_name}")
                                            # print(f"      [Nutrition Data] {json.dumps(nutrition_data, indent=2, ensure_ascii=False)}")
                                        else:
                                            # print(f"      [Nutrition] Failed to scrape nutrition data for {meal_name}")
                                            pass
                                            
                                    except NoSuchElementException:
                                        # print(f"      [Nutrition] No nutrition link found for {meal_name}")
                                        pass
                                    except Exception as e:
                                        # print(f"      [Nutrition] Error clicking nutrition link for {meal_name}: {e}")
                                        pass

                                    # print(f"      [Meal] {meal_name} | Halal: {is_halal}")
                                    halal_data[name][current_category].append({
                                        "name": meal_name, 
                                        "is_halal": is_halal,
                                        "nutrition": nutrition_data
                                    })
                            except NoSuchElementException:
                                # print("      [!] Meal link not found in row.")
                                pass

                # Go back to restaurant list
                safe_click(By.XPATH, '//a[contains(text(), "Back")]', "Back to restaurant list")
                continue  # Skip normal menu loop
            except NoSuchElementException:
                # print(f"  [X] Neither menu panel nor item panel found for {name}. Skipping.")
                pass
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
                # print(f"\n[Menu] Clicking: {label}")
                driver.execute_script("arguments[0].click();", menu_link)
                time.sleep(SECONDS_TO_WAIT)

                item_panel = driver.find_element(By.ID, "itemPanel")
                panel_text = item_panel.text
                if "There are no items available" in panel_text:
                    # print("  No items available — skipping menu.")
                    pass
                else:
                    # print("  ✔ Menu has items!")
                    if name not in halal_data:
                        halal_data[name] = {}

                    rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
                    # print(f"  Found {len(rows)} rows in menu table.")

                    current_category = None

                    for idx, row in enumerate(rows):
                        row_class = row.get_attribute("class")
                        # print(f"    Row {idx} class: {row_class}")

                        if "itemGroupRow" in row_class:
                            try:
                                category_text = row.find_element(By.CSS_SELECTOR, "div[role='button']").text.strip()
                                current_category = category_text
                                # print(f"\n    [Category] {current_category}")
                                if current_category and current_category not in halal_data[name]:
                                    halal_data[name][current_category] = []
                            except NoSuchElementException as e:
                                # print(f"    [X] Failed to extract category: {e}")
                                current_category = None

                        elif "itemPrimaryRow" in row_class or "itemAlternateRow" in row_class:
                            if current_category:
                                try:
                                    meal_elem = row.find_element(By.CSS_SELECTOR, "td a.cbo_nn_itemHover")
                                    meal_full_text = meal_elem.get_attribute("innerText").strip()
                                    meal_name = meal_full_text.split("\n")[0]  # Get only the first line
                                    if meal_name:
                                        # Check if the meal has a halal image
                                        is_halal = False
                                        try:
                                            imgs = meal_elem.find_elements(By.TAG_NAME, "img")
                                            for img in imgs:
                                                if "halal" in img.get_attribute("alt").strip().lower():
                                                    is_halal = True
                                                    break
                                        except Exception:
                                            pass

                                        # Click nutrition label link if it exists
                                        nutrition_data = None
                                        try:
                                            nutrition_link = row.find_element(By.CSS_SELECTOR, "a[id^='showNutrition_'].cbo_nn_itemHover")
                                            nutrition_id = nutrition_link.get_attribute("id")
                                            # print(f"      [Nutrition] Found nutrition link: {nutrition_id}")
                                            driver.execute_script("arguments[0].click();", nutrition_link)
                                            time.sleep(SECONDS_TO_WAIT)
                                            
                                            # Scrape nutrition data from modal
                                            nutrition_data = scrape_nutrition_modal()
                                            if nutrition_data:
                                                # print(f"      [Nutrition] Successfully scraped nutrition data for {meal_name}")
                                                pass
                                                # print(f"      [Nutrition Data] {json.dumps(nutrition_data, indent=2, ensure_ascii=False)}")
                                            else:
                                                # print(f"      [Nutrition] Failed to scrape nutrition data for {meal_name}")
                                                pass
                                                
                                        except NoSuchElementException:
                                            # print(f"      [Nutrition] No nutrition link found for {meal_name}")
                                            pass
                                        except Exception as e:
                                            # print(f"      [Nutrition] Error clicking nutrition link for {meal_name}: {e}")
                                            pass

                                        # print(f"      [Meal] {meal_name} | Halal: {is_halal}")
                                        halal_data[name][current_category].append({
                                            "name": meal_name, 
                                            "is_halal": is_halal,
                                            "nutrition": nutrition_data
                                        })
                                except NoSuchElementException:
                                    # print("      [!] Meal link not found in row.")
                                    pass

                safe_click(By.XPATH, '//a[contains(text(), "Back")]', "Back to menu list")
            except Exception as e:
                # print(f"[X] Error in menu loop for '{name}' - {label}: {e}")
                break

        safe_click(By.XPATH, '//a[contains(text(), "Back")]', "Back to restaurant list")

    except Exception as e:
        # print(f"[X] Error with restaurant: {e}")
        safe_click(By.XPATH, '//a[contains(text(), "Back")]', "Back (error recovery)")
        continue

driver.quit()

# print("\n[✔] Scraping complete. Writing to file...")

# Filter out restaurants with no menu items
non_empty_halal_data = {
    r: cats for r, cats in halal_data.items()
    if any(meals for meals in cats.values())
}

# Structure data for JSON output
json_output = {
    "timestamp": datetime.now().isoformat(),
    "restaurants": []
}

for restaurant, categories in non_empty_halal_data.items():
    hours = dining_hours.get(restaurant, "Hours not available")
    restaurant_data = {
        "name": restaurant,
        "hours": hours,
        "categories": []
    }
    
    for category, meals in categories.items():
        if not meals:
            continue
        category_data = {
            "name": category,
            "meals": meals
        }
        restaurant_data["categories"].append(category_data)
    
    json_output["restaurants"].append(restaurant_data)

with open("outputs/nutri_menus.json", "w", encoding="utf-8") as f:
    json.dump(json_output, f, indent=2, ensure_ascii=False)
print("[✓] Data written to nutri_menus.json")
