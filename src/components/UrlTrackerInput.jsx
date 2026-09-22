import React, { useState } from 'react';
import { Link2, Sparkles, Loader2, ArrowRight, CheckCircle2, AlertCircle } from 'lucide-react';

const SAMPLE_PRODUCTS = [
  {
    name: 'Bournvita Refill 500g',
    tag: 'cadbury-bournvita',
    url: 'https://www.amazon.in/Cadbury-Bournvita-Chocolate-Health-Drink-Refill/dp/B00T7BVY8Q',
    store: 'Amazon India',
    price: '₹255'
  },
  {
    name: 'Sony WH-1000XM5',
    tag: 'sony-wh1000xm5',
    url: 'https://www.amazon.in/dp/B09XS7JWHH?tag=sample-sony-wh1000xm5',
    store: 'Amazon India',
    price: '₹26,990'
  },
  {
    name: 'MacBook Air 15" M3',
    tag: 'macbook-air-m3',
    url: 'https://www.amazon.in/Apple-MacBook-15-inch-Unified-512GB/dp/B0CX21C8S1?tag=sample-macbook-air-m3',
    store: 'Amazon India',
    price: '₹1,14,900'
  },
  {
    name: 'LG C3 OLED 65"',
    tag: 'lg-oled-c3',
    url: 'https://www.amazon.in/dp/B0BYZLX5F3?tag=sample-lg-oled-c3',
    store: 'Amazon India',
    price: '₹1,49,990'
  },
  {
    name: 'AirPods Pro 2',
    tag: 'airpods-pro-2',
    url: 'https://www.amazon.in/Apple-AirPods-Pro-2nd-Generation/dp/B0BDHW459S?tag=sample-airpods-pro-2',
    store: 'Amazon India',
    price: '₹18,990'
  }
];

export default function UrlTrackerInput({ onTrackUrl, isLoading, loadingStep }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!url.trim()) {
      setError('Please paste a product URL to track');
      return;
    }
    setError('');
    onTrackUrl(url.trim());
  };

  const handleSelectSample = (sampleUrl) => {
    setUrl(sampleUrl);
    setError('');
    onTrackUrl(sampleUrl);
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="relative group">
        {/* Ambient Gradient Glow */}
        <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500/20 via-indigo-500/20 to-emerald-500/20 rounded-3xl blur-xl opacity-75 group-hover:opacity-100 transition duration-500" />

        <div className="relative glass-panel rounded-2xl p-4 sm:p-6 shadow-2xl border border-slate-800">
          <div className="flex flex-col space-y-4">
            {/* Header / Subtitle */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                <span className="text-xs font-semibold tracking-wide uppercase text-emerald-400">
                  Real-time Scraper & Gemini AI Verdict
                </span>
              </div>
              <span className="text-xs text-slate-400">Supports Amazon.in, Flipkart, Blinkit, Croma, Tata Neu & more</span>
            </div>

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Link2 className="h-5 w-5 text-slate-500" />
                </div>
                <input
                  type="url"
                  id="product-url-input"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    if (error) setError('');
                  }}
                  disabled={isLoading}
                  placeholder="Paste any product URL (e.g., https://www.amazon.in/dp/... or Flipkart link)"
                  className="w-full pl-11 pr-4 py-3.5 rounded-xl bg-dark-900/90 text-white placeholder-slate-500 border border-slate-700/80 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30 outline-none transition text-sm sm:text-base font-normal shadow-inner disabled:opacity-50"
                />
              </div>

              <button
                type="submit"
                id="track-price-btn"
                disabled={isLoading}
                className="flex items-center justify-center space-x-2 px-6 py-3.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-bold transition shadow-lg shadow-emerald-500/25 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed whitespace-nowrap"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin text-slate-950" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-5 w-5 text-slate-950" />
                    <span>Track Price</span>
                    <ArrowRight className="h-4 w-4 text-slate-950" />
                  </>
                )}
              </button>
            </form>

            {/* Error Display */}
            {error && (
              <div className="flex items-center space-x-2 text-xs text-rose-400 bg-rose-950/40 px-3 py-2 rounded-lg border border-rose-800/40">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Loading Progression Stages */}
            {isLoading && (
              <div className="bg-slate-900/80 rounded-xl p-3 border border-slate-800 text-xs flex items-center justify-between animate-pulse">
                <div className="flex items-center space-x-2.5 text-emerald-400 font-medium">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{loadingStep || 'Scraping product metadata and extracting DOM prices...'}</span>
                </div>
                <span className="text-[11px] text-slate-500">Gemini Tiered Fallback Active</span>
              </div>
            )}

            {/* Quick Sample Links Chips */}
            <div className="pt-2 border-t border-slate-800/60 flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-400 font-medium mr-1">Quick Test Deals:</span>
              {SAMPLE_PRODUCTS.map((item) => (
                <button
                  key={item.tag}
                  type="button"
                  onClick={() => handleSelectSample(item.url)}
                  disabled={isLoading}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/60 hover:border-slate-600 transition disabled:opacity-50"
                >
                  <span className="font-semibold text-slate-200">{item.name}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">{item.store}</span>
                  <span className="text-emerald-400 font-medium">{item.price}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
