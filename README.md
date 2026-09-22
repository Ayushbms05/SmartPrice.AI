# SmartPrice AI 🛒✨
### Intelligent E-Commerce Price Tracking & Deal Analysis Powered by Google Gemini

SmartPrice AI is a full-stack, responsive web application that empowers shoppers to track product prices, visualize 30-day historical trendlines, receive automated target price drop alerts, and get AI-generated purchase recommendations powered by **Google Gemini**.

Designed for resilience, speed, and real-time accuracy across major e-commerce platforms (Amazon, Flipkart, etc.) with full native support for **Indian Rupees (`₹`)**.

---

## 🌟 Key Features

- **Live Multi-Store Web Scraping**:
  - Direct URL extraction for Amazon, Flipkart, and general e-commerce platforms.
  - Built-in anti-bot bypass powered by `cloudscraper` with browser TLS fingerprinting and automated retry backoff.
  - Deep schema extraction using regex JSON-LD parsing to reliably extract live prices, original MRPs, high-resolution product photography, review scores, and verified ratings.

- **Self-Healing Google Gemini Verdict Engine**:
  - Analyzes whether a product is a **"BUY NOW"**, **"WAIT"**, or **"DON'T BUY"**.
  - Provides concise 3-bullet verified pros and drawbacks tailored to consumer sentiment.
  - Predicts realistic 30-day price trends and calculates optimal target strike prices.
  - Natural Language Deal Advisor chat allowing users to ask conversational questions about any product.

- **Sleek Price History & Trendline Charting**:
  - Interactive SVG trendline with milestone sampling (`30d ago`, `20d ago`, `10d ago`, `Today`).
  - Edge-anchored labels that never collide or clip.
  - Standout glowing pulse halo on the current price.
  - Hover crosshair with interactive floating tooltip card displaying date and rupee price.

- **Automated Price Drop Alert Simulation**:
  - Set custom target strike prices and alert emails.
  - One-click price drop simulator to test threshold notifications and toast alerts.

---

## 🏛️ Architectural Resilience Pillars

SmartPrice AI's Gemini integration is engineered to run error-free on a single API key with zero downtime:

1. **Security & Key Isolation**: API keys are isolated to the server-side environment. Zero leaks in logs or client-side bundles. Disabled internal SDK retries in favor of application-level retry controls.
2. **Multi-Model Fallback Chains**: Tiered routing (`light` vs `heavy`) with automatic failover across models (`gemini-3.6-flash` ➔ `gemini-3.5-flash-lite` ➔ `gemini-3.1-flash-lite` ➔ `gemini-flash-lite-latest`).
3. **Intelligent Error Classification**: Immediate failover on `503 Service Unavailable`, zero-delay model skipping on `404 Not Found`, exponential backoff on `429 Rate Limits`, and hard abort on `401/403 Invalid Keys`.
4. **Self-Healing Output Validation**: Automatic markdown code fence stripping and JSON schema enforcement with single-attempt zero-temperature schema correction.
5. **Circuit Breaker & Load Protection**: Thread-safe minimum request throttle (1.0s) and 60-second circuit breaker cooldown after consecutive model errors.
6. **Content-Addressable Cache**: In-memory SHA-256 caching for instant responses (< 5ms) on identical product queries.
7. **Redacted Observability**: Structured rotating logs (`backend/logs/calls.log`) with strict non-logging of keys and raw prompts.

---

## 🛠️ Tech Stack

- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React icons
- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pydantic
- **Web Scraping**: Cloudscraper, BeautifulSoup4, Requests
- **AI & LLM**: Google GenAI SDK (`google-genai`), Google Gemini 1.5/2.5/3.x models
- **Deployment Ready**: AWS Amplify (`amplify.yml`), AWS Lambda / FastAPI, DynamoDB schema structure

---

## 🚀 Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Ayushbms05/SmartPrice.AI.git
cd SmartPrice.AI
```

### 2. Configure Environment Variables
Copy the `.env.example` template:
```bash
cp .env.example .env
```
Open `.env` and add your **Google Gemini API Key**:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
*(The `.env` file is strictly ignored by `.gitignore` and will never be committed).*

### 3. Backend Setup
```bash
# Create and activate a Python virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate  # On Windows: backend\venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Start the FastAPI backend server
python backend/main.py
```
The API server will run at `http://127.0.0.1:8000`.

### 4. Frontend Setup
In a separate terminal:
```bash
# Install frontend dependencies
npm install

# Start the Vite development server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Running Resilience Tests

To verify that the Gemini fallback chains, error classification, caching, and scraper operate correctly:
```bash
./backend/venv/bin/python backend/test_gemini_resilience.py
```

---

## 🔒 Security Best Practices

- **Never commit `.env`**: Always use `.env.example` as a template for team members.
- **Server-Side API Calls**: All communication with Gemini runs server-side via FastAPI endpoints (`/api/scrape`, `/api/chat`, etc.). The frontend never accesses or stores the Gemini API key.
- **Strict Gitignore**: Git ignore patterns protect against committing logs, cache files, and virtual environments.

---

## 📄 License
MIT License. Built for modern, intelligent shopping.
