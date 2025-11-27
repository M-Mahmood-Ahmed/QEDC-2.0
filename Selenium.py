from datetime import datetime
from pathlib import Path
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import undetected_chromedriver as uc
import pandas as pd
import json
import os
import re
import logging

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def init_driver():
    """Initialize the undetected ChromeDriver with options and random user agent."""
    try:
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--headless")

        useragentarray = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        ]

        # driver = uc.Chrome(options=chrome_options)
        driver = uc.Chrome(options=chrome_options)
        # driver = uc.Chrome(options=chrome_options, driver_executable_path=r"D:\Work\chromedriver\chromedriver.exe")
        user_agent = random.choice(useragentarray)
        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride", {"userAgent": user_agent}
        )

        return driver

    except Exception as e:
        logging.error("Error initializing the driver:", e)
        return None


def login_to_linkedin(driver, username, password):
    """Log in to LinkedIn account."""
    try:
        logging.info("Navigating to LinkedIn login page...")
        driver.get("https://www.linkedin.com/login")

        # Wait for the login page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        logging.info("Filling in the login credentials...")
        time.sleep(random.uniform(2, 4))
        email_input = driver.find_element(By.ID, "username")
        password_input = driver.find_element(By.ID, "password")

        email_input.send_keys(username)
        password_input.send_keys(password)

        login_button = driver.find_element(By.XPATH, '//button[@type="submit"]')
        login_button.click()
        time.sleep(random.uniform(2, 4))

        # Wait for the page to navigate away from the login page
        WebDriverWait(driver, 20).until(lambda d: "login" not in d.current_url)

        # CAPTCHA and additional verification checks
        if "checkpoint" in driver.current_url:
            logging.info("CAPTCHA detected. Please solve it manually.")
            input("Press Enter once you've solved the CAPTCHA and the page has loaded.")

        if "authwall" in driver.current_url:
            logging.info(
                "Phone verification required. Please verify your phone number."
            )
            input("Press Enter once you've verified and the page has loaded.")

        # Final login check
        if "login" in driver.current_url:
            logging.warning("Login failed. Still on the login page.")
            return False
        else:
            logging.info("Successfully logged in!")
            return True

    except Exception as e:
        logging.error(f"Error during login: {e}")
        try:
            driver.quit()
        except Exception as quit_error:
            logging.warning(f"Error while quitting the driver: {quit_error}")
        return False


def extract_relevant_data(soup):
    # Required headings to cross-check
    required_headings = {
        "Website": "-",
        "Industry": "-",
        "Company size": "-",
        "No. of associated members": "-",
        "Headquarters": "-",
        "Founded": "-",
        "Specialties": "-",
    }

    # Initialize the dictionary with default values
    result = required_headings.copy()

    # Find all dt and dd elements
    dt_elements = soup.find_all("dt")
    # dd_elements = soup.find_all('dd')

    # Iterate through dt elements to extract headings and their corresponding values
    for dt in dt_elements:
        heading = dt.get_text(strip=True)
        dd = dt.find_next_sibling("dd")  # Get the next sibling dd element

        if heading == "Company size":
            # Special case for Company size and No. of associated members
            if dd:
                company_size_text = dd.get_text(strip=True)
                company_size_match = re.search(
                    r".*(?=\s*employees)", company_size_text, re.IGNORECASE
                )
                if company_size_match:
                    result["Company size"] = "'" + company_size_match.group().strip()

                # Check for the next dd for No. of associated members
                next_dd = dd.find_next_sibling("dd")
                if next_dd:
                    associated_members_text = next_dd.get_text(strip=True)
                    associated_members_match = re.search(
                        r"[\d,]+(?=\s*associated member[s]?)",
                        associated_members_text,
                        re.IGNORECASE,
                    )
                    if associated_members_match:
                        result["No. of associated members"] = (
                            associated_members_match.group().strip()
                        )
        elif heading in result:
            # For other headings
            if dd:
                result[heading] = dd.get_text(strip=True)

    return result


