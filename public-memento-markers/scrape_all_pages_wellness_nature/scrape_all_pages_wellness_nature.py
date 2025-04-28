import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from datetime import datetime
from langdetect import detect
from pathlib import Path
import logging
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Union
import hashlib

# -----------------------------
# CONFIGURATION
# -----------------------------
BASE_SECTION_URL = "https://secretnyc.co/wellness-nature/page/{}/"
SCRIPT_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "mementos_wellness_nature_all_pages.json")

CATEGORIES_PATH = os.path.abspath(os.path.join(ROOT_DIR, "memento_categories_combined.json"))
TAGS_PATH = os.path.abspath(os.path.join(ROOT_DIR, "memento_tags_combined.json"))
DEFAULT_USER = "Secret NYC"
TOTAL_KNOWN_PAGES = 63  # Total pages from the Wellness & Nature section
MAX_RETRIES_PER_PAGE = 3  # Number of retries for failed pages

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

# -----------------------------
# LOAD CATEGORIES & TAGS
# -----------------------------
with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
    CATEGORIES = json.load(f)

with open(TAGS_PATH, "r", encoding="utf-8") as f:
    TAGS = json.load(f)

CATEGORY_LOOKUP = {cat["symbol"]: cat for cat in CATEGORIES}
TAG_LOOKUP = {tag["symbol"]: tag for tag in TAGS}

# -----------------------------
# HELPERS
# -----------------------------
def create_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    return session

