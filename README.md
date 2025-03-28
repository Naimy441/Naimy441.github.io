# Duke Halal Menu Scraper — How to Use

Visit the website [naimy441.github.io](https://naimy441.github.io) to view the latest PDF version of the halal menus.

Alternatively, you can clone this repository and use the scraper scripts provided:

- Use `scrape.py` to run the scraper with an open Chrome window (useful for debugging or watching the scraper in action).
- Use `bot_scrape.py` to run the scraper in headless mode (recommended for automation or GitHub Actions).

The scripts generate two files:
- `halal_menus.pdf`: A nicely formatted, colorful PDF version of the scraped menus.
- `halal_menus.txt`: A simplified, plain-text version of the menus.

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

---

## 3. Run the Script

After cloning the repository, navigate to its directory and run one of the following scripts:

**For visual (windowed) scraping:**

```bash
python scrape.py
```

**For headless scraping (no visible browser window):**

```bash
python bot_scrape.py
```

---

## 4. What Happens

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
