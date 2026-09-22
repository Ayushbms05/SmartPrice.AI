import React from 'react';
import { 
  ShieldCheck, 
  TrendingDown, 
  TrendingUp, 
  Clock, 
  ExternalLink, 
  Sparkles, 
  Trash2, 
  Zap,
  CheckCircle2,
  AlertTriangle,
  Flame,
  ArrowDownRight
} from 'lucide-react';

export default function ProductCard({ 
  product, 
  onInspect, 
  onSimulateDrop, 
  onDelete 
}) {
  const verdict = product?.verdict_data?.verdict || 'WAIT';
  const integrity = product?.verdict_data?.deal_integrity_score ?? 85;
  const rationale = product?.verdict_data?.rationale || 'Price is currently fluctuating within seasonal norms.';
  
  // Format relative time
  const formatTime = (timestamp) => {
    if (!timestamp) return 'Just now';
    const diff = Math.floor((Date.now() / 1000) - timestamp);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  // Verdict color schemes
  const getVerdictStyle = () => {
    switch (verdict.toUpperCase()) {
      case 'BUY NOW':
        return {
          bg: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40 glow-emerald',
          dot: 'bg-emerald-400',
          icon: Flame,
          label: 'BUY NOW',
          colorText: 'text-emerald-400'
        };
      case 'WAIT':
        return {
          bg: 'bg-amber-500/15 text-amber-300 border-amber-500/40 glow-amber',
          dot: 'bg-amber-400',
          icon: Clock,
          label: 'WAIT FOR DROP',
          colorText: 'text-amber-400'
        };
      case 'RISKY':
      default:
        return {
          bg: 'bg-rose-500/15 text-rose-300 border-rose-500/40 glow-risky',
          dot: 'bg-rose-400',
          icon: AlertTriangle,
          label: 'RISKY / INFLATED',
          colorText: 'text-rose-400'
        };
    }
  };

  const style = getVerdictStyle();
  const VerdictIcon = style.icon;

  const originalPrice = product.original_price;
  const currentPrice = product.current_price;
  const discountPercent = originalPrice && originalPrice > currentPrice 
    ? Math.round(((originalPrice - currentPrice) / originalPrice) * 100) 
    : 0;

  const targetMet = product.target_price && currentPrice <= product.target_price;

  return (
    <div className="group relative flex flex-col rounded-2xl glass-card overflow-hidden transition-all duration-300 hover:shadow-2xl hover:-translate-y-1">
      {/* Target Price Reached Banner */}
      {targetMet && (
        <div className="bg-gradient-to-r from-emerald-600 to-teal-600 text-slate-950 font-bold text-xs py-1 px-3 flex items-center justify-center space-x-1.5 shadow">
          <Zap className="h-3.5 w-3.5 fill-current" />
          <span>TARGET PRICE HIT! ({product.currency || '₹'}{product.current_price?.toLocaleString('en-IN')})</span>
        </div>
      )}

      {/* Top Media & Store Section */}
      <div className="relative h-48 w-full bg-slate-950/60 overflow-hidden flex items-center justify-center p-4">
        <img
          src={product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'}
          alt={product.title}
          className="max-h-full max-w-full object-contain group-hover:scale-105 transition duration-500"
          loading="lazy"
          onError={(e) => {
            e.target.src = 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80';
          }}
        />

        {/* Store Merchant Badge */}
        <div className="absolute top-3 left-3 px-2.5 py-1 rounded-lg bg-slate-900/90 backdrop-blur-md border border-slate-700/80 text-[11px] font-semibold text-slate-300 flex items-center space-x-1.5 shadow-md">
          <span>{product.merchant || 'Store'}</span>
        </div>

        {/* AI Verdict Badge */}
        <div className={`absolute top-3 right-3 px-3 py-1 rounded-lg border text-xs font-black tracking-wider flex items-center space-x-1.5 shadow-lg backdrop-blur-md ${style.bg}`}>
          <VerdictIcon className="h-3.5 w-3.5" />
          <span>{style.label}</span>
        </div>

        {/* Discount Tag */}
        {discountPercent > 0 && (
          <div className="absolute bottom-3 left-3 px-2 py-0.5 rounded-md bg-emerald-500 text-slate-950 text-xs font-extrabold flex items-center space-x-1">
            <ArrowDownRight className="h-3.5 w-3.5" />
            <span>-{discountPercent}%</span>
          </div>
        )}
      </div>

      {/* Body Information */}
      <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
        <div>
          {/* Title */}
          <h3 
            className="text-sm font-semibold text-white line-clamp-2 hover:text-emerald-400 transition cursor-pointer"
            onClick={() => onInspect(product)}
            title={product.title}
          >
            {product.title}
          </h3>

          {/* Pricing Row */}
          <div className="mt-3 flex items-baseline justify-between">
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-black text-white tracking-tight">
                {product.currency || '₹'}{product.current_price?.toLocaleString('en-IN')}
              </span>
              {originalPrice && originalPrice > currentPrice && (
                <span className="text-xs text-slate-400 line-through font-normal">
                  {product.currency || '₹'}{originalPrice.toLocaleString('en-IN')}
                </span>
              )}
            </div>

            {/* Target Price Status */}
            <div className="text-right">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 block">Target</span>
              <span className={`text-xs font-bold ${targetMet ? 'text-emerald-400 font-extrabold' : 'text-slate-300'}`}>
                {product.currency || '₹'}{product.target_price ? product.target_price.toLocaleString('en-IN') : '--'}
              </span>
            </div>
          </div>

          {/* Deal Integrity Meter */}
          <div className="mt-4 p-2.5 rounded-xl bg-slate-900/70 border border-slate-800/80">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-slate-400 flex items-center space-x-1 font-medium">
                <ShieldCheck className="h-3.5 w-3.5 text-indigo-400" />
                <span>Deal Integrity</span>
              </span>
              <span className={`font-bold ${integrity >= 80 ? 'text-emerald-400' : integrity >= 60 ? 'text-amber-400' : 'text-rose-400'}`}>
                {integrity}% {integrity >= 80 ? 'Genuine' : integrity >= 60 ? 'Moderate' : 'Inflated MSRP'}
              </span>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${
                  integrity >= 80 ? 'bg-emerald-400' : integrity >= 60 ? 'bg-amber-400' : 'bg-rose-400'
                }`} 
                style={{ width: `${Math.min(100, Math.max(5, integrity))}%` }}
              />
            </div>
          </div>

          {/* AI Rationale Snippet */}
          <p className="mt-3 text-xs text-slate-300/90 line-clamp-2 leading-relaxed italic border-l-2 border-slate-700 pl-2.5">
            "{rationale}"
          </p>
        </div>

        {/* Footer Meta & Quick Actions */}
        <div className="pt-3 border-t border-slate-800/70 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-1 text-[11px]">
            <Clock className="h-3.5 w-3.5 text-slate-500" />
            <span>{formatTime(product.last_updated)}</span>
          </div>

          <div className="flex items-center space-x-1">
            {/* Simulate Drop Button */}
            <button
              onClick={() => onSimulateDrop(product.id)}
              className="px-2.5 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 transition flex items-center space-x-1 text-[11px] font-medium"
              title="Simulate 15% price drop to test alerts"
            >
              <Zap className="h-3 w-3" />
              <span>Simulate Drop</span>
            </button>

            {/* Inspect Modal Button */}
            <button
              onClick={() => onInspect(product)}
              className="px-3 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition flex items-center space-x-1 text-[11px] font-semibold"
            >
              <Sparkles className="h-3 w-3" />
              <span>Inspect</span>
            </button>

            {/* Delete button */}
            <button
              onClick={() => onDelete(product.id)}
              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition"
              title="Stop tracking product"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
