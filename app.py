from bs4 import BeautifulSoup
from flask import Flask, render_template, request, Response, redirect,jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time
from flask_cors import CORS
from selenium.webdriver.common.action_chains import ActionChains
import os
from urllib.parse import urljoin,urlparse
import PyPDF2
import json
import requests
from flask import Response, request
app = Flask(__name__)
cors = CORS(app)

# geckodriver_path = r'C:/flask_app/scrub/geckodriver.exe'  # Replace with the actual path to geckodriver
geckodriver_path = r'/home/ubuntu/crawling/crawling/geckodriver.exe'
firefox_binary_path = r'/usr/bin/firefox'  # Replace with the actual path to Firefox binary
@app.route('/', methods=['GET', 'POST'])
def scrape_website():
    if request.method == 'POST':
        # Get the list of words from the form
        target_words = request.form.getlist('word')

        # Define the URL of the website you want to scrape
        url = request.form.get('url')  # Replace with the desired website URL
        print("=-=-=-=-url=-=-=-",url)
        discovered_urls = get_all_pages(url)
        word_found_urls = set()  # Set to store the URLs where the words are found
        options = Options()
        options.headless = True  # Run Firefox in headless mode
        options.binary = firefox_binary_path  # Set the Firefox binary path

        sentence_locations = []
        for i in discovered_urls:
            # Call the function to check if the words are present on the page
            if check_words_on_page(i, target_words):
                word_found_urls.add(i)
            driver = webdriver.Firefox(options=options, executable_path=geckodriver_path)
            driver.get(i)
            print("=-=--loop=-=-=", i)
            for word in target_words:

                sentence_elements = find_sentence_elements(driver, word)
                for sentence_element in sentence_elements:
                    position = get_element_position(sentence_element)
                    if position['top'] != -1 and position['left'] != -1:
                        location_info = {
                            'word': word,
                            'url': i,
                            'positions': [position]  # Update to include 'positions' key
                        }
                        sentence_locations.append(location_info)
                        print("=-=-=sentence_locations=-=-=-",sentence_locations)    
            driver.quit()

        # Pass the word_found_urls and sentence_locations to the template
        return render_template('coordinates.html', word_found_urls=list(word_found_urls),
                               sentence_locations=sentence_locations)

    return render_template('index.html')




def check_words_on_page(url, target_words):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        for word in target_words:
            if soup.body and word.lower() in soup.body.get_text().lower():
                return True
    return False