def associated_members(soup):
    associated_members = "-"
    # Find the div with the specific class
    org_people_div = soup.find("div", class_="org-people__header-spacing-carousel")

    # Extract the text from the h2 element
    associated_members_text = org_people_div.find("h2").get_text(strip=True)

    # Adjusted regex to match both "associated member" and "associated members"
    associated_members_match = re.search(
        r"[\d,]+(?=\s*associated member[s]?)", associated_members_text, re.IGNORECASE
    )

    if associated_members_match:
        associated_members = associated_members_match.group().strip()
        logging.info(f"Associated Members: {associated_members}")
    else:
        logging.info("Could not extract the associated members count.")

    return associated_members


def scrape_about_section(driver, base_url):
    """Scrape company information from the 'About' section of LinkedIn."""
    about_url = f"{base_url}/about/"
    start_time = datetime.now()
    try:
        driver.get(about_url)
        time.sleep(5)
        current_url = driver.current_url

        if current_url != about_url:
            logging.info(f"Redirected to {current_url} ...")
            if "/unavailable/" in current_url:
                logging.warning("Company not available on LinkedIn.")
                return {
                    "Company Name": "-",
                    "LinkedIn URL": base_url,
                    "Targeted URL": about_url,
                    "Redirected to URL": current_url,
                    "Time Stamp": start_time.isoformat(),
                }

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
        except Exception as e:
            logging.error(f"Error loading {about_url}: {str(e)}")
            about_data = {
                "Company Name": "-",
                "LinkedIn URL": base_url,
                "Error": str(e),
                "Time Stamp": start_time.isoformat(),
            }
            return about_data

        soup = BeautifulSoup(driver.page_source, "html.parser")
        about_data = {}

        # Extract fields with proper checks
        about_data["Company Name"] = (
            soup.find("h1").text.strip() if soup.find("h1") else "-"
        )
        try:
            extracted_data = extract_relevant_data(soup)
        except Exception as e:
            logging.error(f"Error extracting relevant data, error - {e}")
            extracted_data = {}

        # Append extracted_data to about_data
        about_data.update(extracted_data)

        # Add the LinkedIn URL and timestamp
        about_data["LinkedIn URL"] = base_url
        about_data["Time Stamp"] = start_time.isoformat()
        about_data["Redirected to URL"] = current_url

        return about_data

    except Exception as e:
        logging.error(f"Error scraping {about_url}: {str(e)}")
        about_data = {
            "Company Name": "-",
            "LinkedIn URL": base_url,
            "Error": str(e),
            "Time Stamp": start_time.isoformat(),
        }
        return about_data


def scrape_where_they_live_with_quantum(driver, base_url):
    """Scrape the 'Where They Live' data from the 'People' section."""
    location_url = f"{base_url}/people/?keywords=quantum"
    start_time = datetime.now()
    try:
        driver.get(location_url)
        time.sleep(6)
        current_url = driver.current_url
        if current_url != location_url:
            logging.info(f"Redirected to {current_url} ...")
            if "/unavailable/" in current_url:
                logging.warning("Company not available on LinkedIn.")
                about_data = {
                    "Company Name": "-",
                    "LinkedIn URL": base_url,
                    "Targeted URL": location_url,
                    "Redirected to URL": current_url,
                    "Time Stamp": start_time.isoformat(),
                }
                return about_data
        try:
            company_name = "-"
            soup = BeautifulSoup(driver.page_source, "html.parser")
            company_name_tag = soup.find("h1", class_="org-top-card-summary__title")
            company_name = (
                company_name_tag.get_text(strip=True) if company_name_tag else "-"
            )
        except Exception:
            logging.error(
                "Can't find the soup for the where they live with quantum ..."
            )
            data = {
                "Company Name": company_name,
                "Quantum Associated Members": "-",
                "Locations": "-",
                "Time Stamp": start_time.isoformat(),
                "Redirected to URL": current_url,
            }
            return data

        try:
            quantum_members_count = associated_members(soup)
        except Exception as e:
            logging.error(
                f"Unexpected error in associated memebers count ..., error - {e}"
            )
            quantum_members_count = "-"

        try:
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "org-people-bar-graph-element")
                )
            )
        except Exception:
            logging.warning(f"No QUANTUM member data found for {location_url} ---")
            data = {
                "Company Name": company_name,
                "Quantum Associated Members": quantum_members_count,
                "Locations": "-",
                "Time Stamp": start_time.isoformat(),
                "Redirected to URL": current_url,
            }
            return data

        where_they_live = []

        where_they_live_li = soup.find("li", {"data-item-index": "0"})
        if where_they_live_li:
            buttons = where_they_live_li.find_all(
                "button", class_="org-people-bar-graph-element"
            )
            for button in buttons:
                count = (
                    button.find("strong").text.strip() if button.find("strong") else "-"
                )
                location = (
                    button.find(
                        "span", class_="org-people-bar-graph-element__category"
                    ).text.strip()
                    if button.find("span")
                    else "-"
                )
                where_they_live.append({"Count": count, "Location": location})

        where_they_live_data = {
            "Company Name": company_name,
            "Quantum Associated Members": quantum_members_count,
            "Locations": where_they_live,
            "Time Stamp": start_time.isoformat(),
            "Redirected to URL": current_url,
        }

        return where_they_live_data

    except Exception as e:
        logging.error(f"Error scraping Where They Live with Quantum data: {e}")
        return {
            "Company Name": "-",
            "Quantum Associated Members": "-",
            "Locations": "-",
            "Time Stamp": start_time.isoformat(),
            "Error": str(e),
        }


