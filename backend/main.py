"""
SmartPrice AI - FastAPI Backend Server & AWS Lambda Handler
Provides REST endpoints for product scraping, Gemini AI deal analysis,
natural language chat advisor, price alert simulations, and observability.
"""

import os
import json
import uuid
import time
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from mangum import Mangum

from dotenv import load_dotenv
load_dotenv()

from gemini_engine import (
    analyze_deal,
    ask_advisor,
    get_last_call_info,
    _circuit_consecutive_failures,
    _circuit_cooldown_expiry,
    LOG_FILE
)
from scraper import scrape_product, SAMPLE_CATALOG

app = FastAPI(
    title="SmartPrice AI API",
    description="Intelligent Price Tracking and Deal Analysis powered by Google Gemini API",
    version="1.0.0"
)

# Enable CORS for local dev and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage with file persistence fallback for local state & instant demonstration
DB_FILE = os.path.join(os.path.dirname(__file__), "tracked_products.json")


def _load_products() -> List[Dict[str, Any]]:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Initialize with default sample products for rich instant dashboard view
    initial_items = [
        {
            "id": "prod-bournvita-0",
            "url": "https://www.amazon.in/Cadbury-Bournvita-Chocolate-Health-Drink-Refill/dp/B00T7BVY8Q",
            "title": "Cadbury Bournvita Chocolate Health Drink Refill - 500 g",
            "current_price": 255.00,
            "original_price": 275.00,
            "target_price": 245.00,
            "currency": "₹",
            "merchant": "Amazon",
            "image_url": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=800&q=80",
            "rating": 4.5,
            "reviews_count": 14250,
            "alert_enabled": True,
            "alert_email": "shopper@example.com",
            "last_updated": time.time() - 1800,
            "verdict_data": {
                "verdict": "BUY NOW",
                "rationale": "The current price of ₹255 offers a steady grocery markdown close to wholesale average. Since nutrition drink pricing is stable year-round, waiting for a holiday sale is unnecessary.",
                "deal_integrity_score": 88,
                "pros": ["Classic chocolate malt taste", "Enriched with vitamins & minerals", "Consistent everyday value"],
                "cons": ["Refill pack needs an airtight container", "Marginal 7% discount"],
                "recommended_target_price": 245.00,
                "price_trend_prediction": "Stable price"
            },
            "price_history": [
                {"day": "30 days ago", "price": 275.00},
                {"day": "20 days ago", "price": 269.00},
                {"day": "10 days ago", "price": 260.00},
                {"day": "Yesterday", "price": 255.00},
                {"day": "Today", "price": 255.00}
            ]
        },
        {
            "id": "prod-sony-1",
            "url": "https://www.amazon.in/dp/B09XS7JWHH",
            "title": "Sony WH-1000XM5 Wireless Industry Leading Noise Canceling Headphones - Black",
            "current_price": 26990.00,
            "original_price": 34990.00,
            "target_price": 25000.00,
            "currency": "₹",
            "merchant": "Amazon",
            "image_url": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=800&q=80",
            "rating": 4.6,
            "reviews_count": 14820,
            "alert_enabled": True,
            "alert_email": "shopper@example.com",
            "last_updated": time.time() - 3600,
            "verdict_data": {
                "verdict": "BUY NOW",
                "rationale": "Current price of ₹26,990 is within 2% of the all-time historic low recorded during Great Indian Festival sales. Further markdowns before festive sales are unlikely.",
                "deal_integrity_score": 94,
                "pros": ["Authentic ₹8,000 markdown off MSRP", "Industry-leading active noise cancellation", "Exceptional 30-hour battery life"],
                "cons": ["Non-folding headband design", "Microfiber earcups can warm up"],
                "recommended_target_price": 26000.00,
                "price_trend_prediction": "At historic low"
            },
            "price_history": [
                {"day": "30 days ago", "price": 34990.00},
                {"day": "20 days ago", "price": 31990.00},
                {"day": "10 days ago", "price": 28990.00},
                {"day": "Yesterday", "price": 27490.00},
                {"day": "Today", "price": 26990.00}
            ]
        },
        {
            "id": "prod-mac-2",
            "url": "https://www.amazon.in/Apple-MacBook-15-inch-Unified-512GB/dp/B0CX21C8S1",
            "title": "Apple MacBook Air 15-inch Laptop with M3 Chip - Midnight (16GB, 512GB)",
            "current_price": 114900.00,
            "original_price": 134900.00,
            "target_price": 108000.00,
            "currency": "₹",
            "merchant": "Amazon",
            "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80",
            "rating": 4.8,
            "reviews_count": 3920,
            "alert_enabled": True,
            "alert_email": "shopper@example.com",
            "last_updated": time.time() - 7200,
            "verdict_data": {
                "verdict": "WAIT",
                "rationale": "Apple hardware typically receives bank discounts up to ₹10,000 during upcoming festive promotions. Holding off could yield substantial additional savings.",
                "deal_integrity_score": 78,
                "pros": ["Stellar M3 power efficiency & battery", "Stunning Liquid Retina display", "Silent fanless aluminum unibody"],
                "cons": ["Upgraded storage tiers are pricey", "Midnight finish attracts fingerprints"],
                "recommended_target_price": 108000.00,
                "price_trend_prediction": "Likely to drop within 30 days"
            },
            "price_history": [
                {"day": "30 days ago", "price": 134900.00},
                {"day": "20 days ago", "price": 124900.00},
                {"day": "10 days ago", "price": 119900.00},
                {"day": "Yesterday", "price": 114900.00},
                {"day": "Today", "price": 114900.00}
            ]
        },
        {
            "id": "prod-tv-3",
            "url": "https://www.amazon.in/dp/B0BYZLX5F3",
            "title": "LG 65-Inch Class OLED evo C3 Series 4K UHD Smart webOS TV",
            "current_price": 149990.00,
            "original_price": 199990.00,
            "target_price": 139990.00,
            "currency": "₹",
            "merchant": "Amazon",
            "image_url": "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=800&q=80",
            "rating": 4.7,
            "reviews_count": 5210,
            "alert_enabled": False,
            "alert_email": "",
            "last_updated": time.time() - 14400,
            "verdict_data": {
                "verdict": "BUY NOW",
                "rationale": "Deep clearance discount of ₹50,000 off MRP. This matches the lowest recorded festive promotion price for LG OLED displays.",
                "deal_integrity_score": 96,
                "pros": ["Exceptional infinite contrast & blacks", "Superb HDR performance for movies & gaming", "4 HDMI 2.1 120Hz ports"],
                "cons": ["Slightly reflective in direct sunlight", "Audio speaker is basic without soundbar"],
                "recommended_target_price": 145000.00,
                "price_trend_prediction": "At historic low"
            },
            "price_history": [
                {"day": "30 days ago", "price": 199990.00},
                {"day": "20 days ago", "price": 174990.00},
                {"day": "10 days ago", "price": 159990.00},
                {"day": "Yesterday", "price": 149990.00},
                {"day": "Today", "price": 149990.00}
            ]
        }
    ]
    _save_products(initial_items)
    return initial_items