def get_all_pages(url):
    visited_urls = set()
    urls_to_visit = [url]
    discovered_urls = set()

    while urls_to_visit:
        current_url = urls_to_visit.pop(0)

        if current_url in visited_urls:
            continue

        try:
            # Add scheme if missing
            if not current_url.startswith('http'):
                current_url = f'http://{current_url}'

            response = requests.get(current_url)
            visited_urls.add(current_url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Find and extract all links
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if not href.startswith(('http://', 'https://')):
                        # Relative URL, append it to the base URL
                        internal_url = urljoin(current_url, href)
                        internal_url = internal_url.split('#')[0]  # Remove '#' and everything after it

                        parsed_url = urlparse(internal_url)
                        if (
                            parsed_url.scheme != 'mailto' and
                            not any(
                                x in parsed_url.path.lower()
                                for x in ['index.html', 'index.php', 'index.htm', 'index.asp']
                            )
                        ):
                            links.append(internal_url)

                # Add new links to the list to visit
                urls_to_visit.extend(links)

                # Store discovered URLs
                discovered_urls.add(current_url)

        except Exception as e:
            print(f"An error occurred while crawling {current_url}: {e}")

    return discovered_urls


async def get_sentence_locations(urls, target_words):
    options = Options()
    options.headless = True  # Run Firefox in headless mode
    options.binary = firefox_binary_path  # Set the Firefox binary path

    sentence_locations = []

    for url in urls:
        driver = webdriver.Firefox(options=options, executable_path=geckodriver_path)
        driver.get(url)
        print("=-=--loop=-=-=",url)
        for word in target_words:
           
            sentence_elements = find_sentence_elements(driver, word)
            for sentence_element in sentence_elements:
                position = get_element_position(sentence_element)
                if position['top'] != -1 and position['left'] != -1:
                    location_info = {
                        'word': word,
                        'url': url,
                        'positions': [position]  # Update to include 'positions' key
                    }
                    sentence_locations.append(location_info)

        driver.quit()

    # Pass the word_found_urls and sentence_locations to the template
    return render_template('coordinates.html', word_found_urls=list(urls), sentence_locations=sentence_locations)




def find_sentence_elements(driver, target_word):
    xpath_expression = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{target_word.lower()}')]"
    sentence_elements = driver.find_elements(By.XPATH, xpath_expression)
    return sentence_elements


def get_element_position(element):
    location = element.location
    position = {
        'top': location['y'],
        'left': location['x']
    }
    return position


@app.route('/scroll_to_position', methods=['GET'])
def scroll_to_position():
    try:
        url = 'http://www.chillarcards.com/'
        target_element_id = 'fintech-service'
        print(f'Target element ID: {target_element_id}')

        options = Options()
        options.headless = True  # Run Firefox in headless mode
        options.binary = firefox_binary_path  # Set the Firefox binary path
        driver = webdriver.Firefox(options=options, executable_path=geckodriver_path)

        # Make the request directly without a proxy
        driver.get(url)

        # Find the target element by ID
        target_element = driver.find_element('id', target_element_id)

        # Scroll to the position of the target element using JavaScript
        scroll_script = f"window.scrollTo({{ top: {target_element.location['y']}, left: {target_element.location['x']} }})"
        driver.execute_script(scroll_script)

        # Delay to allow time for scrolling
        time.sleep(1)

        # Quit the driver
        driver.quit()

        # Redirect to the specified URL
        return redirect(url)

    except Exception as e:
        print(e)
        return f"An error occurred: {e}"



@app.route('/proxy', methods=['GET'])
def proxy_request():
    try:
        url = request.args.get('url')
        response = requests.get(url, stream=True)
        headers = {'Content-Type': 'text/html'}  # Set Content-Type to text/html
        data = response.content

        # Extract base URL from the original request
        base_domain = url.split('?')[0]  # Get the base URL without query parameters

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(data, 'html.parser')

        # Rewrite script src attributes
        script_tags = soup.find_all('script')
        for script_tag in script_tags:
            src = script_tag.get('src')
            if src and not src.startswith('http'):
                script_tag['src'] = urljoin(base_domain, src)

        # Rewrite link href attributes
        link_tags = soup.find_all('link')
        for link_tag in link_tags:
            href = link_tag.get('href')
            if href and not href.startswith('http'):
                link_tag['href'] = urljoin(base_domain, href)

        # Rewrite img src attributes
        img_tags = soup.find_all('img')
        for img_tag in img_tags:
            src = img_tag.get('src')
            if src and not src.startswith('http'):
                img_tag['src'] = urljoin(base_domain, src)

        # Get the modified HTML content
        modified_html = str(soup)

        return Response(modified_html, headers=headers)

    except Exception as e:
        # Handle any exceptions that occur during the proxy request
        return str(e)


@app.route('/pdf', methods=['GET'])
def pdf():
    
    return render_template('pdf.html')


@app.route('/pdf_extract', methods=['POST'])
def pdf_extract():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        password = request.form.get('password')

        print(f'=-=-pass : {password}')
        
        # Check if a file is selected
        if uploaded_file.filename != '':
            # Read the uploaded file and extract text
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            if pdf_reader.is_encrypted:
                pdf_reader.decrypt(password)

            headings = []
            current_heading = None
            current_content = ""
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                lines = page_text.split("\n")

                for line in lines:
                    if line.strip():
                        if line.isupper() and not line.isdigit():
                            # New heading encountered
                            if current_heading and current_content:
                                # Add previous heading and content to the list
                                headings.append({
                                    'heading': current_heading,
                                    'content': current_content.strip()
                                })
                                current_content = ""
                            current_heading = line.strip()
                        else:
                            # Append content under current heading
                            current_content += line.strip() + " "

            # Add the last heading and content to the list
            if current_heading and current_content:
                headings.append({
                    'heading': current_heading,
                    'content': current_content.strip()
                })

            # Convert the list to JSON format
            json_data = json.dumps(headings)

            # Render the template with the extracted text
            return render_template('result.html', extracted_text=json_data)

    return render_template('pdf.html')


if __name__ == '__main__':
    os.environ['PATH'] += os.pathsep + os.path.dirname(geckodriver_path)
    app.run(host='0.0.0.0')