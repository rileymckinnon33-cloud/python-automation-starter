import os
import json
import requests
import datetime
from utils.logger import get_logger

# ---------- Load config ----------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
DEFAULTS = {
    "nasa_api_key": "DEMO_KEY",     # Replace with your own key from https://api.nasa.gov/
    "save_dir": "output",           # Where to save files
    "download_hd": False            # Try HD image when available
}

def load_config():
    cfg = DEFAULTS.copy()
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        cfg.update(user_cfg or {})
    return cfg

# ---------- APOD fetch ----------
def fetch_apod(api_key: str, date: str = None):
    """Fetch NASA APOD metadata (and image URL if present)."""
    url = "https://api.nasa.gov/planetary/apod"
    params = {"api_key": api_key}
    if date:
        params["date"] = date  # YYYY-MM-DD
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()

def download_file(url: str, dest_path: str):
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

def main():
    logger = get_logger()
    cfg = load_config()
    save_dir = os.path.join(os.path.dirname(__file__), cfg["save_dir"])
    os.makedirs(save_dir, exist_ok=True)

    # Use today's date
    today = datetime.date.today().isoformat()
    try:
        data = fetch_apod(cfg["nasa_api_key"], date=today)
    except Exception as e:
        logger.exception("Failed to fetch APOD: %s", e)
        return

    # Save metadata JSON
    meta_name = f"apod_{today}.json"
    meta_path = os.path.join(save_dir, meta_name)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Saved metadata: %s", meta_path)

    # If it's an image, download it
    media_type = data.get("media_type")
    img_url = None
    if media_type == "image":
        if cfg.get("download_hd") and data.get("hdurl"):
            img_url = data["hdurl"]
        else:
            img_url = data.get("url")

    if img_url:
        # Guess filename extension
        ext = os.path.splitext(img_url.split("?")[0])[1] or ".jpg"
        img_name = f"apod_{today}{ext}"
        img_path = os.path.join(save_dir, img_name)
        try:
            download_file(img_url, img_path)
            logger.info("Saved image: %s", img_path)
        except Exception as e:
            logger.exception("Failed to download image: %s", e)
    else:
        logger.info("No downloadable image for today (media_type=%s).", media_type)

if __name__ == "__main__":
    main()