def _save_products(items: List[Dict[str, Any]]):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# Request & Response Schemas
class ScrapeRequest(BaseModel):
    url: str


class AnalyzeRequest(BaseModel):
    product_title: str
    current_price: float
    original_price: Optional[float] = None
    currency: str = "₹"
    merchant: str = "Store"
    rating: Optional[float] = None
    reviews_summary: Optional[str] = ""


class ChatRequest(BaseModel):
    question: str
    product_title: str
    current_price: float
    currency: str = "₹"
    merchant: str = "Store"
    verdict_data: Optional[Dict[str, Any]] = None


class TrackProductRequest(BaseModel):
    url: str
    target_price: Optional[float] = None
    alert_enabled: bool = True
    alert_email: Optional[str] = ""


class UpdateProductRequest(BaseModel):
    target_price: Optional[float] = None
    alert_enabled: Optional[bool] = None
    alert_email: Optional[str] = None


class SimulatePriceDropRequest(BaseModel):
    new_price: Optional[float] = None
    percent_drop: Optional[float] = 15.0


# Endpoints
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "SmartPrice AI", "timestamp": time.time()}


@app.get("/api/status")
def get_system_status():
    """Returns observability status, circuit breaker states, and recent log records."""
    last_call = get_last_call_info()

    # Read recent logs
    recent_logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                recent_logs = lines[-15:]
        except Exception:
            pass

    return {
        "last_call": last_call,
        "circuit_breaker": {
            "failures": _circuit_consecutive_failures,
            "cooldowns": {
                k: max(0.0, round(v - time.time(), 1))
                for k, v in _circuit_cooldown_expiry.items()
                if v > time.time()
            }
        },
        "recent_logs": recent_logs,
        "sample_catalog": list(SAMPLE_CATALOG.keys())
    }


