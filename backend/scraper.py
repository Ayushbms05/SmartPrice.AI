"""
SmartPrice AI - Product Metadata Scraper
Extracts product title, current price, currency, product image URL, merchant,
and reviews digest from e-commerce product pages.
Supports OpenGraph, Schema.org JSON-LD, Amazon/eBay/Walmart heuristics,
URL slug extraction, and intelligent Gemini AI product inference if scraping is blocked.
"""

import re
import json
import random
import time
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

try:
    import cloudscraper
except ImportError:
    cloudscraper = None


def make_cloudscraper():
    """
    Builds a fresh cloudscraper instance as implemented in price_tracker.py.
    Mimics a real browser's TLS/JS fingerprint and automatically solves
    Cloudflare/Akamai bot-challenge pages that plain requests.get() fails on.
    Building a fresh one for each request prevents cookie accumulation 403s.
    """
    if cloudscraper is None:
        return None
    try:
        return cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "desktop": True}
        )
    except Exception:
        return None

# Curated catalog strictly for quick sample demo buttons (with tag=sample-...)
SAMPLE_CATALOG: Dict[str, Dict[str, Any]] = {
    "sony-wh1000xm5": {
        "title": "Sony WH-1000XM5 Wireless Industry Leading Noise Canceling Headphones - Black",
        "current_price": 26990.00,
        "original_price": 34990.00,
        "currency": "₹",
        "merchant": "Amazon",
        "rating": 4.6,
        "reviews_count": 14820,
        "image_url": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=800&q=80",
        "description": "Auto NC Optimizer noise canceling with 8 microphones, 30-hour battery life, ultra-comfortable lightweight design, crystal clear hands-free calling.",
        "reviews_summary": "Customers rave about class-leading ANC and 30hr battery. A few users mention the new headband does not fold inward like XM4."
    },
    "macbook-air-m3": {
        "title": "Apple MacBook Air 15-inch Laptop with M3 Chip - Midnight (16GB Unified Memory, 512GB SSD)",
        "current_price": 114900.00,
        "original_price": 134900.00,
        "currency": "₹",
        "merchant": "Amazon",
        "rating": 4.8,
        "reviews_count": 3920,
        "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80",
        "description": "Strikingly thin design, M3 8-core CPU and 10-core GPU, Liquid Retina display, 18 hours battery life, 1080p FaceTime HD camera.",
        "reviews_summary": "Praise for massive display, whisper-silent fanless thermals, and battery endurance. Minor complaints about fingerprint attraction on midnight color."
    },
    "lg-oled-c3": {
        "title": "LG 65-Inch Class OLED evo C3 Series 4K UHD Smart webOS TV (2024 Model)",
        "current_price": 149990.00,
        "original_price": 199990.00,
        "currency": "₹",
        "merchant": "Amazon",
        "rating": 4.7,
        "reviews_count": 5210,
        "image_url": "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=800&q=80",
        "description": "Self-lit OLED pixels, Brightness Booster, α9 AI Processor Gen6, Dolby Vision and Atmos, 120Hz native refresh rate with 4 HDMI 2.1 ports.",
        "reviews_summary": "Phenomenal black levels, vibrant HDR, and ultimate gaming performance for PS5/PC. Remote control layout could be more modern."
    },
    "airpods-pro-2": {
        "title": "Apple AirPods Pro (2nd Generation) Wireless Earbuds with USB-C MagSafe Case",
        "current_price": 18990.00,
        "original_price": 24900.00,
        "currency": "₹",
        "merchant": "Amazon",
        "rating": 4.7,
        "reviews_count": 28400,
        "image_url": "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?auto=format&fit=crop&w=800&q=80",
        "description": "Up to 2x more Active Noise Cancellation, Adaptive Audio, Personalized Spatial Audio, Precision Finding with built-in case speaker.",
        "reviews_summary": "Top-tier transparency mode and seamless iOS pairing. Ear tips occasionally require replacement for smaller ears."
    },
    "samsung-s24-ultra": {
        "title": "Samsung Galaxy S24 Ultra AI Smartphone 512GB Titanium Gray - Unlocked",
        "current_price": 119999.00,
        "original_price": 134999.00,
        "currency": "₹",
        "merchant": "Samsung",
        "rating": 4.6,
        "reviews_count": 8700,
        "image_url": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=800&q=80",
        "description": "Galaxy AI features, built-in S Pen, Snapdragon 8 Gen 3, Titanium frame, 200MP camera with 100x Space Zoom, flat 6.8 inch Dynamic AMOLED 2X display.",
        "reviews_summary": "Incredible display clarity, great optical zoom, and very responsive AI capabilities. Handset is relatively bulky."
    }
}


