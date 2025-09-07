import os
import requests
import json
from datetime import datetime
from pathlib import Path
from PIL import Image
from io import BytesIO
import time
import random

# Categories and their search keywords
categories = {
    "mobile": "mobile wallpaper bird",
    "tablet": "tablet wallpaper bird",
    "other_mobile": "phone wallpaper bird",
    "other_tablet": "tablet highres bird"
}

min_images = 10  # minimum images per category

images_dir = Path("images")
images_dir.mkdir(exist_ok=True)

# Load existing index.json
index_file = Path("index.json")
if index_file.exists():
    with open(index_file) as f:
        try:
            index_data = json.load(f)
            if not isinstance(index_data, dict):
                print("index.json is not a dict, resetting it.")
                index_data = {}
        except json.JSONDecodeError:
            print("index.json is invalid, resetting it.")
            index_data = {}
else:
    index_data = {}

def fetch_pexels_images(query, per_page=20):
    headers = {"Authorization": os.getenv("PEXELS_KEY")}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page={per_page}"
    resp = requests.get(url).json()
    return [photo["src"]["original"] for photo in resp.get("photos", [])]

def fetch_pixabay_images(query, per_page=20):
    key = os.getenv("PIXABAY_KEY")
    url = f"https://pixabay.com/api/?key={key}&q={query}&per_page={per_page}&image_type=photo"
    resp = requests.get(url).json()
    return [hit["largeImageURL"] for hit in resp.get("hits", [])]

def download_image(url, path):
    resp = requests.get(url, timeout=10)
    img = Image.open(BytesIO(resp.content))
    img.save(path)

for cat, keyword in categories.items():
    cat_dir = images_dir / cat
    cat_dir.mkdir(exist_ok=True)
    
    # Fetch images from both APIs
    urls = fetch_pexels_images(keyword)
    if len(urls) < min_images:
        urls += fetch_pixabay_images(keyword)
    
    # Remove duplicates
    urls = list(dict.fromkeys(urls))
    
    # Ensure at least min_images (if not, will download as many as available)
    urls_to_download = urls[:max(min_images, len(urls))]
    
    index_data.setdefault(cat, [])
    
    for url in urls_to_download:
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        rand_suffix = random.randint(1000,9999)
        filename = f"{cat}-{timestamp}-{rand_suffix}.jpg"
        file_path = cat_dir / filename
        try:
            download_image(url, file_path)
            index_data[cat].append({
                "file": str(file_path),
                "url": url,
                "category": cat,
                "downloaded_at": datetime.now().isoformat()
            })
            time.sleep(0.5)  # avoid hitting API rate limits
        except Exception as e:
            print(f"Failed to download {url}: {e}")

# Save updated index.json
with open(index_file, "w") as f:
    json.dump(index_data, f, indent=2)
