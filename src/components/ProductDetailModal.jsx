import React, { useState, useMemo } from 'react';
import { 
  X, 
  Sparkles, 
  ShieldCheck, 
  TrendingDown, 
  TrendingUp, 
  Check, 
  AlertCircle, 
  ExternalLink, 
  Bell, 
  Send, 
  MessageSquare, 
  Loader2, 
  Zap, 
  Flame, 
  Clock, 
  AlertTriangle,
  ThumbsUp,
  ThumbsDown,
  Info
} from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');

export default function ProductDetailModal({ 
  product, 
  onClose, 
  onUpdateAlerts, 
  onSimulateDrop
}) {
  if (!product) return null;

  const [activeTab, setActiveTab] = useState('chart'); // 'chart' | 'advisor' | 'alerts'
  const [targetPrice, setTargetPrice] = useState(product.target_price || product.current_price * 0.9);
  const [alertEnabled, setAlertEnabled] = useState(product.alert_enabled ?? true);
  const [alertEmail, setAlertEmail] = useState(product.alert_email || '');
  const [isSavingAlert, setIsSavingAlert] = useState(false);
  const [alertSavedSuccess, setAlertSavedSuccess] = useState(false);
  const [hoveredPoint, setHoveredPoint] = useState(null);

  // Natural Language Advisor Chat state
  const [userQuestion, setUserQuestion] = useState('');
  const [isAskingAdvisor, setIsAskingAdvisor] = useState(false);
  const [advisorResponses, setAdvisorResponses] = useState([]);
  const [advisorError, setAdvisorError] = useState('');

  const verdict = product?.verdict_data?.verdict || 'WAIT';
  const integrity = product?.verdict_data?.deal_integrity_score ?? 85;
  const rationale = product?.verdict_data?.rationale || 'Price is currently fluctuating within seasonal norms.';
  const pros = product?.verdict_data?.pros || [
    'Competitive market pricing',
    'High customer satisfaction score',
    'Verified seller reliability'
  ];
  const cons = product?.verdict_data?.cons || [
    'Seasonal price promotions may occur soon',
    'Alternative models available'
  ];
  const prediction = product?.verdict_data?.price_trend_prediction || 'Stable price';

  const history = product.price_history || [
    { day: '30d ago', price: product.current_price * 1.15 },
    { day: '20d ago', price: product.current_price * 1.1 },
    { day: '10d ago', price: product.current_price * 1.05 },
    { day: 'Today', price: product.current_price }
  ];

  // Helper to format clean day labels (e.g. "Day -30" -> "30d ago", "Today" -> "Today")
  const formatDayLabel = (label) => {
    if (!label) return '';
    const str = String(label).trim();
    const match = str.match(/^Day\s*-?(\d+)$/i);
    if (match) {
      const num = parseInt(match[1], 10);
      if (num === 0) return 'Today';
      if (num === 1) return 'Yesterday';
      return `${num}d ago`;
    }
    if (/^today$/i.test(str)) return 'Today';
    if (/^yesterday$/i.test(str)) return 'Yesterday';
    return str.replace(/\s*days?\s*ago/i, 'd ago');
  };

  // Price calculations for chart
  const prices = history.map(h => h.price);
  const minPrice = Math.min(...prices, targetPrice || 0);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice || 1;

  // Chart coordinate mapping
  const chartHeight = 160;
  const chartWidth = 520;
  const points = history.map((item, idx) => {
    const x = (idx / (history.length - 1 || 1)) * (chartWidth - 60) + 30;
    const y = chartHeight - 30 - ((item.price - minPrice) / priceRange) * (chartHeight - 60);
    return { x, y, day: item.day, price: item.price };
  });

  // Sampled milestone ticks for X axis to ensure clean non-overlapping labels
  const xAxisTicks = useMemo(() => {
    if (!points || points.length === 0) return [];
    if (points.length <= 4) {
      return points.map((pt, idx) => ({
        ...pt,
        align: idx === 0 ? 'start' : idx === points.length - 1 ? 'end' : 'middle'
      }));
    }
    const count = points.length;
    // Pick 4 evenly spaced milestone ticks: 0, 33%, 67%, 100%
    const indices = [
      0,
      Math.round((count - 1) * 0.33),
      Math.round((count - 1) * 0.67),
      count - 1
    ];
    const uniqueIndices = Array.from(new Set(indices)).sort((a, b) => a - b);
    return uniqueIndices.map((idx, i) => ({
      ...points[idx],
      align: i === 0 ? 'start' : i === uniqueIndices.length - 1 ? 'end' : 'middle'
    }));
  }, [points]);

  const pathD = points.reduce((acc, pt, idx) => 
    idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`, ''
  );

  const targetY = targetPrice 
    ? chartHeight - 30 - ((targetPrice - minPrice) / priceRange) * (chartHeight - 60) 
    : null;

  // Handle saving alert settings
  const handleSaveAlerts = async () => {
    setIsSavingAlert(true);
    try {
      await onUpdateAlerts(product.id, {
        target_price: parseFloat(targetPrice),
        alert_enabled: alertEnabled,
        alert_email: alertEmail
      });
      setAlertSavedSuccess(true);
      setTimeout(() => setAlertSavedSuccess(false), 2500);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSavingAlert(false);
    }
  };

  // Handle Natural Language Advisor query
  const handleAskAdvisor = async (promptQuery) => {
    const query = promptQuery || userQuestion;
    if (!query.trim()) return;

    setIsAskingAdvisor(true);
    setAdvisorError('');

    try {
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          question: query,
          product_title: product.title,
          current_price: product.current_price,
          currency: product.currency || '₹',
          merchant: product.merchant || 'Store',
          verdict_data: product.verdict_data
        })
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Error from AI advisor');

      setAdvisorResponses(prev => [
        {
          question: query,
          answer: data.advice.answer,
          recommendation: data.advice.recommendation,
          confidence: data.advice.confidence,
          key_takeaway: data.advice.key_takeaway,
          model_used: data.metadata?.model_used,
          source: data.metadata?.source
        },
        ...prev
      ]);
      setUserQuestion('');
    } catch (err) {
      setAdvisorError(err.message);
    } finally {
      setIsAskingAdvisor(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-dark-900 rounded-3xl border border-slate-700/80 shadow-2xl overflow-hidden my-6 max-h-[92vh] flex flex-col">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-dark-950/70">
          <div className="flex items-center space-x-3">
            <span className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Sparkles className="h-5 w-5" />
            </span>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs uppercase font-bold text-slate-400 tracking-wider">Product Intelligence</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-semibold">{product.merchant}</span>
              </div>
              <h2 className="text-base sm:text-lg font-bold text-white line-clamp-1 max-w-xl">{product.title}</h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Tabs Navigation */}
        <div className="px-6 border-b border-slate-800 bg-slate-900/40 flex space-x-2 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('chart')}
            className={`py-3 px-4 border-b-2 transition flex items-center space-x-1.5 ${
              activeTab === 'chart' 
                ? 'border-emerald-400 text-emerald-400' 
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <TrendingDown className="h-4 w-4" />
            <span>Price Trend & Gemini Verdict</span>
          </button>

          <button
            onClick={() => setActiveTab('advisor')}
            className={`py-3 px-4 border-b-2 transition flex items-center space-x-1.5 ${
              activeTab === 'advisor' 
                ? 'border-indigo-400 text-indigo-400' 
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="h-4 w-4" />
            <span>Ask AI Advisor ("Should I buy?")</span>
            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-indigo-500/20 text-indigo-300">Natural Language</span>
          </button>

          <button
            onClick={() => setActiveTab('alerts')}
            className={`py-3 px-4 border-b-2 transition flex items-center space-x-1.5 ${
              activeTab === 'alerts' 
                ? 'border-emerald-400 text-emerald-400' 
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Bell className="h-4 w-4" />
            <span>Alert Settings & Simulation</span>
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-200 text-sm">
          
          {/* TAB 1: CHART & AI VERDICT */}
          {activeTab === 'chart' && (
            <>
              {/* Top Verdict Highlight Banner */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* AI Verdict Card */}
                <div className={`p-4 rounded-2xl border flex flex-col justify-between ${
                  verdict === 'BUY NOW' 
                    ? 'bg-emerald-950/30 border-emerald-500/30 glow-emerald' 
                    : verdict === 'WAIT'
                    ? 'bg-amber-950/30 border-amber-500/30 glow-amber'
                    : 'bg-rose-950/30 border-rose-500/30 glow-risky'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase font-bold tracking-wider text-slate-400">Gemini Verdict</span>
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-white/10 text-white font-medium">gemini-1.5-flash</span>
                  </div>
                  <div className="my-2">
                    <span className={`text-2xl font-black ${
                      verdict === 'BUY NOW' ? 'text-emerald-400' : verdict === 'WAIT' ? 'text-amber-400' : 'text-rose-400'
                    }`}>
                      {verdict}
                    </span>
                    <p className="text-xs text-slate-300 mt-1 font-medium">{prediction}</p>
                  </div>
                  <div className="text-[11px] text-slate-400 pt-2 border-t border-white/10">
                    Recommended Buy Target: <strong className="text-white">{product.currency || '₹'}{(product.verdict_data?.recommended_target_price || product.target_price)?.toLocaleString('en-IN')}</strong>
                  </div>
                </div>

                {/* Deal Integrity Meter */}
                <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase font-bold tracking-wider text-slate-400">Deal Integrity</span>
                    <ShieldCheck className="h-4 w-4 text-indigo-400" />
                  </div>
                  <div className="my-2">
                    <div className="flex items-baseline space-x-1">
                      <span className="text-3xl font-black text-white">{integrity}%</span>
                      <span className="text-xs font-semibold text-emerald-400">
                        {integrity >= 80 ? 'Genuine Markdown' : integrity >= 60 ? 'Fair Value' : 'Inflated MSRP'}
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full mt-2 overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${integrity >= 80 ? 'bg-emerald-400' : integrity >= 60 ? 'bg-amber-400' : 'bg-rose-400'}`} 
                        style={{ width: `${integrity}%` }}
                      />
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-400">Analyzed against retailer pricing cycles & fake discount filters.</p>
                </div>

                {/* Current vs Historic Snapshot */}
                <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between">
                  <span className="text-xs uppercase font-bold tracking-wider text-slate-400">Current Pricing</span>
                  <div className="my-2">
                    <div className="text-3xl font-black text-white">
                      {product.currency || '₹'}{product.current_price?.toLocaleString('en-IN')}
                    </div>
                    {product.original_price && (
                      <span className="text-xs text-slate-400 line-through">
                        Original MSRP: {product.currency || '₹'}{product.original_price?.toLocaleString('en-IN')}
                      </span>
                    )}
                  </div>
                  <a
                    href={product.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] font-semibold text-emerald-400 hover:text-emerald-300 flex items-center space-x-1"
                  >
                    <span>View on {product.merchant || 'Store'}</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </div>

              {/* Rationale Digest */}
              <div className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center space-x-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Gemini AI Rationale & Sale Cycle Timing</span>
                </h4>
                <p className="text-sm text-slate-200 leading-relaxed font-normal">
                  {rationale}
                </p>
              </div>

              {/* Interactive Price History Chart */}
              <div className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h4 className="text-sm font-bold text-white flex items-center space-x-2">
                      <span>Price History & Trendline</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">30-Day Tracking</span>
                    </h4>
                    <p className="text-xs text-slate-400">Green line indicates price movement; dashed yellow line marks your alert threshold.</p>
                  </div>
                  <div className="flex items-center space-x-3 text-xs">
                    <span className="text-slate-400">Low: <strong className="text-emerald-400">{product.currency || '₹'}{Math.round(minPrice).toLocaleString('en-IN')}</strong></span>
                    <span className="text-slate-400">High: <strong className="text-rose-400">{product.currency || '₹'}{Math.round(maxPrice).toLocaleString('en-IN')}</strong></span>
                  </div>
                </div>

                {/* SVG Line Chart */}
                <div className="w-full overflow-x-auto">
                  <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-44 overflow-visible">
                    <defs>
                      <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    {/* Grid lines */}
                    <line x1="20" y1="30" x2={chartWidth - 10} y2="30" stroke="#334155" strokeWidth="0.5" strokeDasharray="3 3" />
                    <line x1="20" y1={chartHeight / 2} x2={chartWidth - 10} y2={chartHeight / 2} stroke="#334155" strokeWidth="0.5" strokeDasharray="3 3" />
                    <line x1="20" y1={chartHeight - 30} x2={chartWidth - 10} y2={chartHeight - 30} stroke="#334155" strokeWidth="1" />

                    {/* Milestone X-Axis Ticks & Clean Labels */}
                    {xAxisTicks.map((tick, i) => (
                      <g key={`xtick-${i}`}>
                        <line
                          x1={tick.x}
                          y1={chartHeight - 30}
                          x2={tick.x}
                          y2={chartHeight - 24}
                          stroke="#475569"
                          strokeWidth="1.5"
                        />
                        <text
                          x={tick.x}
                          y={chartHeight - 10}
                          textAnchor={tick.align}
                          fill="#94a3b8"
                          fontSize="10"
                          fontWeight="500"
                          className="select-none font-medium"
                        >
                          {formatDayLabel(tick.day)}
                        </text>
                      </g>
                    ))}

                    {/* Target Price Threshold Dashed Line */}
                    {targetY && (
                      <g>
                        <line
                          x1="20"
                          y1={targetY}
                          x2={chartWidth - 10}
                          y2={targetY}
                          stroke="#f59e0b"
                          strokeWidth="1.5"
                          strokeDasharray="4 4"
                        />
                        <text x={chartWidth - 85} y={targetY - 5} fill="#f59e0b" fontSize="9" fontWeight="bold">
                          Target {product.currency || '₹'}{Math.round(targetPrice || 0).toLocaleString('en-IN')}
                        </text>
                      </g>
                    )}

                    {/* Area under curve */}
                    {points.length > 0 && (
                      <path
                        d={`${pathD} L ${points[points.length - 1].x} ${chartHeight - 30} L ${points[0].x} ${chartHeight - 30} Z`}
                        fill="url(#chartGradient)"
                      />
                    )}

                    {/* Line path */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />

                    {/* Vertical Hover Crosshair Guide Line */}
                    {hoveredPoint && (
                      <line
                        x1={hoveredPoint.x}
                        y1="25"
                        x2={hoveredPoint.x}
                        y2={chartHeight - 30}
                        stroke="#34d399"
                        strokeWidth="1.5"
                        strokeDasharray="3 3"
                        opacity="0.6"
                      />
                    )}

                    {/* Data Points on the line */}
                    {points.map((pt, i) => {
                      const isLast = i === points.length - 1;
                      const isHovered = hoveredPoint === pt;
                      const manyPoints = points.length > 8;

                      return (
                        <g key={i} className="cursor-pointer">
                          {/* Standout Glowing Ring for Latest Point (Today) */}
                          {isLast && (
                            <circle
                              cx={pt.x}
                              cy={pt.y}
                              r={8}
                              className="fill-emerald-500/30 animate-pulse pointer-events-none"
                            />
                          )}

                          {/* Data point dot */}
                          {(!manyPoints || isLast || isHovered) ? (
                            <circle
                              cx={pt.x}
                              cy={pt.y}
                              r={isHovered ? 5.5 : isLast ? 4.5 : 3.5}
                              className={`${
                                isHovered
                                  ? 'fill-emerald-300 stroke-white stroke-2'
                                  : isLast
                                  ? 'fill-emerald-400 stroke-white stroke-2'
                                  : 'fill-slate-900 stroke-emerald-400 stroke-2'
                              } transition-all pointer-events-none`}
                            />
                          ) : (
                            <circle
                              cx={pt.x}
                              cy={pt.y}
                              r={1.5}
                              className="fill-emerald-400/40 pointer-events-none"
                            />
                          )}

                          {/* Invisible wider hover hit target */}
                          <circle
                            cx={pt.x}
                            cy={pt.y}
                            r={14}
                            fill="transparent"
                            onMouseEnter={() => setHoveredPoint(pt)}
                            onMouseLeave={() => setHoveredPoint(null)}
                          />
                        </g>
                      );
                    })}

                    {/* Floating Tooltip Card */}
                    {hoveredPoint && (
                      <g
                        transform={`translate(${Math.min(Math.max(hoveredPoint.x, 48), chartWidth - 48)}, ${Math.max(22, hoveredPoint.y - 28)})`}
                        className="pointer-events-none"
                      >
                        <rect
                          x="-45"
                          y="-20"
                          width="90"
                          height="34"
                          rx="6"
                          fill="#0b1324"
                          stroke="#10b981"
                          strokeWidth="1.2"
                        />
                        <text
                          x="0"
                          y="-7"
                          textAnchor="middle"
                          fill="#94a3b8"
                          fontSize="9"
                          fontWeight="500"
                        >
                          {formatDayLabel(hoveredPoint.day)}
                        </text>
                        <text
                          x="0"
                          y="8"
                          textAnchor="middle"
                          fill="#34d399"
                          fontSize="11"
                          fontWeight="bold"
                        >
                          {product.currency || '₹'}{Math.round(hoveredPoint.price).toLocaleString('en-IN')}
                        </text>
                      </g>
                    )}
                  </svg>
                </div>
              </div>

              {/* Pros & Cons 3-Bullet Summary */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Pros */}
                <div className="p-4 rounded-2xl bg-emerald-950/20 border border-emerald-900/40">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400 mb-3 flex items-center space-x-1.5">
                    <ThumbsUp className="h-4 w-4" />
                    <span>Top Verified Pros (From Reviews)</span>
                  </h4>
                  <ul className="space-y-2">
                    {pros.map((pro, i) => (
                      <li key={i} className="text-xs text-slate-300 flex items-start space-x-2">
                        <Check className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0 mt-0.5" />
                        <span>{pro}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Cons */}
                <div className="p-4 rounded-2xl bg-rose-950/20 border border-rose-900/40">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400 mb-3 flex items-center space-x-1.5">
                    <ThumbsDown className="h-4 w-4" />
                    <span>Potential Drawbacks</span>
                  </h4>
                  <ul className="space-y-2">
                    {cons.map((con, i) => (
                      <li key={i} className="text-xs text-slate-300 flex items-start space-x-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-rose-400 flex-shrink-0 mt-0.5" />
                        <span>{con}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </>
          )}

          {/* TAB 2: NATURAL LANGUAGE AI ADVISOR */}
          {activeTab === 'advisor' && (
            <div className="space-y-5">
              <div className="p-4 rounded-2xl bg-indigo-950/30 border border-indigo-800/40">
                <div className="flex items-start space-x-3">
                  <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400">
                    <MessageSquare className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">Ask Anything in Natural Language</h3>
                    <p className="text-xs text-slate-300 mt-1">
                      Ask questions like <em>"Should I buy it now or wait for Black Friday?"</em>, <em>"Is this discount genuine?"</em>, or <em>"Is it good for gaming?"</em>.
                      Powered by the heavy model chain with real-time deal grounding.
                    </p>
                  </div>
                </div>
              </div>

              {/* Quick Prompt Chips */}
              <div className="flex flex-wrap gap-2 text-xs">
                {[
                  "Should I buy it now or wait?",
                  "Is this discount genuine or inflated?",
                  "Will the price drop further in 30 days?",
                  "Are there recurring issues in customer reviews?"
                ].map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => handleAskAdvisor(chip)}
                    disabled={isAskingAdvisor}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-700 transition"
                  >
                    "{chip}"
                  </button>
                ))}
              </div>

              {/* Chat Input */}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={userQuestion}
                  onChange={(e) => setUserQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAskAdvisor();
                  }}
                  disabled={isAskingAdvisor}
                  placeholder="e.g. Should I buy this now or wait for a price drop?"
                  className="flex-1 px-4 py-3 rounded-xl bg-dark-950 border border-slate-700 text-white placeholder-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none text-sm"
                />
                <button
                  onClick={() => handleAskAdvisor()}
                  disabled={isAskingAdvisor || !userQuestion.trim()}
                  className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition flex items-center space-x-2 disabled:opacity-50"
                >
                  {isAskingAdvisor ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      <span>Ask AI</span>
                    </>
                  )}
                </button>
              </div>

              {advisorError && (
                <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/40 text-xs text-rose-300">
                  {advisorError}
                </div>
              )}

              {/* Chat Responses History */}
              <div className="space-y-4">
                {advisorResponses.map((res, idx) => (
                  <div key={idx} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-300">Q: "{res.question}"</span>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                          res.recommendation === 'BUY NOW' ? 'bg-emerald-500/20 text-emerald-400' :
                          res.recommendation === 'WAIT' ? 'bg-amber-500/20 text-amber-400' : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {res.recommendation}
                        </span>
                        <span className="text-slate-500 text-[10px]">Confidence: {res.confidence}%</span>
                      </div>
                    </div>

                    <p className="text-sm text-slate-100 leading-relaxed">
                      {res.answer}
                    </p>

                    {res.key_takeaway && (
                      <div className="p-2.5 rounded-lg bg-dark-950 border border-slate-800 text-xs text-indigo-300 font-medium">
                        💡 <strong>Takeaway:</strong> {res.key_takeaway}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: ALERT SETTINGS & SIMULATION */}
          {activeTab === 'alerts' && (
            <div className="space-y-6">
              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                  <Bell className="h-4 w-4 text-emerald-400" />
                  <span>Price Drop Notification Settings</span>
                </h3>

                {/* Target Price Input */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Notify me when price drops below:
                  </label>
                  <div className="relative max-w-xs">
                    <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-400 font-bold">{product.currency || '₹'}</span>
                    <input
                      type="number"
                      step="1"
                      value={targetPrice}
                      onChange={(e) => setTargetPrice(e.target.value)}
                      className="w-full pl-8 pr-4 py-2.5 rounded-xl bg-dark-950 border border-slate-700 text-white font-bold focus:border-emerald-500 outline-none"
                    />
                  </div>
                  <span className="text-[11px] text-slate-400 mt-1 block">
                    Current: {product.currency || '₹'}{product.current_price?.toLocaleString('en-IN')} | Recommended target: {product.currency || '₹'}{(product.verdict_data?.recommended_target_price || (product.current_price * 0.9))?.toLocaleString('en-IN')}
                  </span>
                </div>

                {/* Email Alert Toggle */}
                <div className="pt-3 border-t border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-white block">Email Alerts</span>
                      <span className="text-[11px] text-slate-400">Receive instant alerts when the deal hits your target.</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setAlertEnabled(!alertEnabled)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${alertEnabled ? 'bg-emerald-500' : 'bg-slate-700'}`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${alertEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
                    </button>
                  </div>

                  {alertEnabled && (
                    <input
                      type="email"
                      value={alertEmail}
                      onChange={(e) => setAlertEmail(e.target.value)}
                      placeholder="shopper@example.com"
                      className="w-full max-w-sm px-3.5 py-2 rounded-xl bg-dark-950 border border-slate-700 text-white text-xs placeholder-slate-500 outline-none focus:border-emerald-500"
                    />
                  )}
                </div>

                <div className="pt-2 flex items-center space-x-3">
                  <button
                    onClick={handleSaveAlerts}
                    disabled={isSavingAlert}
                    className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition flex items-center space-x-2"
                  >
                    {isSavingAlert ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                    <span>Save Alert Settings</span>
                  </button>
                  {alertSavedSuccess && (
                    <span className="text-xs text-emerald-400 font-semibold animate-pulse">
                      Settings updated successfully!
                    </span>
                  )}
                </div>
              </div>

              {/* Price Drop Simulation Testing */}
              <div className="p-5 rounded-2xl bg-indigo-950/30 border border-indigo-800/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                      <Zap className="h-4 w-4 text-indigo-400" />
                      <span>Simulate Real-time Price Drop</span>
                    </h3>
                    <p className="text-xs text-slate-300 mt-0.5">
                      Simulate a 15% retail flash sale to test alert notifications and trigger immediate Gemini AI re-evaluation.
                    </p>
                  </div>
                  <button
                    onClick={() => onSimulateDrop(product.id)}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition shadow-lg shadow-indigo-500/25 flex items-center space-x-1.5"
                  >
                    <Zap className="h-3.5 w-3.5" />
                    <span>Drop Price Now</span>
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-dark-950/70 flex items-center justify-between text-xs text-slate-400">
          <span>SmartPrice AI Deal Intelligence</span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium transition"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