def scrape_where_they_live_without_quantum(driver, base_url):
    """Scrape the 'Where They Live' data from the 'People' section."""
    location_url_wihout_quantum = f"{base_url}/people/"
    start_time = datetime.now()
    try:
        driver.get(location_url_wihout_quantum)
        time.sleep(6)
        current_url = driver.current_url
        if current_url != location_url_wihout_quantum:
            logging.info(f"Redirected to {current_url} ...")
            if "/unavailable/" in current_url:
                logging.warning("Company not available on LinkedIn.")
                about_data = {
                    "Company Name": "-",
                    "LinkedIn URL": base_url,
                    "Targeted URL": location_url_wihout_quantum,
                    "Redirected to URL": current_url,
                    "Time Stamp": start_time.isoformat(),
                }
                return about_data

        try:
            company_name = "-"
            soup = BeautifulSoup(driver.page_source, "html.parser")
            company_name_tag = soup.find("h1", class_="org-top-card-summary__title")
            company_name = (
                company_name_tag.get_text(strip=True) if company_name_tag else "-"
            )
        except Exception:
            logging.error(
                "Can't find the soup for the where they live with quantum ..."
            )
            data = {
                "Company Name": company_name,
                "Associated Members": "-",
                "Locations": "-",
                "Time Stamp": start_time.isoformat(),
                "Redirected to URL": current_url,
            }
            return data

        try:
            associated_members_count = associated_members(soup)
        except Exception as e:
            logging.error(
                f"Unexpected error in associated memebers count ..., error - {e}"
            )
            associated_members_count = "-"

        try:
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "org-people-bar-graph-element")
                )
            )
        except Exception:
            logging.warning(
                f"No member data found for {location_url_wihout_quantum} ---"
            )
            data = {
                "Company Name": company_name,
                "Associated Members": associated_members_count,
                "Locations": "-",
                "Time Stamp": start_time.isoformat(),
                "Redirected to URL": current_url,
            }
            return data

        where_they_live_without_quantum = []

        where_they_live_li = soup.find("li", {"data-item-index": "0"})
        if where_they_live_li:
            buttons = where_they_live_li.find_all(
                "button", class_="org-people-bar-graph-element"
            )
            for button in buttons:
                count = (
                    button.find("strong").text.strip() if button.find("strong") else "-"
                )
                location = (
                    button.find(
                        "span", class_="org-people-bar-graph-element__category"
                    ).text.strip()
                    if button.find("span")
                    else "-"
                )
                where_they_live_without_quantum.append(
                    {"Count": count, "Location": location}
                )

            where_they_live_without_quantum_data = {
                "Company Name": company_name,
                "Associated Members": associated_members_count,
                "Locations": where_they_live_without_quantum,
                "Time Stamp": start_time.isoformat(),
                "Redirected to URL": current_url,
            }
        return where_they_live_without_quantum_data

    except Exception as e:
        logging.error(f"Error scraping Where They Live without Quantum data: {e}")
        return {
            "Company Name": "-",
            "Associated Members": "-",
            "Locations": "-",
            "Time Stamp": start_time.isoformat(),
            "Error": str(e),
        }


