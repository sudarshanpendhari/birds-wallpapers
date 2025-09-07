import os
import requests
import json
from datetime import datetime
from pathlib import Path
from PIL import Image
from io import BytesIO
import time
import random
import base64

# Categories and search queries
categories = {
    "mobile": "mobile wallpaper bird",
    "tablet": "tablet wallpaper bird",
    "other_mobile": "phone wallpaper bird",
    "other_tablet": "tablet highres bird"
}

min_images = 10
index_file = Path("index.json")

# Load existing index.json
if index_file.exists():
    with open(index_file) as f:
        index_data = json.load(f)
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

def upload_to_imgbb(image_bytes, name):
    key = os.getenv("IMGBB_KEY")
    url = "https://api.imgbb.com/1/upload"
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "key": key,
        "image": b64,
        "name": name
    }
    resp = requests.post(url, data=payload)
    if resp.status_code == 200:
        return resp.json()["data"]["url"]
    else:
        print("ImgBB upload failed:", resp.text)
        return None

def download_and_upload(url, category):
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        raise Exception(f"Download failed: {url}")

    # unique filename
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    rand_suffix = random.randint(1000, 9999)
    filename = f"{category}-{timestamp}-{rand_suffix}.jpg"

    # upload to ImgBB
    uploaded_url = upload_to_imgbb(resp.content, filename)
    if not uploaded_url:
        raise Exception("Upload to ImgBB failed")

    return {
        "url": uploaded_url,
        "category": category,
        "date_added": datetime.now().isoformat()
    }

# Main loop
for cat, keyword in categories.items():
    urls = fetch_pexels_images(keyword)
    if len(urls) < min_images:
        urls += fetch_pixabay_images(keyword)

    urls = list(dict.fromkeys(urls))  # dedupe
    urls_to_process = urls[:max(min_images, len(urls))]

    index_data.setdefault(cat, [])

    for url in urls_to_process:
        try:
            meta = download_and_upload(url, cat)
            index_data[cat].append(meta)
            time.sleep(1)  # rate limit
        except Exception as e:
            print(f"Error processing {url}: {e}")

# Save updated index.json
with open(index_file, "w") as f:
    json.dump(index_data, f, indent=2)
