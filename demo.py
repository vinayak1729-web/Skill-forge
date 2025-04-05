from flask import Flask, jsonify, render_template, request
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

app = Flask(__name__)

# Configuration for each company: job search URL, selectors, and pagination details
companies = {
    "meta": {
        "url": "https://www.facebook.com/careers/jobs/",
        "job_list_selector": "a[href*='/careers/v2/jobs/']",
        "qualifications_selector": ".job-qualifications",
        "next_page_selector": "a.next"
    },
    "amazon": {
        "url": "https://www.amazon.jobs/en/",
        "job_list_selector": "a.job-title",
        "qualifications_selector": ".basic-qualifications",
        "next_page_selector": "a.next-page"
    },
    "apple": {
        "url": "https://jobs.apple.com/en-us/search",
        "job_list_selector": "a[href*='/en-us/details/']",
        "qualifications_selector": ".job-description",
        "next_page_selector": "a.next"
    },
    "netflix": {
        "url": "https://jobs.netflix.com/jobs",
        "job_list_selector": "a.job-link",
        "qualifications_selector": ".job-requirements",
        "next_page_selector": "a.pagination-next"
    },
    "google": {
        "url": "https://careers.google.com/jobs/results/",
        "job_list_selector": "a.gc-card",
        "qualifications_selector": ".qualifications",
        "next_page_selector": "a[aria-label='Next']"
    },
    "microsoft": {
        "url": "https://careers.microsoft.com/us/en/search-results",
        "job_list_selector": "a[href*='/job/']",
        "qualifications_selector": ".qualifications-section",
        "next_page_selector": "a.next"
    },
    "tesla": {
        "url": "https://www.tesla.com/careers/search",
        "job_list_selector": "a.job-item",
        "qualifications_selector": ".requirements",
        "next_page_selector": "a.next-page"
    },
    "ibm": {
        "url": "https://www.ibm.com/us-en/employment/",
        "job_list_selector": "a[href*='/job/']",
        "qualifications_selector": ".required-technical-skills",
        "next_page_selector": "a.next"
    },
    "oracle": {
        "url": "https://www.oracle.com/corporate/careers/",
        "job_list_selector": "a[href*='/jobs/']",
        "qualifications_selector": ".requirements",
        "next_page_selector": "a.next"
    },
    "salesforce": {
        "url": "https://boards.greenhouse.io/salesforce",
        "job_list_selector": "a[href*='/salesforce/jobs/']",
        "qualifications_selector": ".job-details",
        "next_page_selector": "a.next"
    }
}

# Headers to mimic a browser request
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def scrape_page(url, config, results, max_jobs=10):
    """
    Scrape a single page for job listings and extract skills.
    Args:
        url (str): URL of the page to scrape.
        config (dict): Company configuration with selectors.
        results (list): List to append job data to.
        max_jobs (int): Maximum number of jobs to scrape.
    Returns:
        str or None: URL of the next page, if available.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find job listing links
        job_links = soup.select(config["job_list_selector"])
        if not job_links:
            return None

        # Process each job link until max_jobs is reached
        base_url = config["url"]
        for job_link in job_links:
            if len(results) >= max_jobs:
                break

            job_title = job_link.get_text(strip=True) or "Unknown Title"
            href = job_link.get('href', '')
            job_url = urljoin(base_url, href)

            # Fetch the individual job page
            try:
                job_response = requests.get(job_url, headers=HEADERS, timeout=10)
                job_response.raise_for_status()
                job_soup = BeautifulSoup(job_response.text, 'html.parser')

                # Extract skills/requirements
                qualifications = job_soup.select_one(config["qualifications_selector"])
                skills_text = qualifications.get_text(strip=True) if qualifications else "Skills not found"

                if job_title == "Unknown Title":
                    title_element = job_soup.find('h1')
                    job_title = title_element.get_text(strip=True) if title_element else "Unknown Title"

                results.append({
                    "job_title": job_title,
                    "skills": skills_text,
                    "url": job_url
                })

            except requests.RequestException as e:
                results.append({
                    "job_title": job_title,
                    "skills": f"Error fetching job page: {str(e)}",
                    "url": job_url
                })

        # Check for next page
        next_page = soup.select_one(config["next_page_selector"])
        if next_page and len(results) < max_jobs:
            next_url = urljoin(base_url, next_page.get('href', ''))
            return next_url
        return None

    except requests.RequestException:
        return None

@app.route('/')
def index():
    """Render the main page with company selection form"""
    return render_template('index.html', companies=sorted(companies.keys()))

@app.route('/scrape', methods=['POST'])
def scrape_company():
    """
    Scrape job listings for a specified company with pagination.
    """
    company = request.form.get('company', '').lower()
    
    if not company or company not in companies:
        return render_template('index.html', 
                              companies=sorted(companies.keys()),
                              error="Please select a valid company")

    config = companies[company]
    results = []
    current_url = config["url"]
    max_jobs = 10  # Limit to 10 jobs total

    try:
        while current_url and len(results) < max_jobs:
            next_url = scrape_page(current_url, config, results, max_jobs)
            current_url = next_url

        if not results:
            return render_template('index.html', 
                                  companies=sorted(companies.keys()),
                                  error="No job listings found for this company")

        return render_template('results.html', 
                              company=company.capitalize(),
                              results=results)

    except Exception as e:
        return render_template('index.html', 
                              companies=sorted(companies.keys()),
                              error=f"Scraping failed: {str(e)}")

@app.route('/api/scrape/<company>')
def api_scrape_company(company):
    """API endpoint for scraping (for programmatic access)"""
    if company.lower() not in companies:
        return jsonify({"error": "Company not supported"}), 400

    config = companies[company.lower()]
    results = []
    current_url = config["url"]
    max_jobs = 10

    try:
        while current_url and len(results) < max_jobs:
            next_url = scrape_page(current_url, config, results, max_jobs)
            current_url = next_url

        if not results:
            return jsonify({"error": "No job listings found"}), 404

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True ,port =8080 )