def scrape_what_they_do_with_quantum(driver, base_url):
    """Scrape the 'What They Do' data from the 'People' section."""
    role_url = f"{base_url}/people/?keywords=quantum"
    start_time = datetime.now()

    try:
        driver.get(role_url)
        time.sleep(6)
        current_url = driver.current_url
        if current_url != role_url:
            logging.info(f"Redirected to {current_url} ...")
            if "/unavailable/" in current_url:
                logging.warning("Company not available on LinkedIn.")
                about_data = {
                    "Company Name": "-",
                    "LinkedIn URL": base_url,
                    "Targeted URL": role_url,
                    "Redirected to URL": current_url,
                    "Time Stamp": start_time.isoformat(),
                }
                return about_data

        try:
            company_name = "-"
            soup = BeautifulSoup(driver.page_source, "html.parser")
            company_name_tag = soup.find("h1", class_="org-top-card-summary__title")
            company_name = (
                company_name_tag.get_text(strip=True) if company_name_tag else "-"
            )
        except Exception:
            logging.error(
                "Can't find the soup for the where they live with quantum ..."
            )
            data = {
                "Company Name": company_name,
                "Quantum Associated Members": "-",
                "Roles": "-",
                "Time Stamp": start_time.isoformat(),
                "Redirected to URL": current_url,
            }
            return data

        try:
            quantum_members_count = associated_members(soup)
        except Exception as e:
            logging.error(
                f"Unexpected error in associated memebers count ..., error - {e}"
            )
            quantum_members_count = "-"

        try:
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "org-people-bar-graph-element")
                )
            )
        except Exception:
            logging.warning(f"No member data found for {role_url} ---")
            data = {
                "Company Name": company_name,
                "Quantum Associated Members": quantum_members_count,
                "Roles": "-",
                "Time Stamp": start_time.isoformat(),
                "Redirected to URL": current_url,
            }
            return data

        what_they_do = []
        what_they_do_li = soup.find("li", {"data-item-index": "2"})

        if what_they_do_li:
            buttons = what_they_do_li.find_all(
                "button", class_="org-people-bar-graph-element"
            )
            for button in buttons:
                count = (
                    button.find("strong").text.strip() if button.find("strong") else "-"
                )
                role = (
                    button.find(
                        "span", class_="org-people-bar-graph-element__category"
                    ).text.strip()
                    if button.find("span")
                    else "-"
                )
                what_they_do.append({"Count": count, "Role": role})

        what_they_do_data = {
            "Company Name": company_name,
            "Quantum Associated Members": quantum_members_count,
            "Roles": what_they_do,
            "Time Stamp": start_time.isoformat(),
            "Redirected to URL": current_url,
        }

        return what_they_do_data

    except Exception as e:
        logging.error(f"Error scraping What They Do with Quantum data: {e}")
        return {
            "Company Name": "-",
            "Quantum Associated Members": "-",
            "Roles": "-",
            "Time Stamp": start_time.isoformat(),
            "Error": str(e),
        }


def scrape_what_they_do_without_quantum(driver, base_url):
    """Scrape the 'What They Do' data from the 'People' section."""
    role_url_without_quantum = f"{base_url}/people/"
    start_time = datetime.now()

    try:
        driver.get(role_url_without_quantum)
        time.sleep(6)
        current_url = driver.current_url
        if current_url != role_url_without_quantum:
            logging.info(f"Redirected to {current_url} ...")
            if "/unavailable/" in current_url:
                logging.warning("Company not available on LinkedIn.")
                about_data = {
                    "Company Name": "-",
                    "LinkedIn URL": base_url,
                    "Targeted URL": role_url_without_quantum,
                    "Redirected to URL": current_url,
                    "Time Stamp": start_time.isoformat(),
                }
                return about_data

        try:
            company_name = "-"
            soup = BeautifulSoup(driver.page_source, "html.parser")
            company_name_tag = soup.find("h1", class_="org-top-card-summary__title")
            company_name = (
                company_name_tag.get_text(strip=True) if company_name_tag else "-"
            )
        except Exception:
            logging.error(
                "Can't find the soup for the where they live with quantum ..."
            )
            data = {
                "Company Name": company_name,
                "Associated Members": "-",
                "Roles": "-",
                "Time Stamp": start_time.isoformat(),
                "Redirected to URL": current_url,
            }
            return data

        try:
            associated_members_count = associated_members(soup)
        except Exception as e:
            logging.error(
                f"Unexpected error in associated memebers count ..., error - {e}"
            )
            associated_members_count = "-"

        try:
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "org-people-bar-graph-element")
                )
            )
        except Exception:
            logging.warning(f"No member data found for {role_url_without_quantum} ---")
            data = {
                "Company Name": company_name,
                "Associated Members": associated_members_count,
                "Roles": "-",
                "Time Stamp": start_time.isoformat(),
                "Redirected to URL": current_url,
            }
            return data

        what_they_do_without_quantum_data = []
        what_they_do_li = soup.find("li", {"data-item-index": "2"})

        if what_they_do_li:
            buttons = what_they_do_li.find_all(
                "button", class_="org-people-bar-graph-element"
            )
            for button in buttons:
                count = (
                    button.find("strong").text.strip() if button.find("strong") else "-"
                )
                role = (
                    button.find(
                        "span", class_="org-people-bar-graph-element__category"
                    ).text.strip()
                    if button.find("span")
                    else "-"
                )
                what_they_do_without_quantum_data.append({"Count": count, "Role": role})

        what_they_do_without_quantum_data = {
            "Company Name": company_name,
            "Associated Members": associated_members_count,
            "Roles": what_they_do_without_quantum_data,
            "Time Stamp": start_time.isoformat(),
            "Redirected to URL": current_url,
        }

        return what_they_do_without_quantum_data

    except Exception as e:
        logging.error(f"Error scraping What They Do without Quantum data: {str(e)}")
        return {
            "Company Name": "-",
            "Associated Members": "-",
            "Roles": "-",
            "Time Stamp": start_time.isoformat(),
            "Error": str(e),
        }


