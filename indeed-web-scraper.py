import csv
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementNotInteractableException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time


def get_url(position, location):
    """Generate url from position and location"""
    template = 'https://www.indeed.com/jobs?q={}&l={}'
    position = position.replace(' ', '+')
    location = location.replace(' ', '+')
    url = template.format(position, location)
    return url


def set_filters(driver):
    """Set filters for Education and Experience Level on the search results page."""

    def attempt_click(element, desc, xpath_check):
        """Try to click an element multiple times, with a check for success."""
        for _ in range(5):  # try 5 times
            try:
                element.click()
                time.sleep(2)  # wait for 2 seconds

                # Check if the dropdown is visible now, if yes, break
                if driver.find_element(By.XPATH, xpath_check).is_displayed():
                    break
            except Exception as e:
                print(f"Attempt to click {desc} failed: {e}")

    try:
        # EDUCATION FILTER
        education_filter = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "filter-edulvl"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", education_filter)
        attempt_click(education_filter, "Education Filter", "//a[contains(text(),\"Bachelor's Degree\")]")

        bachelors_degree_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),\"Bachelor's Degree\")]"))
        )
        bachelors_degree_option.click()

        # EXPERIENCE FILTER
        experience_filter = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, "filter-explvl"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", experience_filter)
        attempt_click(experience_filter, "Experience Filter", "//a[contains(text(),\"Entry Level\")]")

        entry_level_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),\"Entry Level\")]"))
        )
        entry_level_option.click()

    except (NoSuchElementException, TimeoutException):
        print("Error setting filters. Proceeding without them...")


def scrape_jobs(driver):
    job_elements = driver.find_elements(By.XPATH, "//td[@class='resultContent']")

    all_data = []

    for job_element in job_elements:
        # Extracting job title
        try:
            title_element = job_element.find_element(By.XPATH, ".//span[@title]")
            title = title_element.get_attribute("title")
            if not title:  # Fallback in case the title attribute is empty or not present
                title = title_element.text
        except NoSuchElementException:
            title = None

        # Extracting company name
        try:
            company = job_element.find_element(By.XPATH, ".//span[@class='companyName']").text
        except NoSuchElementException:
            company = None

        # Extracting salary
        # First, we'll try to get the estimated salary. If it's not available, we'll check for posted salary.
        try:
            salary = job_element.find_element(By.XPATH, ".//span[contains(text(),'Estimated')]").text
        except NoSuchElementException:
            try:
                salary = job_element.find_element(By.XPATH, ".//span[@class='salary-snippet']").text
            except NoSuchElementException:
                salary = None

        # Extracting attributes
        attributes = []
        try:
            attribute_elements = job_element.find_elements(By.XPATH,
                                                           ".//div[@class='metadata']/div[@class='attribute_snippet']")
            for attribute_element in attribute_elements:
                attributes.append(attribute_element.text)
        except NoSuchElementException:
            attributes = []

        all_data.append((title, company, salary, attributes))

    return all_data


def main(positions, locations, max_pages=9):
    all_job_titles = []
    all_company_names = []
    all_salaries = []
    all_attributes = []
    all_searched_positions = []
    all_searched_locations = []
    all_job_links = []

    for position in positions:
        for location in locations:
            print(f"Scraping for position: {position} in location: {location}")

            url = get_url(position, location)

            options = ChromeOptions()
            options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.124 Safari/537.36')
            options.add_argument('--headless')  # Enable headless mode

            driver = Chrome(options=options)
            driver.get(url)
            set_filters(driver)

            page_counter = 1  # Starting from the first page

            # Loop through pages
            while True:
                try:
                    print(f"Processing page {page_counter}")

                    # Wait for the job titles to load
                    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.jobTitle')))

                    # Scrape job titles from the current page
                    job_data = scrape_jobs(driver)
                    for data in job_data:
                        all_job_titles.append(data[0])
                        all_company_names.append(data[1])
                        all_salaries.append(data[2])
                        all_attributes.append(data[3])
                        for _ in range(len(job_data)):
                            all_searched_positions.append(position)
                            all_searched_locations.append(location)
                            # Scrape job links
                            job_links = driver.find_elements(By.CSS_SELECTOR, '.jobTitle a')
                            job_links = [link.get_attribute('href') for link in job_links]
                            all_job_links.extend(job_links)

                    if page_counter == max_pages:
                        print("Processed all pages. Exiting loop.")
                        break

                    # Wait for the "Next" button to be clickable
                    wait = WebDriverWait(driver, 10)
                    next_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-testid="pagination-page-next"]')))

                    # Scroll the "Next" button into view
                    driver.execute_script("arguments[0].scrollIntoView();", next_button)

                    next_button.click()

                    # Wait for the next page to load
                    WebDriverWait(driver, 30).until(EC.staleness_of(next_button))

                    page_counter += 1  # Increment the page counter

                except NoSuchElementException:
                    print("'Next' button not found. Exiting loop.")
                    break
                except ElementNotInteractableException:
                    print("'Next' button not clickable. Trying to close popup...")
                    # ... (rest of the code)
                except TimeoutException:
                    print("Timed out waiting for 'Next' button or next page. Exiting loop.")
                    break

            driver.quit()
            # Write job titles and company names to a .csv file
    print(f"Collected titles: {all_job_titles}")
    print(f"Collected companies: {all_company_names}")
    print(f"Collected salaries: {all_salaries}")
    print(f"Collected attributes: {all_attributes}")
    print("Writing to CSV now...")
    with open('jobs.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Searched Position', 'Searched Location', 'Job Title', 'Company Name', 'Salary', 'Attribute 1',
                         'Attribute 2', 'Attribute 3', 'Job Link'])
        for searched_position, searched_location, title, company, salary, attribute, link in zip(all_searched_positions,
                                                                                                 all_searched_locations,
                                                                                                 all_job_titles,
                                                                                                 all_company_names,
                                                                                                 all_salaries,
                                                                                                 all_attributes,
                                                                                                 all_job_links):
            while len(attribute) < 3:
                attribute.append(None)
            writer.writerow([searched_position, searched_location, title, company, salary] + attribute + [link])


if __name__ == '__main__':
    job_titles = ['data scientist']
    cities = ['Cincinnati, OH', 'Rochester, NY', 'Dallas, TX', 'Austin, TX', 'Minneapolis, MN', 'Green Bay, WI',
              'Boulder, CO', 'Charlotte, NC', 'Boise, ID', 'Albany, NY', 'Knoxville, TN', 'Syracuse, NY', 'Buffalo, NY',
              'Columbus, OH', 'Nashville, Tenessee', 'Birmingham, Alabama']
    main(job_titles, cities, max_pages=3)
