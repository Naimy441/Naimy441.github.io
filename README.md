# Islam @ Duke Scraper — How to Use

Visit the website [naimy441.github.io](https://naimy441.github.io) to view the latest PDF version of the halal menus and muslim events.

Alternatively, you can clone this repository and use the scraper scripts provided:

- Use `scrape.py` to run the scraper with an open Chrome window (useful for debugging or watching the scraper in action).
- Use `bot_scrape.py` to run the scraper in headless mode (recommended for automation or GitHub Actions).
- Use `get_muslim_calendar.py` to get ICS resource from DukeGroups and output as PDF.

The scripts generate two files:
- `halal_menus.pdf`: A nicely formatted, colorful PDF version of the scraped menus.
- `halal_menus.txt`: A simplified, plain-text version of the menus.
- `muslim_calendar.py`: A nicely formatted, colorful PDF version of the scraped events.

---

## 1. Install Python

Make sure you have **Python 3.x** installed. You can check by running:

```bash
python --version
```

If it’s not installed, [download Python here](https://www.python.org/downloads/).

---

## 2. Install Required Packages

Open your terminal or command prompt and run:

```bash
pip install -r requirements.txt
```

This will install:

- **selenium**: Browser automation library  
- **webdriver-manager**: Automatically downloads the correct version of ChromeDriver
- **reportlab**: Generates PDF output
- **requests**: Pulls ICS feed for calendar
- **beautifulsoup4**: Scrapes Campus Hours

---

## 3. Run the Script

After cloning the repository, navigate to its directory and run one of the following scripts:

**For visual (windowed) scraping:**

```bash
python src/scrape.py
```

**For headless scraping (no visible browser window):**

```bash
python src/bot_scrape.py
```

**For headless scraping (WARNING: this will scrape over 100 pages of food items):**

```bash
python src/full_scrape.py
```

---

## 4. What Happens

- The script parses the Campus Hours website for restaurant timings
- The script opens Duke’s NetNutrition website  
- Dismisses the initial popup  
- Applies the “Halal” filter  
- Visits each **open** dining unit  
- Collects **menu categories and Halal meals**  
- Writes the result into two output files:

```
halal_menus.txt
halal_menus.pdf
```

- The script gets the ICS feed directly from DukeGroups
- Writes the result into one output files:

```
muslim_calendar.pdf
```

 - The calendar includes events from the following groups:
```
28807 - CML
28808 - MSA
28704 - Graduate and Professional MSA
28600 - Duke Students for Justice in Palestine
72105 - Duke Black Muslim Coalition
73950 - One for All
```

---

## 5. Output Example (`halal_menus.txt`)

```
Gothic Grill
  Build Your Own Taco Protein:
    - Grilled Chicken Breast
  Build Your Own Burger (Choose Your Ingredients):
    - Beef Patty
```

The PDF version (`halal_menus.pdf`) will have a similar layout but in a visually appealing format.

---

## 6. Notes

- Ensure **Google Chrome** is installed (required by Selenium).
- ChromeDriver installation is automatic, handled by `webdriver-manager`.
- The script automatically skips **closed restaurants** and removes **duplicate meal names**.
- `full_scrape.py` will **not** skip closed restaurants and will scrape **every** food item and topping
