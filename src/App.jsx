import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import UrlTrackerInput from './components/UrlTrackerInput';
import ProductCard from './components/ProductCard';
import ProductDetailModal from './components/ProductDetailModal';
import AlertNotificationToast from './components/AlertNotificationToast';
import SettingsModal from './components/SettingsModal';
import { 
  Sparkles, 
  TrendingDown, 
  ShieldCheck, 
  Search, 
  SlidersHorizontal, 
  RefreshCw,
  Flame,
  Clock,
  AlertTriangle,
  Zap,
  Info
} from 'lucide-react';

export default function App() {
  const [products, setProducts] = useState([]);
  const [isLoadingProducts, setIsLoadingProducts] = useState(true);
  const [isTrackingUrl, setIsTrackingUrl] = useState(false);
  const [trackingStep, setTrackingStep] = useState('');
  
  // Modals & Drawers
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [activeToast, setActiveToast] = useState(null);

  // Filter & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('ALL'); // 'ALL' | 'BUY NOW' | 'WAIT' | 'HIGH_INTEGRITY'
  const [sortBy, setSortBy] = useState('DEFAULT'); // 'DEFAULT' | 'SAVINGS' | 'PRICE_ASC' | 'PRICE_DESC' | 'INTEGRITY'

  // Fetch tracked products on mount
  const fetchProducts = async () => {
    setIsLoadingProducts(true);
    try {
      const resp = await fetch('/api/products');
      if (resp.ok) {
        const data = await resp.json();
        if (data.products) {
          setProducts(data.products);
        }
      }
    } catch (err) {
      console.error('Error loading products:', err);
    } finally {
      setIsLoadingProducts(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  // Track new URL
  const handleTrackUrl = async (url) => {
    setIsTrackingUrl(true);
    setTrackingStep('Connecting to retailer & scraping metadata...');

    try {
      // Small simulated step update for UX richness
      setTimeout(() => {
        setTrackingStep('Running Gemini AI multi-model verdict engine...');
      }, 700);

      const resp = await fetch('/api/products', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: url
        })
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Failed to track product');
      }

      if (data.product) {
        setProducts(prev => [data.product, ...prev.filter(p => p.id !== data.product.id)]);
        setSelectedProduct(data.product); // Automatically open modal to review deal
      }
    } catch (err) {
      alert(`Could not track product: ${err.message}`);
    } finally {
      setIsTrackingUrl(false);
      setTrackingStep('');
    }
  };

  // Update Alert Settings
  const handleUpdateAlerts = async (productId, updates) => {
    try {
      const resp = await fetch(`/api/products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      if (resp.ok) {
        const data = await resp.json();
        setProducts(prev => prev.map(p => p.id === productId ? data.product : p));
        if (selectedProduct && selectedProduct.id === productId) {
          setSelectedProduct(data.product);
        }
      }
    } catch (err) {
      console.error('Update alerts error:', err);
    }
  };

  // Simulate Price Drop
  const handleSimulateDrop = async (productId) => {
    try {
      const resp = await fetch(`/api/products/${productId}/simulate-drop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ percent_drop: 15.0 })
      });

      if (resp.ok) {
        const data = await resp.json();
        const updated = data.product;

        setProducts(prev => prev.map(p => p.id === productId ? updated : p));
        if (selectedProduct && selectedProduct.id === productId) {
          setSelectedProduct(updated);
        }

        // Trigger alert toast if alert condition is met
        setActiveToast({
          title: updated.title,
          old_price: data.old_price,
          new_price: data.new_price,
          savings: data.savings,
          alert_triggered: data.alert_triggered
        });
      }
    } catch (err) {
      console.error('Simulate price drop error:', err);
    }
  };

  // Delete product
  const handleDeleteProduct = async (productId) => {
    if (!confirm('Are you sure you want to stop tracking this product?')) return;
    try {
      const resp = await fetch(`/api/products/${productId}`, {
        method: 'DELETE'
      });
      if (resp.ok) {
        setProducts(prev => prev.filter(p => p.id !== productId));
        if (selectedProduct && selectedProduct.id === productId) {
          setSelectedProduct(null);
        }
      }
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  // Calculations for ribbon
  const totalSavings = products.reduce((acc, p) => {
    if (p.original_price && p.original_price > p.current_price) {
      return acc + (p.original_price - p.current_price);
    }
    return acc;
  }, 0);

  // Filtered & Sorted products
  const filteredProducts = products.filter(p => {
    const matchesSearch = p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (p.merchant && p.merchant.toLowerCase().includes(searchQuery.toLowerCase()));
    if (!matchesSearch) return false;

    if (selectedFilter === 'BUY NOW') return p.verdict_data?.verdict === 'BUY NOW';
    if (selectedFilter === 'WAIT') return p.verdict_data?.verdict === 'WAIT';
    if (selectedFilter === 'HIGH_INTEGRITY') return (p.verdict_data?.deal_integrity_score ?? 0) >= 90;
    return true;
  }).sort((a, b) => {
    if (sortBy === 'PRICE_ASC') return a.current_price - b.current_price;
    if (sortBy === 'PRICE_DESC') return b.current_price - a.current_price;
    if (sortBy === 'INTEGRITY') return (b.verdict_data?.deal_integrity_score ?? 0) - (a.verdict_data?.deal_integrity_score ?? 0);
    if (sortBy === 'SAVINGS') {
      const savA = (a.original_price || a.current_price) - a.current_price;
      const savB = (b.original_price || b.current_price) - b.current_price;
      return savB - savA;
    }
    return 0; // Default
  });

  return (
    <div className="min-h-screen flex flex-col bg-dark-950 text-slate-100 selection:bg-emerald-500 selection:text-white">
      {/* Top Navbar */}
      <Navbar 
        onOpenSettings={() => setIsSettingsOpen(true)}
        trackedCount={products.length}
        totalSavings={totalSavings}
      />

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
        
        {/* Hero & URL Input Section */}
        <section className="text-center space-y-6 pt-4 pb-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
            <Sparkles className="h-3.5 w-3.5" />
            <span>AI Price Tracking & Deal Authenticity Engine</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white max-w-4xl mx-auto leading-tight">
            Never Overpay Again. <br className="hidden sm:block" />
            <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
              AI-Powered Deal Intelligence.
            </span>
          </h1>

          <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Paste any product URL. SmartPrice AI extracts live prices, maps historical trends, and delivers instant <span className="text-emerald-400 font-semibold">BUY NOW</span> or <span className="text-amber-400 font-semibold">WAIT</span> verdicts using Gemini 1.5 Flash.
          </p>

          {/* URL Tracker Input Bar */}
          <div className="pt-2">
            <UrlTrackerInput 
              onTrackUrl={handleTrackUrl}
              isLoading={isTrackingUrl}
              loadingStep={trackingStep}
            />
          </div>
        </section>

        {/* Dashboard Grid Header: Filter & Sort Ribbon */}
        <section className="space-y-6">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-xl font-extrabold text-white flex items-center space-x-2.5">
                <span>Tracked Products Dashboard</span>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 font-bold border border-slate-700">
                  {filteredProducts.length}
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Real-time alerts, integrity scores, and price histories</p>
            </div>

            {/* Controls: Search, Filter Tabs & Sort */}
            <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
              {/* Search Bar */}
              <div className="relative flex-1 sm:w-48">
                <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter products..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:border-emerald-500 outline-none"
                />
              </div>

              {/* Filter Tabs */}
              <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
                <button
                  onClick={() => setSelectedFilter('ALL')}
                  className={`px-3 py-1 rounded-lg transition ${selectedFilter === 'ALL' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  All
                </button>
                <button
                  onClick={() => setSelectedFilter('BUY NOW')}
                  className={`px-3 py-1 rounded-lg transition flex items-center space-x-1 ${selectedFilter === 'BUY NOW' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  <Flame className="h-3 w-3" />
                  <span>Buy Now</span>
                </button>
                <button
                  onClick={() => setSelectedFilter('WAIT')}
                  className={`px-3 py-1 rounded-lg transition flex items-center space-x-1 ${selectedFilter === 'WAIT' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  <Clock className="h-3 w-3" />
                  <span>Wait</span>
                </button>
                <button
                  onClick={() => setSelectedFilter('HIGH_INTEGRITY')}
                  className={`px-3 py-1 rounded-lg transition flex items-center space-x-1 ${selectedFilter === 'HIGH_INTEGRITY' ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  <ShieldCheck className="h-3 w-3" />
                  <span>90%+ Integrity</span>
                </button>
              </div>

              {/* Sort dropdown */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 font-medium outline-none focus:border-emerald-500"
              >
                <option value="DEFAULT">Sort: Default</option>
                <option value="SAVINGS">Sort: Highest Savings</option>
                <option value="INTEGRITY">Sort: Deal Integrity</option>
                <option value="PRICE_ASC">Sort: Price Low → High</option>
                <option value="PRICE_DESC">Sort: Price High → Low</option>
              </select>

              {/* Refresh button */}
              <button
                onClick={fetchProducts}
                className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition"
                title="Refresh products"
              >
                <RefreshCw className={`h-4 w-4 ${isLoadingProducts ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Cards Grid */}
          {isLoadingProducts ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map(n => (
                <div key={n} className="h-80 rounded-2xl bg-slate-900/60 border border-slate-800 animate-pulse" />
              ))}
            </div>
          ) : filteredProducts.length === 0 ? (
            <div className="py-16 text-center glass-panel rounded-3xl border border-slate-800 space-y-3">
              <div className="h-12 w-12 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto text-slate-500">
                <Search className="h-6 w-6" />
              </div>
              <h3 className="text-base font-bold text-white">No tracked items found</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Paste an Amazon, eBay, or Best Buy link above or click one of the quick test chips to begin tracking.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredProducts.map(product => (
                <ProductCard
                  key={product.id}
                  product={product}
                  onInspect={(prod) => setSelectedProduct(prod)}
                  onSimulateDrop={handleSimulateDrop}
                  onDelete={handleDeleteProduct}
                />
              ))}
            </div>
          )}
        </section>

      </main>

      {/* Footer */}
      <footer className="w-full border-t border-slate-800/80 glass-panel py-6 text-xs text-slate-400 text-center">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-slate-200">SmartPrice AI</span>
            <span>•</span>
            <span>Google Gemini API Architecture</span>
          </div>
          <div className="flex items-center space-x-4 text-slate-400">
            <span>AWS Amplify & DynamoDB Ready</span>
            <span>•</span>
            <span>7 Architectural Pillars Resilient Engine</span>
          </div>
        </div>
      </footer>

      {/* Product Detail Modal */}
      {selectedProduct && (
        <ProductDetailModal
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
          onUpdateAlerts={handleUpdateAlerts}
          onSimulateDrop={handleSimulateDrop}
        />
      )}

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      {/* Price Drop Toast Notification */}
      {activeToast && (
        <AlertNotificationToast
          notification={activeToast}
          onDismiss={() => setActiveToast(null)}
        />
      )}

    </div>
  );
}