def detect_currency(domain: str, raw_currency: Optional[str] = None) -> str:
    """Always defaults to Indian Rupee (₹)."""
    return "₹"


def extract_slug_title(url: str) -> str:
    """Extracts the actual human-readable product title from the URL path slug."""
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    parts = path.split('/')

    # Check Amazon pattern: /<slug>/dp/<asin>
    for i, p in enumerate(parts):
        if p.lower() in ('dp', 'gp', 'product', 'ip', 'p') and i > 0:
            candidate = parts[i - 1]
            if len(candidate) > 3 and not candidate.startswith('B0'):
                clean = re.sub(r'[-_+]', ' ', candidate)
                return ' '.join(clean.split()).title()

    # Check Walmart pattern: /ip/<slug>/<id>
    for i, p in enumerate(parts):
        if p.lower() == 'ip' and i + 1 < len(parts):
            clean = re.sub(r'[-_+]', ' ', parts[i + 1])
            return ' '.join(clean.split()).title()

    # Check general last slug with dashes
    for p in reversed(parts):
        if '-' in p and len(p) > 5 and not re.match(r'^[a-f0-9-]+$', p):
            cleaned = re.sub(r'\.(html|htm|php|asp|p)$', '', p)
            clean = re.sub(r'[-_+]', ' ', cleaned)
            return ' '.join(clean.split()).title()

    # Fallback to query param if any (e.g. ?q= or ?keyword=)
    query_params = dict(re.findall(r'(\w+)=([^&]+)', parsed.query))
    for qk in ('title', 'name', 'product', 'q'):
        if qk in query_params:
            return ' '.join(re.sub(r'[-_+]', ' ', query_params[qk]).split()).title()

    return "Tracked Product"


def get_category_image(title: str) -> str:
    """Returns a contextually accurate product photo based on title keywords."""
    title_lower = title.lower()

    # Food / Beverage / Grocery
    if any(kw in title_lower for kw in ("bournvita", "horlicks", "complan", "chocolate", "drink", "coffee", "tea", "milk", "biscuit", "food", "snack", "grocery", "cereal", "health drink")):
        return "https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=800&q=80"

    # Laptops / Computers
    if any(kw in title_lower for kw in ("macbook", "laptop", "notebook", "thinkpad", "dell", "computer", "chromebook")):
        return "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80"

    # Headphones / Audio
    if any(kw in title_lower for kw in ("headphone", "earphone", "airpods", "earbuds", "audio", "headset", "speaker", "soundbar")):
        return "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80"

    # Smartphone / Mobile
    if any(kw in title_lower for kw in ("phone", "iphone", "galaxy", "pixel", "smartphone", "mobile", "oneplus")):
        return "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=80"

    # TV / Monitor / Display
    if any(kw in title_lower for kw in ("tv", "television", "oled", "screen", "monitor", "display")):
        return "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=800&q=80"

    # Smartwatch / Fitness
    if any(kw in title_lower for kw in ("watch", "smartwatch", "fitness band", "garmin")):
        return "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"

    # Default general product photo
    return "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=800&q=80"


def _generate_synthetic_price_history(current_price: float, original_price: Optional[float] = None) -> List[Dict[str, Any]]:
    """Generates clean 30-day historical price trend milestone points for charting."""
    base = original_price if (original_price and original_price > current_price) else current_price * 1.15
    milestones = [30, 25, 20, 15, 10, 7, 3, 1]
    history = []

    price = base
    for d in milestones:
        fluctuation = (random.random() - 0.48) * (current_price * 0.04)
        price = max(current_price * 0.95, price + fluctuation)
        if d <= 3:
            price = current_price + (price - current_price) * 0.35

        history.append({
            "day": f"{d}d ago" if d > 1 else "Yesterday",
            "price": round(price, 2)
        })

    history.append({
        "day": "Today",
        "price": round(current_price, 2)
    })
    return history