@app.post("/api/scrape")
def api_scrape(req: ScrapeRequest):
    """Extracts product details, specs, and price history from given URL."""
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Product URL is required")
    try:
        product_data = scrape_product(req.url)
        return {"success": True, "product": product_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")


@app.post("/api/analyze")
def api_analyze(req: AnalyzeRequest):
    """Runs Gemini AI Verdict Engine with structured JSON schema."""
    try:
        verdict = analyze_deal(
            product_title=req.product_title,
            current_price=req.current_price,
            original_price=req.original_price,
            currency=req.currency,
            merchant=req.merchant,
            rating=req.rating,
            reviews_summary=req.reviews_summary or ""
        )
        last_call = get_last_call_info()
        return {"success": True, "verdict": verdict, "metadata": last_call}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    """
    Natural language deal advisor (e.g. 'Should I buy it now?').
    Uses task='heavy' for reasoned, contextual advice.
    """
    try:
        advice = ask_advisor(
            question=req.question,
            product_title=req.product_title,
            current_price=req.current_price,
            currency=req.currency,
            merchant=req.merchant,
            verdict_data=req.verdict_data
        )
        last_call = get_last_call_info()
        return {"success": True, "advice": advice, "metadata": last_call}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products")
def list_products():
    """Returns all tracked products."""
    products = _load_products()
    return {"success": True, "count": len(products), "products": products}


@app.post("/api/products")
def create_tracked_product(req: TrackProductRequest):
    """Scrapes, analyzes, and saves a newly tracked product."""
    # 1. Scrape product
    scraped = scrape_product(req.url)

    # 2. Run Gemini Verdict Engine
    verdict = analyze_deal(
        product_title=scraped["title"],
        current_price=scraped["current_price"],
        original_price=scraped.get("original_price"),
        currency=scraped.get("currency", "₹"),
        merchant=scraped.get("merchant", "Store"),
        rating=scraped.get("rating"),
        reviews_summary=scraped.get("reviews_summary", "")
    )

    recommended_target = verdict.get("recommended_target_price") or round(scraped["current_price"] * 0.9, 2)
    target_price = req.target_price if req.target_price else recommended_target

    product_id = f"prod-{uuid.uuid4().hex[:8]}"
    item = {
        "id": product_id,
        "url": scraped["url"],
        "title": scraped["title"],
        "current_price": scraped["current_price"],
        "original_price": scraped.get("original_price"),
        "target_price": target_price,
        "currency": scraped.get("currency", "₹"),
        "merchant": scraped.get("merchant", "Store"),
        "image_url": scraped.get("image_url"),
        "rating": scraped.get("rating"),
        "reviews_count": scraped.get("reviews_count", 0),
        "alert_enabled": req.alert_enabled,
        "alert_email": req.alert_email or "",
        "last_updated": time.time(),
        "verdict_data": verdict,
        "price_history": scraped.get("price_history", [])
    }

    products = _load_products()
    # Prepend new item to list
    products.insert(0, item)
    _save_products(products)

    return {"success": True, "product": item}


@app.put("/api/products/{product_id}")
def update_product(product_id: str, req: UpdateProductRequest):
    """Updates target price and alert settings for a product."""
    products = _load_products()
    for p in products:
        if p["id"] == product_id:
            if req.target_price is not None:
                p["target_price"] = req.target_price
            if req.alert_enabled is not None:
                p["alert_enabled"] = req.alert_enabled
            if req.alert_email is not None:
                p["alert_email"] = req.alert_email
            p["last_updated"] = time.time()
            _save_products(products)
            return {"success": True, "product": p}
    raise HTTPException(status_code=404, detail="Product not found")


@app.delete("/api/products/{product_id}")
def delete_product(product_id: str):
    """Deletes a tracked product."""
    products = _load_products()
    filtered = [p for p in products if p["id"] != product_id]
    if len(filtered) == len(products):
        raise HTTPException(status_code=404, detail="Product not found")
    _save_products(filtered)
    return {"success": True, "message": "Product removed from tracking"}


@app.post("/api/products/{product_id}/simulate-drop")
def simulate_price_drop(product_id: str, req: SimulatePriceDropRequest):
    """
    Simulates a price drop on a tracked product to trigger alert notification evaluation
    and updates historical chart.
    """
    products = _load_products()
    for p in products:
        if p["id"] == product_id:
            old_price = p["current_price"]
            if req.new_price is not None:
                new_price = req.new_price
            else:
                drop_pct = (req.percent_drop or 15.0) / 100.0
                new_price = round(old_price * (1.0 - drop_pct), 2)

            p["current_price"] = new_price
            p["last_updated"] = time.time()

            # Append to history
            history = p.get("price_history", [])
            history.append({
                "day": "Simulated Drop",
                "price": new_price
            })
            p["price_history"] = history

            # Re-evaluate Gemini AI verdict with new price
            try:
                new_verdict = analyze_deal(
                    product_title=p["title"],
                    current_price=new_price,
                    original_price=p.get("original_price") or old_price,
                    currency=p.get("currency", "₹"),
                    merchant=p.get("merchant", "Store"),
                    rating=p.get("rating"),
                    reviews_summary="Price suddenly dropped below recent average."
                )
                p["verdict_data"] = new_verdict
            except Exception:
                pass

            _save_products(products)

            alert_triggered = bool(p.get("alert_enabled") and new_price <= p.get("target_price", 0))
            return {
                "success": True,
                "product": p,
                "old_price": old_price,
                "new_price": new_price,
                "alert_triggered": alert_triggered,
                "savings": round(old_price - new_price, 2)
            }

    raise HTTPException(status_code=404, detail="Product not found")


# Mangum ASGI adapter for AWS Lambda deployment
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
