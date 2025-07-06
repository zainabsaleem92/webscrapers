from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import re

# Setup
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.maximize_window()
driver.get("https://www.wirtgen-group.com/en-in/parts-and-service/sales-and-service-worldwide/")
wait = WebDriverWait(driver, 20)

# Accept cookies
try:
    accept_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]")))
    accept_btn.click()
    print("✅ Cookies accepted")
except:
    print("⚠️ Cookie popup not found")

# Handle location confirmation modal
try:
    continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
    continue_btn.click()
    print("✅ Location modal dismissed")
except:
    print("⚠️ Location modal not found")


master_data = []

# Get all continent options
continent_dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select.select.dealer__region")))
continent_options = continent_dropdown.find_elements(By.TAG_NAME, "option")
continents = [(opt.get_attribute("value"), opt.text.strip()) for opt in continent_options if opt.get_attribute("value")]

for continent_value, continent_label in continents:
    print(f"\n🌍 CONTINENT: {continent_label}")

    # Select continent
    driver.execute_script(f"document.querySelector('select.select.dealer__region').value = '{continent_value}';")
    driver.execute_script("document.querySelector('select.select.dealer__region').dispatchEvent(new Event('change'));")
    time.sleep(2)

    # Wait for country dropdown to load
    try:
        country_dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select.select.dealer__country")))
        country_options = country_dropdown.find_elements(By.TAG_NAME, "option")
        countries = [(opt.get_attribute("value"), opt.text.strip()) for opt in country_options if opt.get_attribute("value")]
    except:
        print("❌ Could not find countries for this continent")
        continue

    for country_value, country_label in countries:
        print(f"   🏳️ COUNTRY: {country_label}")

        try:
            # Select country
            driver.execute_script(f"document.querySelector('select.select.dealer__country').value = '{country_value}';")
            driver.execute_script("document.querySelector('select.select.dealer__country').dispatchEvent(new Event('change'));")
            time.sleep(2)

            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".row.dealer__item")))
            dealers = driver.find_elements(By.CSS_SELECTOR, ".row.dealer__item")
            print(f"      Found {len(dealers)} dealers")

            for dealer in dealers:
                try:
                    name = dealer.find_element(By.CSS_SELECTOR, "h3.hdl").text.strip()

                    # Try getting email via visible text
                    email_elem = dealer.find_elements(By.CSS_SELECTOR, '.iconlist__content a[href^="javascript:window.location.href"]')
                    if email_elem:
                        # Visible version
                        email_text = email_elem[0].text.strip()
                        email = email_text if "@" in email_text else ""

                        # Parse JS fallback
                        if not email:
                            href = email_elem[0].get_attribute("href")
                            match = re.search(r"\['(.+?)','(.+?)'\]", href)
                            if match:
                                email = f"{match.group(1)}@{match.group(2)}"
                    else:
                        email = ""

                    website = ""  # Not available in DOM per sample

                    #print(f"         ✅ {name} | 📧 {email}")
                    master_data.append({
                        "Continent": continent_label,
                        "Country": country_label,
                        "Name": name,
                        "Email": email,
                        "Website": website
                    })

                except Exception as e:
                    print(f"         ⚠️ Error extracting dealer info: {e}")

        except Exception as e:
            print(f"      ❌ Error loading dealers for country {country_label}: {e}")

        # Save after each country
        df = pd.DataFrame(master_data)
        df.to_csv("wirtgen_dealers.csv", index=False)
        print(f"      💾 Saved data after {country_label}")

print("\n✅ Finished scraping.")
driver.quit()