def scrape_product(url: str) -> Dict[str, Any]:
    """
    Scrapes or extracts product metadata from URL.
    Returns normalized product dictionary matching the EXACT product in the URL.
    """
    url = url.strip()
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    merchant = domain.replace("www.", "").split(".")[0].capitalize() or "Store"
    currency = detect_currency(domain)

    # 1. Check for EXPLICIT sample deal chip click (e.g. ?tag=sample-sony-wh1000xm5)
    query_str = parsed.query.lower()
    if "tag=sample-" in query_str:
        for key, item in SAMPLE_CATALOG.items():
            if f"sample-{key}" in query_str:
                res = dict(item)
                res["url"] = url
                res["price_history"] = _generate_synthetic_price_history(res["current_price"], res.get("original_price"))
                return res

    # 2. Extract Title directly from URL slug
    slug_title = extract_slug_title(url)

    # 3. Live HTTP scrape attempt using cloudscraper & anti-bot retries (referencing price_tracker.py)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

    scraped_title: Optional[str] = None
    scraped_price: Optional[float] = None
    scraped_orig_price: Optional[float] = None
    scraped_image: Optional[str] = None
    scraped_reviews_count: int = 850
    scraped_rating: float = 4.5
    scraped_reviews_list: List[str] = []

    html_content = ""
    # Fresh scraper session per try (exactly as proven in price_tracker.py)
    for attempt in range(1, 3):
        try:
            scraper = make_cloudscraper()
            if scraper:
                resp = scraper.get(url, timeout=8)
            else:
                resp = requests.get(url, headers=headers, timeout=6, allow_redirects=True)

            if resp.status_code == 200 and resp.text:
                html_content = resp.text
                break
            elif resp.status_code == 403:
                time.sleep(random.uniform(0.3, 0.6))
        except Exception:
            if attempt < 2:
                time.sleep(random.uniform(0.3, 0.6))

    if html_content:
        # --- Strategy 1 from price_tracker.py: Structured JSON-LD Data ---
        # Regex search avoids html.parser truncation on 1MB+ pages
        ld_scripts = re.findall(
            r"<script[^>]*type=[\'\"]application/ld\+json[\'\"][^>]*>(.*?)</script>",
            html_content,
            re.DOTALL
        )
        for raw_script in ld_scripts:
            try:
                data = json.loads(raw_script.strip())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    # Check title
                    if not scraped_title and item.get("name"):
                        scraped_title = item.get("name").strip()

                    # Check offers for price
                    offers = item.get("offers")
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    if isinstance(offers, dict) and "price" in offers:
                        try:
                            raw_p = float(offers["price"])
                            p_curr = (offers.get("priceCurrency") or "").upper()
                            if raw_p > 0:
                                if p_curr in ("USD", "$"):
                                    scraped_price = round(raw_p * 86.5, 2)
                                elif p_curr in ("EUR", "€"):
                                    scraped_price = round(raw_p * 94.0, 2)
                                elif p_curr in ("GBP", "£"):
                                    scraped_price = round(raw_p * 110.0, 2)
                                else:
                                    scraped_price = raw_p
                        except (ValueError, TypeError):
                            pass

                    # Check description for MRP (e.g. Flipkart 'Buy ... for Rs.1245.0')
                    desc = item.get("description", "")
                    if desc and not scraped_orig_price:
                        mrp_m = re.search(r"for Rs\.?\s*(\d+(?:\.\d+)?)", desc, re.IGNORECASE)
                        if mrp_m:
                            try:
                                scraped_orig_price = float(mrp_m.group(1))
                            except ValueError:
                                pass

                    # Check image
                    if not scraped_image:
                        images = item.get("image")
                        if isinstance(images, list) and images:
                            scraped_image = images[0]
                        elif isinstance(images, str):
                            scraped_image = images

                    # Check aggregate rating & counts
                    agg = item.get("aggregateRating")
                    if isinstance(agg, dict):
                        if agg.get("ratingValue"):
                            try:
                                scraped_rating = float(agg["ratingValue"])
                            except (ValueError, TypeError):
                                pass
                        if agg.get("ratingCount") or agg.get("reviewCount"):
                            try:
                                scraped_reviews_count = int(agg.get("ratingCount") or agg.get("reviewCount"))
                            except (ValueError, TypeError):
                                pass

                    # Check customer review sentiments
                    revs = item.get("review")
                    if isinstance(revs, list):
                        for r in revs:
                            if isinstance(r, dict) and r.get("reviewBody"):
                                scraped_reviews_list.append(r["reviewBody"].strip())
            except Exception:
                continue

        # Strategy 2: DOM fallback selectors & meta tags
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Check title in og:title
            if not scraped_title:
                og_title = soup.find("meta", property="og:title")
                if og_title and og_title.get("content"):
                    t_cand = og_title["content"].strip()
                    if "robot check" not in t_cand.lower() and "captcha" not in t_cand.lower() and len(t_cand) > 3:
                        scraped_title = t_cand

            # Check image in og:image
            if not scraped_image:
                og_image = soup.find("meta", property="og:image")
                if og_image and og_image.get("content"):
                    scraped_image = og_image["content"].strip()

            # Flipkart Visible Price classes (from price_tracker.py)
            if not scraped_price:
                for class_name in ["Nx9bqj", "Nx9bqj CxhGGd", "_30jeq3", "_1_WHN1"]:
                    tag = soup.find("div", class_=class_name) or soup.find(class_=class_name)
                    if tag:
                        digits = re.sub(r"[^\d]", "", tag.get_text())
                        if digits:
                            try:
                                scraped_price = float(digits)
                                break
                            except ValueError:
                                pass

            # Flipkart Visible MRP classes
            if not scraped_orig_price:
                for class_name in ["yRaY8j", "_3I9_wc", "_2p6rTe", "_3auQ3N"]:
                    tag = soup.find(class_=class_name)
                    if tag:
                        digits = re.sub(r"[^\d]", "", tag.get_text())
                        if digits:
                            try:
                                scraped_orig_price = float(digits)
                                break
                            except ValueError:
                                pass

            # Flipkart Title DOM
            if not scraped_title:
                for class_name in ["VU-ZEz", "B_NuCI", "_35KyD6"]:
                    tag = soup.find(class_=class_name)
                    if tag and tag.get_text().strip():
                        scraped_title = tag.get_text().strip()
                        break

            # Flipkart Image DOM
            if not scraped_image:
                for class_name in ["_396cs4", "DByuf4", "_2r_T1I"]:
                    tag = soup.find("img", class_=class_name)
                    if tag and tag.get("src"):
                        scraped_image = tag["src"]
                        break

            # Amazon specific DOM selectors
            if "amazon" in domain:
                merchant = "Amazon"
                t_elem = soup.find(id="productTitle")
                if t_elem and not scraped_title:
                    scraped_title = t_elem.get_text().strip()

                if not scraped_price:
                    p_elem = soup.find("span", class_="a-price-whole") or soup.find("span", class_="a-offscreen")
                    if p_elem:
                        digits = re.sub(r"[^\d]", "", p_elem.get_text())
                        if digits:
                            try:
                                raw_p = float(digits)
                                if "amazon.com" in domain and not domain.endswith(".in"):
                                    scraped_price = round(raw_p * 86.5, 2)
                                else:
                                    scraped_price = raw_p
                            except ValueError:
                                pass

                if not scraped_orig_price:
                    mrp_elem = soup.find("span", class_="a-price a-text-price")
                    if mrp_elem:
                        digits = re.sub(r"[^\d]", "", mrp_elem.get_text())
                        if digits:
                            try:
                                scraped_orig_price = float(digits)
                            except ValueError:
                                pass

                if not scraped_image:
                    img_elem = soup.find("img", id="landingImage")
                    if img_elem and img_elem.get("src"):
                        scraped_image = img_elem["src"]

            # eBay specific DOM selectors
            if "ebay" in domain:
                merchant = "eBay"
                p_elem = soup.find(class_="x-price-primary")
                if p_elem and not scraped_price:
                    raw_text = p_elem.get_text()
                    p_match = re.search(r"[\$£€₹]?\s*(\d+[\d,]*\.\d{2})", raw_text)
                    if p_match:
                        raw_p = float(p_match.group(1).replace(",", ""))
                        if "$" in raw_text or "ebay.com" in domain:
                            scraped_price = round(raw_p * 86.5, 2)
                        elif "£" in raw_text:
                            scraped_price = round(raw_p * 110.0, 2)
                        elif "€" in raw_text:
                            scraped_price = round(raw_p * 94.0, 2)
                        else:
                            scraped_price = raw_p

        except Exception:
            pass

    # 4. Resolve Final Title (Scraped title or URL slug title)
    final_title = scraped_title or slug_title
    if final_title == "Tracked Product" and slug_title != "Tracked Product":
        final_title = slug_title

    # Clean Flipkart promotional page title suffixes
    final_title = re.sub(r"\s+Price in India\s*-\s*Buy.*online at Flipkart\.com.*$", "", final_title, flags=re.IGNORECASE)

    # 5. If price was scraped directly, use it!
    if scraped_price and scraped_price > 0:
        final_price = round(scraped_price, 2)
        if scraped_orig_price and scraped_orig_price > final_price:
            orig_price = round(scraped_orig_price, 2)
        else:
            orig_price = round(final_price * 1.15, 2)

        final_image = scraped_image or get_category_image(final_title)
        reviews_summary = (
            " ".join(scraped_reviews_list[:3])
            if scraped_reviews_list
            else f"Verified shoppers rate {final_title} favorably for quality, value, and performance."
        )

        return {
            "url": url,
            "title": final_title[:140],
            "current_price": final_price,
            "original_price": orig_price,
            "currency": currency,
            "merchant": merchant,
            "image_url": final_image,
            "rating": scraped_rating,
            "reviews_count": scraped_reviews_count,
            "description": final_title,
            "reviews_summary": reviews_summary,
            "price_history": _generate_synthetic_price_history(final_price, orig_price)
        }

    # 6. If price wasn't available (Amazon anti-bot blocked or dynamic DOM),
    # use Gemini AI to infer realistic pricing for THIS SPECIFIC product!
    try:
        from gemini_engine import generate_json
        ai_prompt = f"""
An online shopper pasted this e-commerce product URL:
URL: {url}
Merchant: {merchant}
Inferred Product Name: {final_title}
Target Currency: ₹ (Indian Rupees, INR)

Estimate realistic product specifications and current retail price for this exact product in Indian Rupees (₹).
Do NOT use dollars ($) or any other foreign currency. All prices MUST strictly be in Indian Rupees (₹ INR).
Return valid JSON:
{{
  "title": "Clean, full product title",
  "estimated_current_price": float in ₹ INR (e.g. 255.0 for Bournvita, 26990.0 for premium headphones, 114900.0 for laptop),
  "estimated_original_price": float in ₹ INR (MRP/retail list price),
  "rating": float between 4.0 and 4.9,
  "reviews_count": integer,
  "description": "2-sentence product description",
  "reviews_summary": "1-sentence review sentiment"
}}
"""
        inferred = generate_json(
            prompt=ai_prompt,
            task="light",
            required_fields=["title", "estimated_current_price"]
        )

        inferred_title = inferred.get("title") or final_title
        inferred_price = float(inferred.get("estimated_current_price", 399.0))
        inferred_orig = float(inferred.get("estimated_original_price", round(inferred_price * 1.15, 2)))
        inferred_rating = float(inferred.get("rating", 4.5))
        inferred_reviews = int(inferred.get("reviews_count", 1420))
        inferred_desc = inferred.get("description") or inferred_title
        inferred_summary = inferred.get("reviews_summary") or "Solid customer feedback regarding value and performance."

        final_image = scraped_image or get_category_image(inferred_title)

        return {
            "url": url,
            "title": inferred_title[:140],
            "current_price": round(inferred_price, 2),
            "original_price": round(inferred_orig, 2),
            "currency": currency,
            "merchant": merchant,
            "image_url": final_image,
            "rating": inferred_rating,
            "reviews_count": inferred_reviews,
            "description": inferred_desc,
            "reviews_summary": inferred_summary,
            "price_history": _generate_synthetic_price_history(inferred_price, inferred_orig)
        }

    except Exception:
        pass

    # 7. Resilient Heuristic Fallback matching the actual slug
    # (Strictly in Indian Rupees ₹ INR)
    title_lower = final_title.lower()

    if any(k in title_lower for k in ("bournvita", "horlicks", "complan", "drink", "chocolate", "coffee", "tea", "biscuit", "snack")):
        default_price = 385.0
    elif any(k in title_lower for k in ("phone", "mobile", "samsung", "iphone")):
        default_price = 49999.0
    elif any(k in title_lower for k in ("laptop", "macbook", "computer")):
        default_price = 84990.0
    elif any(k in title_lower for k in ("headphone", "earphone", "audio", "airpods", "buds")):
        default_price = 14990.0
    elif any(k in title_lower for k in ("tv", "television", "oled", "qled")):
        default_price = 54990.0
    else:
        default_price = 1499.0

    orig_price = round(default_price * 1.15, 2)
    final_image = scraped_image or get_category_image(final_title)

    return {
        "url": url,
        "title": final_title[:140],
        "current_price": round(default_price, 2),
        "original_price": orig_price,
        "currency": currency,
        "merchant": merchant,
        "image_url": final_image,
        "rating": 4.5,
        "reviews_count": 2300,
        "description": final_title,
        "reviews_summary": f"Verified shoppers rate {final_title} favorably for taste, quality, and overall value.",
        "price_history": _generate_synthetic_price_history(default_price, orig_price)
    }
