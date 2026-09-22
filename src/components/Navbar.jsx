import React from 'react';
import { Sparkles, Settings, ShieldCheck, Activity, BellRing } from 'lucide-react';

export default function Navbar({ onOpenSettings, trackedCount = 0, totalSavings = 0 }) {
  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 ring-1 ring-white/20">
            <Sparkles className="h-5 w-5 text-white animate-pulse-subtle" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                SmartPrice<span className="text-emerald-400">.AI</span>
              </span>
              <span className="hidden sm:inline-flex text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                Gemini 1.5 Flash
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">Intelligent Price Tracking & Deal Verdicts</p>
          </div>
        </div>

        {/* Center: Live Stats Ribbon */}
        <div className="hidden md:flex items-center space-x-6 text-xs text-slate-300">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800">
            <Activity className="h-4 w-4 text-indigo-400" />
            <span>Tracked: <strong className="text-white font-semibold">{trackedCount}</strong></span>
          </div>

          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>Avg Deal Integrity: <strong className="text-emerald-400 font-semibold">92%</strong></span>
          </div>

          {totalSavings > 0 && (
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-emerald-300">
              <BellRing className="h-4 w-4 text-emerald-400" />
              <span>Potential Savings: <strong className="text-white font-semibold">₹{Math.round(totalSavings).toLocaleString('en-IN')}</strong></span>
            </div>
          )}
        </div>

        {/* Right Actions */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onOpenSettings}
            className="group flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-750 text-slate-200 hover:text-white border border-slate-700/80 transition shadow-sm"
            title="View Architecture & Engine Diagnostics"
          >
            <Settings className="h-4 w-4 text-slate-400 group-hover:text-emerald-400 transition" />
            <span className="text-xs font-medium">Architecture & Diagnostics</span>
            <span className="h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-emerald-400/20" title="Engine Active" />
          </button>
        </div>
      </div>
    </header>
  );
}