def get_article_links(page_url: str) -> List[str]:
    session = create_session()
    try:
        response = session.get(page_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        
        # Find articles in the Top News section
        articles = soup.find_all("article")
        for article in articles:
            link = article.find("a", href=True)
            if link and link["href"].startswith("https://secretnyc.co/"):
                links.append(link["href"])
        
        return list(set(links))
    except Exception as e:
        logging.error(f"Error fetching article links: {e}")
        return []

def get_total_pages() -> int:
    """Get total number of pages, with fallback to known total."""
    session = create_session()
    try:
        response = session.get(BASE_SECTION_URL.format(1), timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find the pagination section
        pagination = soup.find("div", class_="pagination")
        if pagination:
            # Find all page numbers
            page_numbers = []
            for a in pagination.find_all("a", href=True):
                try:
                    page_num = int(a.text.strip())
                    page_numbers.append(page_num)
                except ValueError:
                    continue
            
            if page_numbers:
                detected_pages = max(page_numbers)
                logging.info(f"Detected {detected_pages} pages")
                return detected_pages
        
        # If no pagination found or error, return known total
        logging.warning("Could not detect pages, using known total of 63")
        return TOTAL_KNOWN_PAGES
    except Exception as e:
        logging.error(f"Error getting total pages: {e}")
        logging.warning("Using known total of 63 pages")
        return TOTAL_KNOWN_PAGES

def scrape_page(page_num: int) -> List[Dict]:
    page_url = BASE_SECTION_URL.format(page_num)
    logging.info(f"🔗 Scraping page {page_num}/{get_total_pages()}...")
    
    article_links = get_article_links(page_url)
    logging.info(f"✅ Found {len(article_links)} articles on page {page_num}")
    
    mementos = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_url = {executor.submit(process_article, url): url for url in article_links}
        for i, future in enumerate(future_to_url):
            url = future_to_url[future]
            try:
                memento = future.result()
                if memento:
                    mementos.append(memento)
                logging.info(f"📄 [{i+1}/{len(article_links)}] {url}")
            except Exception as e:
                logging.error(f"❌ Error processing {url}: {e}")
    
    return mementos

def save_mementos(mementos: List[Dict], output_path: str):
    """Save mementos to file with smart backup handling."""
    try:
        # Only create backup if the file exists and has different content
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    # Only create backup if content is different
                    if existing_data != mementos:
                        backup_path = output_path.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                        os.rename(output_path, backup_path)
                        logging.info(f"Created backup at {backup_path}")
            except Exception as e:
                logging.error(f"Error reading existing file: {e}")
        
        # Save new mementos
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(mementos, f, indent=4, ensure_ascii=False)
        logging.info(f"Saved {len(mementos)} mementos to {output_path}")
        
        # Clean up old backups (keep only last 3)
        if os.path.exists(output_path):
            backup_dir = os.path.dirname(output_path)
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith(os.path.basename(output_path).replace('.json', '_backup_'))]
            backup_files.sort(reverse=True)  # Sort by newest first
            for old_backup in backup_files[3:]:  # Keep only last 3 backups
                try:
                    os.remove(os.path.join(backup_dir, old_backup))
                    logging.info(f"Removed old backup: {old_backup}")
                except Exception as e:
                    logging.error(f"Error removing old backup {old_backup}: {e}")
                    
    except Exception as e:
        logging.error(f"Error saving mementos: {e}")

def parse_date(date_str: str) -> str:
    try:
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%B %d, %Y",
            "%A, %B %d, %Y",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                # Format as "March 5, 2024 at 12:05 PM"
                return dt.strftime("%B %d, %Y at %I:%M %p")
            except ValueError:
                continue
        match = re.search(r'(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)?,?\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}', date_str)
        if match:
            try:
                dt = datetime.strptime(match.group(0), "%A, %B %d, %Y")
                return dt.strftime("%B %d, %Y at %I:%M %p")
            except ValueError:
                pass
        return datetime.now().strftime("%B %d, %Y at %I:%M %p")
    except:
        return datetime.now().strftime("%B %d, %Y at %I:%M %p")

def clean_description(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"A post shared by.*?(\n|$)", "", text)
    text = re.sub(r"This year.*?website reads:", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"([.!?])\s*", r"\1 ", text).strip()
    return " ".join(re.split(r'(?<=[.!?])\s+', text)[:5])

def geocode_location(query: str) -> Optional[Dict[str, float]]:
    if not query:
        return None
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": query + ", New York City", "format": "json", "limit": 1}
        headers = {"User-Agent": "MEMENTO-map-collector/1.0"}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return {"latitude": float(data[0]["lat"]), "longitude": float(data[0]["lon"])}
    except Exception as e:
        logging.error(f"Error geocoding location {query}: {e}")
    return None

def extract_fallback_location(description: str, title: str) -> Optional[str]:
    combined_text = title + " " + description
    patterns = [
        r"(?:at|in|near|on)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(Avenue|Street|Boulevard|Park|Square|Bridge)"
    ]
    for pattern in patterns:
        match = re.search(pattern, combined_text)
        if match:
            return match.group(1).strip()
    return None

def match_keywords(text: str, items: List[Dict], context: Dict = None) -> List[str]:
    matched = []
    text = text.lower()
    
    # Create a scoring system for better matching
    scores = {}
    
    for item in items:
        score = 0
        # Check for exact matches first
        for kw in item["keywords"]:
            kw = kw.lower()
            if kw in text:
                # Give higher score for exact matches
                score += 2
                # Give bonus for matches in title
                if context and context.get('title') and kw in context['title'].lower():
                    score += 1
                # Give bonus for matches in location
                if context and context.get('location_name') and kw in context['location_name'].lower():
                    score += 1
                # Give bonus for matches in media description
                if context and context.get('media_desc') and kw in context['media_desc'].lower():
                    score += 1
        
        # Check for related words and context based on category/tag ID
        if item["id"] == "architecture" and any(word in text for word in ["building", "structure", "design", "facade", "landmark"]):
            score += 1
        elif item["id"] == "urban-nature" and any(word in text for word in ["park", "garden", "tree", "plant", "green"]):
            score += 1
        elif item["id"] == "cultural" and any(word in text for word in ["art", "museum", "exhibit", "culture", "heritage"]):
            score += 1
        elif item["id"] == "social" and any(word in text for word in ["people", "crowd", "group", "community", "gathering"]):
            score += 1
        elif item["id"] == "street-food" and any(word in text for word in ["food", "eat", "drink", "restaurant", "cafe"]):
            score += 1
        elif item["id"] == "public-event" and any(word in text for word in ["event", "festival", "celebration", "parade", "party"]):
            score += 1
        elif item["id"] == "popup-culture" and any(word in text for word in ["pop-up", "popup", "temporary", "limited time"]):
            score += 1
        elif item["id"] == "playful" and any(word in text for word in ["play", "game", "fun", "interactive", "participate"]):
            score += 1
        elif item["id"] == "learning" and any(word in text for word in ["learn", "education", "workshop", "class", "study"]):
            score += 1
        elif item["id"] == "tranquil" and any(word in text for word in ["peaceful", "quiet", "calm", "serene", "tranquil"]):
            score += 1
        elif item["id"] == "experimental" and any(word in text for word in ["experiment", "innovative", "new", "unique", "different"]):
            score += 1
        elif item["id"] == "ephemeral" and any(word in text for word in ["temporary", "short-lived", "momentary", "fleeting"]):
            score += 1
        elif item["id"] == "unmapped" and any(word in text for word in ["unknown", "hidden", "undiscovered", "secret"]):
            score += 1
        elif item["id"] == "niche" and any(word in text for word in ["underground", "cult", "niche", "specialized"]):
            score += 1
        elif item["id"] == "emotional" and any(word in text for word in ["emotional", "sentimental", "feeling", "touching"]):
            score += 1
        elif item["id"] == "hidden" and any(word in text for word in ["hidden", "secret", "underground", "unexpected"]):
            score += 1
        elif item["id"] == "unexpected" and any(word in text for word in ["unexpected", "surprise", "random", "serendipity"]):
            score += 1
        elif item["id"] == "reflective" and any(word in text for word in ["reflective", "poetic", "philosophical", "thoughtful"]):
            score += 1
        elif item["id"] == "unpleasant" and any(word in text for word in ["unpleasant", "truth", "harsh", "sad"]):
            score += 1
        elif item["id"] == "rare" and any(word in text for word in ["rare", "once-in-a-while", "infrequent", "special"]):
            score += 1
        elif item["id"] == "recurring" and any(word in text for word in ["recurring", "regular", "periodic", "routine"]):
            score += 1
        elif item["id"] == "local" and any(word in text for word in ["local", "neighborhood", "community", "resident"]):
            score += 1
        elif item["id"] == "performative" and any(word in text for word in ["performance", "show", "act", "entertainment"]):
            score += 1
        elif item["id"] == "blink" and any(word in text for word in ["quick", "passing", "fleeting", "must-see"]):
            score += 1
        elif item["id"] == "social-heavy" and any(word in text for word in ["social", "crowd", "group", "community"]):
            score += 1
        elif item["id"] == "nightlife" and any(word in text for word in ["night", "nightlife", "late", "dark", "club"]):
            score += 1
        elif item["id"] == "touristy" and any(word in text for word in ["tourist", "tour", "explore", "bucket list"]):
            score += 1
        elif item["id"] == "clean-cut" and any(word in text for word in ["polished", "clean", "perfect", "pristine"]):
            score += 1
        elif item["id"] == "beginner" and any(word in text for word in ["beginner", "first-time", "new", "introductory"]):
            score += 1
        elif item["id"] == "iconic" and any(word in text for word in ["iconic", "landmark", "famous", "well-known"]):
            score += 1
        
        # Add base score for categories/tags without keywords
        if not item["keywords"] and score == 0:
            # Check if the category/tag name itself appears in the text
            if item["name"].lower() in text:
                score += 1
            # Check if the category/tag ID appears in the text
            if item["id"].replace("-", " ") in text:
                score += 1
        
        if score > 0:
            scores[item["symbol"] + " " + item["name"]] = score
    
    # Sort by score and return top matches
    sorted_matches = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [match[0] for match in sorted_matches[:3]]

def assign_category(desc: str, context: Dict = None) -> str:
    matches = match_keywords(desc, CATEGORIES, context)
    return matches[0] if matches else "🗂️ Other"

def assign_tags(desc: str, context: Dict = None) -> List[str]:
    matches = match_keywords(desc, TAGS, context)
    return matches[:3] if matches else ["🗂️ Other"]

def extract_context(soup: BeautifulSoup, title: str, desc: str) -> Dict:
    context = {
        'title': title,
        'description': desc,
        'location_name': None,
        'media_desc': None
    }
    
    # Extract location from article
    loc_line = next((p.get_text(strip=True) for p in soup.select("section.article__body p") if "📍" in p.get_text()), None)
    if loc_line:
        context['location_name'] = loc_line.replace("📍", "").strip()
    
    # Extract media description
    img_tag = soup.select_one("section.article__body figure img")
    if img_tag and img_tag.has_attr("alt"):
        context['media_desc'] = img_tag["alt"]
    
    return context

def extract_duration(desc: str) -> Optional[str]:
    patterns = {
        r'\b\d+\s*(?:minute|min)s?\b': 'less-than-15min',
        r'\b1?\s*hour\b': '15min-1hr',
        r'\b[1-2]\s*hours?\b': '1-2hrs',
        r'\b[2-6]\s*hours?\b': '2-6hrs',
        r'\b[6-9]|1[0-2]\s*hours?\b': '6-12hrs',
        r'\b(?:all day|full day)\b': '12-24hrs',
        r'\b(?:permanent|always|forever)\b': 'eternal'
    }
    for pat, dur in patterns.items():
        if re.search(pat, desc, re.IGNORECASE): return dur
    return None

def validate_memento(memento: Dict) -> bool:
    required_fields = ["userId", "name", "description", "category", "timestamp", "mementoTags", "link", "mementoType"]
    return all(field in memento and memento[field] for field in required_fields)

def scrape_article(article_url: str) -> Optional[Dict]:
    session = create_session()
    try:
        response = session.get(article_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Untitled"
        paragraphs = soup.select("section.article__body p")
        desc = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        try:
            if detect(desc) != "en": return None
        except: return None

        cleaned = clean_description(desc)
        
        # Extract context for better matching
        context = extract_context(soup, title, cleaned)

        # ✅ Indoor filter - Modified for Wellness & Nature to allow certain wellness venues
        indoor_keywords = [
            # Entertainment Venues (non-wellness/nature)
            "theater", "theatre", "cinema", "movie", "screening",
            "auditorium", "concert hall", "stage", "performance",
            "show", "play", "musical", "opera",

            # Shopping and Retail
            "mall", "shopping center", "store", "shop", "boutique", "retail",
            "outlet", "department store", "shopping complex", "plaza", "arcade",

            # Entertainment Centers
            "arcade", "game center", "escape room", "vr", "virtual reality",
            "indoor playground", "trampoline park", "laser tag",
            "entertainment complex", "fun center",

            # Office and Business
            "office", "workspace", "coworking", "business center", "corporate",
            "meeting room", "conference center", "convention center",

            # Dining and Nightlife
            "restaurant", "cafe", "cafeteria", "bar", "pub", "club", "lounge",
            "eatery", "bistro", "diner", "food hall", "brewery", "winery",
            "speakeasy", "nightclub", "cocktail bar"
        ]

        # Add wellness and nature exceptions that should not be filtered
        wellness_exceptions = [
            "spa", "wellness center", "yoga studio", "meditation", "fitness center",
            "gym", "studio", "indoor garden", "greenhouse", "conservatory",
            "botanical garden", "nature center", "aquarium", "indoor pool",
            "health center", "healing", "therapy", "treatment", "massage",
            "holistic", "natural", "organic", "eco-friendly"
        ]

        # Check both title and description for indoor keywords
        combined_text = (title + " " + cleaned).lower()
        
        # First check if it's a wellness/nature exception
        is_wellness = any(word in combined_text for word in wellness_exceptions)
        
        # If it's not a wellness venue, then check if it's an indoor venue to filter
        if not is_wellness and any(word in combined_text for word in indoor_keywords):
            return None

        img_tag = soup.select_one("section.article__body figure img")
        media_url = img_tag["src"] if img_tag and img_tag.has_attr("src") else None
        author = soup.select_one("section.article__body figure figcaption")
        author = author.get_text(strip=True) if author else DEFAULT_USER
        if author != DEFAULT_USER and not author.startswith("Source /"):
            author = f"Source / {author}"

        # Extract date - Top News articles often have a different date format
        date_line = next((p.get_text(strip=True) for p in paragraphs if "🗓️" in p.get_text()), None)
        time_tag = soup.find("time")
        article_date = None
        
        # Try to find date in the article metadata first
        meta_date = soup.find("meta", property="article:published_time")
        if meta_date and meta_date.get("content"):
            article_date = meta_date["content"]
        
        timestamp = (
            parse_date(date_line.replace("🗓️", "").strip()) if date_line else
            parse_date(article_date) if article_date else
            parse_date(time_tag["datetime"]) if time_tag and time_tag.has_attr("datetime") else
            datetime.now().strftime("%B %d, %Y at %I:%M %p")
        )

        loc_line = next((p.get_text(strip=True) for p in paragraphs if "📍" in p.get_text()), None)
        loc_name = loc_line.replace("📍", "").strip() if loc_line else extract_fallback_location(desc, title)
        coords = geocode_location(loc_name)

        memento = {
            "userId": author,
            "location": coords,
            "media": [media_url] if media_url else [],
            "name": title,
            "description": cleaned,
            "category": assign_category(cleaned, context),
            "timestamp": timestamp,
            "mementoTags": assign_tags(cleaned, context),
            "link": article_url,
            "mementoType": "public"
        }
        
        dur = extract_duration(cleaned)
        if dur: memento["mementoDuration"] = dur
        
        if not validate_memento(memento):
            logging.warning(f"Invalid memento data for {article_url}")
            return None
            
        return memento
    except Exception as e:
        logging.error(f"Error scraping {article_url}: {e}")
        return None

def process_article(url: str) -> Optional[Dict]:
    try:
        memento = scrape_article(url)
        if memento and memento["location"] and memento["media"] and memento["media"][0] and not memento["media"][0].startswith("data:image/svg"):
            return memento
    except Exception as e:
        logging.error(f"Error processing {url}: {e}")
    return None

# -----------------------------
# MAIN SCRIPT
# -----------------------------
def main():
    # Get total number of pages
    total_pages = get_total_pages()
    logging.info(f"Starting to scrape {total_pages} pages")
    
    all_mementos = []
    failed_pages = []
    
    # Progress tracking
    start_time = time.time()
    total_articles = 0
    
    # Save progress every 10 pages instead of every page
    save_interval = 10
    
    for page_num in range(1, total_pages + 1):
        retries = 0
        while retries < MAX_RETRIES_PER_PAGE:
            try:
                # Progress information
                elapsed_time = time.time() - start_time
                avg_time_per_page = elapsed_time / page_num if page_num > 1 else 0
                estimated_remaining = avg_time_per_page * (total_pages - page_num)
                
                logging.info(f"\n{'='*50}")
                logging.info(f"Processing page {page_num}/{total_pages} ({(page_num/total_pages*100):.1f}%)")
                logging.info(f"Estimated time remaining: {estimated_remaining/60:.1f} minutes")
                logging.info(f"Total articles scraped so far: {total_articles}")
                logging.info(f"{'='*50}\n")
                
                # Scrape the page
                page_mementos = scrape_page(page_num)
                if page_mementos:
                    all_mementos.extend(page_mementos)
                    total_articles += len(page_mementos)
                    
                    # Save progress every save_interval pages
                    if page_num % save_interval == 0 or page_num == total_pages:
                        save_mementos(all_mementos, OUTPUT_PATH)
                    
                    # Add a small delay between pages to be nice to the server
                    if page_num < total_pages:
                        time.sleep(2)
                    
                    # If successful, break the retry loop
                    break
                else:
                    raise Exception("No mementos found on page")
                    
            except Exception as e:
                retries += 1
                logging.error(f"Error scraping page {page_num} (attempt {retries}/{MAX_RETRIES_PER_PAGE}): {e}")
                if retries < MAX_RETRIES_PER_PAGE:
                    time.sleep(5)  # Wait longer between retries
                else:
                    failed_pages.append(page_num)
                    logging.error(f"Failed to scrape page {page_num} after {MAX_RETRIES_PER_PAGE} attempts")
                    break
    
    # Final save
    save_mementos(all_mementos, OUTPUT_PATH)
    
    # Final summary
    logging.info("\n" + "="*50)
    logging.info("Scraping completed!")
    logging.info(f"Total pages processed: {total_pages}")
    logging.info(f"Total articles scraped: {total_articles}")
    logging.info(f"Failed pages: {failed_pages if failed_pages else 'None'}")
    logging.info(f"Total time taken: {(time.time() - start_time)/60:.1f} minutes")
    logging.info(f"Results saved to: {OUTPUT_PATH}")
    logging.info("="*50)

if __name__ == "__main__":
    main()
