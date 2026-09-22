import React from 'react';
import { Zap, X, Bell, Flame } from 'lucide-react';

export default function AlertNotificationToast({ notification, onDismiss }) {
  if (!notification) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 max-w-md w-full animate-bounce-short">
      <div className="p-4 rounded-2xl glass-panel border border-emerald-500/50 shadow-2xl shadow-emerald-500/20 bg-dark-900/95 backdrop-blur-xl flex items-start space-x-3">
        <div className="p-2.5 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-500 text-slate-950 font-black shadow-lg">
          <Flame className="h-5 w-5 fill-current" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-extrabold uppercase tracking-wider text-emerald-400 flex items-center space-x-1">
              <Zap className="h-3 w-3 fill-current" />
              <span>Price Alert Triggered!</span>
            </span>
            <button
              onClick={onDismiss}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <h4 className="text-xs font-bold text-white mt-1 line-clamp-1">
            {notification.title}
          </h4>

          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-base font-black text-emerald-400">
              ₹{notification.new_price?.toLocaleString('en-IN')}
            </span>
            {notification.old_price && (
              <span className="text-xs text-slate-400 line-through">
                ₹{notification.old_price?.toLocaleString('en-IN')}
              </span>
            )}
            {notification.savings > 0 && (
              <span className="text-[11px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                Save ₹{notification.savings?.toLocaleString('en-IN')}
              </span>
            )}
          </div>

          <p className="text-[11px] text-slate-300 mt-1">
            Price dropped below your target threshold! Recommended action: <strong className="text-emerald-400">BUY NOW</strong>.
          </p>
        </div>
      </div>
    </div>
  );
}
