from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

# --- Helper Functions ---
def decode_email(encrypted_str, vector):
    try:
        decoded = []
        for i, char in enumerate(encrypted_str.replace(",", "")):
            decoded_char = chr(ord(char) - vector - i)
            decoded.append(decoded_char)
        return ''.join(decoded)
    except:
        return ""

def extract_email(dealer_element):
    try:
        email_link = dealer_element.find_element(By.CSS_SELECTOR, "a[data-mailto-token]")
        encrypted = email_link.get_attribute("data-mailto-token")
        vector = int(email_link.get_attribute("data-mailto-vector"))
        email = decode_email(encrypted, vector)
        if "@" in email:
            return email
        visible_text = email_link.text.strip()
        if "@" in visible_text:
            return visible_text
    except:
        pass
    return ""

def select_option_from_dropdown(dropdown_element, option_text):
    dropdown_element.click()
    time.sleep(1)
    options = dropdown_element.find_elements(By.CSS_SELECTOR, ".choices__item--selectable")
    seen_texts = set()
    max_scroll_attempts = 30

    print(f"         🔍 Trying to select: '{option_text}'")

    for attempt in range(max_scroll_attempts):
        for opt in options:
            text = opt.text.strip()
            if text and text not in seen_texts:
                seen_texts.add(text)
                print(f"            🔍 Option: '{text}'")
                if text.lower() == option_text.strip().lower():
                    opt.click()
                    time.sleep(2)
                    return True

        if options:
            ActionChains(dropdown_element.parent).move_to_element(options[-1]).perform()
            time.sleep(0.5)

        options = dropdown_element.find_elements(By.CSS_SELECTOR, ".choices__item--selectable")

    print(f"         ❌ Could not find '{option_text}' in dropdown")
    return False

def get_options_from_dropdown(dropdown_element):
    dropdown_element.click()
    time.sleep(1)
    options = dropdown_element.find_elements(By.CSS_SELECTOR, ".choices__item--selectable")
    texts = [opt.text.strip() for opt in options if opt.text.strip() and not opt.text.lower().startswith("choose your")]
    dropdown_element.click()
    time.sleep(1)
    return texts

# --- Setup WebDriver ---
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.maximize_window()
driver.get("https://www.sennebogen.com/en/service/dealer-search")
wait = WebDriverWait(driver, 20)

# Accept cookies
try:
    accept_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]")))
    accept_button.click()
    print("✅ Cookies accepted")
except:
    print("⚠️ Cookie popup not found")

master_data = []

# Get all available continents
continent_dropdown = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".choices")))[0]
continent_list = get_options_from_dropdown(continent_dropdown)

for continent in continent_list:
    print(f"\n🌍 CONTINENT: {continent}")

    continent_dropdown = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".choices")))[0]
    if not select_option_from_dropdown(continent_dropdown, continent):
        print(f"❌ Could not select continent {continent}, skipping")
        continue
    time.sleep(2)

    country_dropdown = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".choices")))[1]
    country_list = get_options_from_dropdown(country_dropdown)
    print(f"Found {len(country_list)} countries in {continent}")

    for country in country_list:
        print(f"\n   🏳️ COUNTRY: {country}")
        try:
            country_dropdown = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".choices")))[1]

            if not select_option_from_dropdown(country_dropdown, country):
                print(f"      ❌ Could not select country {country}, skipping")
                continue

            time.sleep(3)

            dealer_blocks = driver.find_elements(By.CSS_SELECTOR, ".c-storelocator__item")
            if not dealer_blocks:
                print("      🚫 No dealers found")
                continue

            print(f"      Found {len(dealer_blocks)} dealers")

            for dealer in dealer_blocks:
                try:
                    name = dealer.find_element(By.CSS_SELECTOR, "h3.c-storelocator__item-header").text.strip()
                    email = extract_email(dealer)

                    website_elem = dealer.find_elements(By.CSS_SELECTOR, ".basicdata a.c-storelocator__link")
                    website = website_elem[0].get_attribute("href") if website_elem else ""

                    data = {
                        "Continent": continent,
                        "Country": country,
                        "Company Name": name,
                        "Website": website,
                        "Email": email
                    }
                    master_data.append(data)
                except Exception as e:
                    print(f"         ⚠️ Error processing dealer: {e}")

            # Save after each country
            df = pd.DataFrame(master_data)
            df.to_csv("sennebogen_dealers_basic.csv", index=False)
            print(f"      ✅ Saved data after {country}")

        except Exception as e:
            print(f"❌ Error processing country {country}: {e}")

print(f"\n✅ Finished scraping {len(master_data)} dealers.")
driver.quit()