def save_to_json(data, filename):
    """Save data to a JSON file inside the output directory."""
    target_path = OUTPUT_DIR / filename
    logging.info(f"Saving data to {target_path}")
    if target_path.is_file():
        with target_path.open("r", encoding="utf-8") as file:
            existing_data = json.load(file)
        existing_data.append(data)
    else:
        existing_data = [data]

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(existing_data, file, indent=4)


def validate_linkedin_url(url):
    """
    Validate and clean a LinkedIn company URL.

    Args:
        url (str): The LinkedIn URL to validate and clean.

    Returns:
        str: The cleaned and valid LinkedIn company URL, or None if invalid.
    """
    # Ensure the URL starts with https://
    if url.startswith("http://"):
        url = "https://" + url[len("http://") :]
    elif url.startswith("www."):
        url = "https://" + url
    elif not url.startswith("https://"):
        return None  # Invalid URL

    # Remove everything after the 5th '/'
    parts = url.split("/")
    if len(parts) > 5:
        url = "/".join(parts[:5])

    return url


def main(input_csv, username, password):
    """
    Main function to read LinkedIn URLs from the input CSV,
    log in to LinkedIn, scrape data, and save the results.
    """
    try:
        logging.info("---<<< STARTED SCRAPING >>>---")
        logging.info("Reading input CSV file...")
        # Read LinkedIn URLs from input CSV
        input_df = pd.read_csv(input_csv, encoding="ISO-8859-1")

        logging.info("Initializing Selenium WebDriver...")
        # Initialize the Selenium WebDriver
        driver = init_driver()

        if driver is None:
            logging.error("Failed to initialize the WebDriver. Exiting.")
            return

        # Log in to LinkedIn
        if not login_to_linkedin(driver, username, password):
            logging.error("Failed to log in to LinkedIn. Exiting.")
            return

        # Iterate through each row and extract Name and LinkedIn URL
        for index, row in input_df.iterrows():
            company_name = row.get(
                "Name", ""
            )  # Replace "Name" with the actual column name in your CSV
            linkedin_url = row.get(
                "LinkedIn", ""
            )  # Replace with the actual column name
            logging.info(
                f"{index + 1}/{len(input_df)} - Getting Data for Company: {company_name} Data ---"
            )
            try:
                if (
                    linkedin_url == ""
                    or linkedin_url is None
                    or linkedin_url.isspace()
                    or linkedin_url == "-"
                ):
                    logging.info(
                        f"LinkedIn URL is empty for {company_name}. Skipping..."
                    )

                    data = {
                        "Company Name": company_name,
                        "LinkedIn URL": linkedin_url,
                        "Time Stamp": datetime.now().isoformat(),
                    }
                    save_to_json(data, "about_data.json")
                    save_to_json(data, "where_they_live_with_quantum_data.json")
                    save_to_json(data, "where_they_live_without_quantum_data.json")
                    save_to_json(data, "what_they_do_with_quantum_data.json")
                    save_to_json(data, "what_they_do_without_quantum_data.json")
                    continue

                # Validate and clean the LinkedIn URL
                logging.info(f"Validating LinkedIn URL: {linkedin_url}...")
                v_linkedin_url = validate_linkedin_url(linkedin_url)

                if v_linkedin_url is None:
                    logging.error(f"Invalid LinkedIn URL: {linkedin_url}")
                    data = {
                        "Company Name": company_name,
                        "LinkedIn URL": linkedin_url,
                        "Time Stamp": datetime.now().isoformat(),
                    }
                    save_to_json(data, "about_data.json")
                    save_to_json(data, "where_they_live_with_quantum_data.json")
                    save_to_json(data, "where_they_live_without_quantum_data.json")
                    save_to_json(data, "what_they_do_with_quantum_data.json")
                    save_to_json(data, "what_they_do_without_quantum_data.json")
                    continue

                # Scrape 'About' section
                logging.info(f"Scraping about data for {v_linkedin_url}...")
                about_data = scrape_about_section(driver, v_linkedin_url)
                about_data["input_company_name"] = company_name
                save_to_json(about_data, "about_data.json")

                # # Scrape 'Where They Live'(Quantum)
                logging.info(
                    f"Scraping where_they_live_with_quantum data for {v_linkedin_url}..."
                )
                where_they_live_with_quantum_data = scrape_where_they_live_with_quantum(
                    driver, v_linkedin_url
                )
                where_they_live_with_quantum_data["input_company_name"] = company_name
                save_to_json(
                    where_they_live_with_quantum_data,
                    "where_they_live_with_quantum_data.json",
                )

                # # Scrape 'Where They Live'(Without Quantum)
                logging.info(
                    f"Scraping where_they_live_without_quantum data for {v_linkedin_url}..."
                )
                where_they_live_without_quantum_data = (
                    scrape_where_they_live_without_quantum(driver, v_linkedin_url)
                )
                where_they_live_without_quantum_data["input_company_name"] = (
                    company_name
                )
                save_to_json(
                    where_they_live_without_quantum_data,
                    "where_they_live_without_quantum_data.json",
                )

                # # Scrape 'What They Do'(Quantum)
                logging.info(
                    f"Scraping what_they_do_with_quantum data for {v_linkedin_url}..."
                )
                what_they_do_with_quantum_data = scrape_what_they_do_with_quantum(
                    driver, v_linkedin_url
                )
                what_they_do_with_quantum_data["input_company_name"] = company_name
                save_to_json(
                    what_they_do_with_quantum_data,
                    "what_they_do_data_with_quantum.json",
                )

                # # Scrape 'What They Do'(Without Quantum)
                logging.info(
                    f"Scraping what_they_do_without_quantum data for {v_linkedin_url}..."
                )
                what_they_do_without_quantum_data = scrape_what_they_do_without_quantum(
                    driver, v_linkedin_url
                )
                what_they_do_without_quantum_data["input_company_name"] = company_name
                save_to_json(
                    what_they_do_without_quantum_data,
                    "what_they_do_data_without_quantum.json",
                )

                logging.info(
                    f"{index + 1}/{len(input_df)} - Data scraped and saved for {v_linkedin_url} ..."
                )

            except Exception as scrape_error:
                logging.error(f"Error processing {linkedin_url}: {scrape_error}")
                continue

    except FileNotFoundError:
        logging.error(
            f"Error: The file {input_csv} does not exist. Please provide a valid CSV file."
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


def setup_logging():
    # Create a unique log file based on the current timestamp
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)  # Ensure the logs directory exists
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    # Configure the logging
    logging.basicConfig(
        level=logging.INFO,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
        handlers=[
            logging.FileHandler(log_file),  # Save logs to the unique file
            logging.StreamHandler(),  # SShow logs to the console
        ],
    )


# Main script
if __name__ == "__main__":
    setup_logging()
    input_csv_file = "QED-C_Linkedin_URLS_Jan_2024.csv"
    linkedin_username = "tivet80750@bablace.com"
    linkedin_password = "Callit00F"

    main(input_csv_file, linkedin_username, linkedin_password)
