import os
import requests
from bs4 import BeautifulSoup
import urllib.request
import PyPDF2

# Create folder to store images
folder_name = 'AyurHerbs'
if not os.path.exists(folder_name):
    os.makedirs(folder_name)

# Function to read PDF and extract plant names
def extract_plant_names_from_pdf(pdf_path):
    plant_names = []
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in range(len(reader.pages)):
            page_text = reader.pages[page].extract_text()
            # Assuming plant names are listed in each row, split text into lines
            lines = page_text.split("\n")
            for line in lines:
                # You might need to adjust the extraction logic based on the PDF structure
                plant_names.append(line.strip())
    
    # Remove any duplicates or empty names
    plant_names = list(set(filter(None, plant_names)))
    return plant_names

# Function to search for and scrape one image per plant name
def fetch_image_url(plant_name):
    search_query = f"{plant_name} medicinal plant image"
    search_url = f"https://www.google.com/search?tbm=isch&q={search_query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the first valid image URL
    for img_tag in soup.find_all('img'):
        img_url = img_tag.get('src')
        if img_url and 'http' in img_url:
            return img_url
    return None

# Function to download and save the image
def download_image(image_url, plant_name):
    try:
        image_name = f"{plant_name.replace(' ', '_')}.jpg"
        file_path = os.path.join(folder_name, image_name)
        urllib.request.urlretrieve(image_url, file_path)
        print(f"Downloaded: {image_name}")
    except Exception as e:
        print(f"Error downloading {plant_name}: {e}")

# Main function to process the PDF and scrape images
def scrape_images_from_pdf(pdf_path):
    plant_names = extract_plant_names_from_pdf(pdf_path)
    
    for plant_name in plant_names:
        print(f"Scraping image for: {plant_name}")
        image_url = fetch_image_url(plant_name)
        
        if image_url:
            download_image(image_url, plant_name)
        else:
            print(f"No image found for {plant_name}")

# Example usage
pdf_path = r"C:\Users\Shanmugam\OneDrive\Desktop\Chittu Kuruvi\dataset\Dictionary_of_Medicinal_Plants.pdf"
scrape_images_from_pdf(pdf_path)
