import React, { useState, useEffect } from 'react';
import { 
  X, 
  Check, 
  ShieldCheck, 
  Activity, 
  Cpu, 
  FileText, 
  RefreshCw,
  Sliders,
  Lock
} from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');

export default function SettingsModal({ 
  isOpen, 
  onClose 
}) {
  if (!isOpen) return null;

  const [systemStatus, setSystemStatus] = useState(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(false);

  const fetchStatus = async () => {
    setIsLoadingStatus(true);
    try {
      const res = await fetch(`${API_BASE}/api/status`);
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingStatus(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-dark-900 rounded-3xl border border-slate-700 shadow-2xl overflow-hidden my-6 max-h-[90vh] flex flex-col">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-dark-950/70">
          <div className="flex items-center space-x-2.5">
            <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Sliders className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-base font-bold text-white">System Architecture & Gemini Engine</h2>
              <p className="text-xs text-slate-400">Multi-model fallback chains, security status, and observability</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-200 text-xs">
          
          {/* Section 1: Server-Side Security Status */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-emerald-500/30 glow-emerald space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-white flex items-center space-x-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <span>API Key Security Status</span>
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-semibold border border-emerald-500/30 flex items-center space-x-1">
                <Lock className="h-3 w-3" />
                <span>Server-Side Isolated</span>
              </span>
            </div>

            <p className="text-slate-300 leading-relaxed">
              API authentication is strictly isolated to your server-side <code className="text-emerald-300 font-mono font-bold">.env</code> file. Direct browser entry has been disabled to prevent client-side key leakage, script scraping, and unauthorized exposure.
            </p>

            <div className="p-3 rounded-xl bg-dark-950 border border-slate-800 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-slate-400">
                <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Loaded from: <code className="text-slate-200 font-mono">/Users/ayush/Developer/aws/.env</code></span>
              </div>
              <span className="text-[11px] text-emerald-400 font-bold">ACTIVE & SECURED</span>
            </div>
          </div>

          {/* Section 2: Architectural Pillars & Fallback Chains */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
            <span className="text-sm font-bold text-white flex items-center space-x-2">
              <Cpu className="h-4 w-4 text-indigo-400" />
              <span>Multi-Model Fallback Chains (Tiered Routing)</span>
            </span>

            <div className="space-y-3">
              {/* Heavy Chain */}
              <div className="p-3 rounded-xl bg-dark-950 border border-slate-800">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-bold text-slate-300">Heavy Task Chain (Deal Rationale & NL Advisor)</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300">task="heavy"</span>
                </div>
                <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">1. gemini-3.6-flash</span>
                  <span className="text-slate-500">→</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">2. gemini-3.5-flash-lite</span>
                  <span className="text-slate-500">→</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">3. gemini-3.1-flash-lite</span>
                  <span className="text-slate-500">→</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400">4. gemini-flash-lite-latest</span>
                </div>
              </div>

              {/* Light Chain */}
              <div className="p-3 rounded-xl bg-dark-950 border border-slate-800">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-bold text-slate-300">Light Task Chain (Integrity & Pros/Cons)</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300">task="light"</span>
                </div>
                <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                  <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">1. gemini-3.5-flash-lite</span>
                  <span className="text-slate-500">→</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">2. gemini-3.1-flash-lite</span>
                  <span className="text-slate-500">→</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">3. gemini-3.6-flash</span>
                  <span className="text-slate-500">→</span>
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400">4. gemini-flash-lite-latest</span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: Observability & Rotating Log Monitor */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-bold text-white flex items-center space-x-2">
                <Activity className="h-4 w-4 text-emerald-400" />
                <span>Observability & Diagnostic Records</span>
              </span>
              <button
                onClick={fetchStatus}
                disabled={isLoadingStatus}
                className="text-slate-400 hover:text-white p-1"
                title="Refresh logs"
              >
                <RefreshCw className={`h-4 w-4 ${isLoadingStatus ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Last Call Snapshot */}
            {systemStatus?.last_call && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="p-2.5 rounded-xl bg-dark-950 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase block">Model Used</span>
                  <span className="font-mono text-emerald-400 font-semibold">{systemStatus.last_call.model_used || 'cache'}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-dark-950 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase block">Source</span>
                  <span className="font-semibold text-white uppercase">{systemStatus.last_call.source}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-dark-950 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase block">Attempts</span>
                  <span className="font-semibold text-white">{systemStatus.last_call.attempts}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-dark-950 border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase block">Latency</span>
                  <span className="font-semibold text-white">{systemStatus.last_call.seconds}s</span>
                </div>
              </div>
            )}

            {/* Recent Rotating Log Records */}
            <div>
              <span className="text-[11px] font-bold text-slate-400 block mb-1.5 flex items-center space-x-1">
                <FileText className="h-3.5 w-3.5" />
                <span>Recent logs from backend/logs/calls.log (RotatingFileHandler):</span>
              </span>
              <div className="bg-dark-950 rounded-xl p-3 font-mono text-[10px] text-slate-400 max-h-36 overflow-y-auto space-y-1 border border-slate-800">
                {systemStatus?.recent_logs?.length ? (
                  systemStatus.recent_logs.map((line, i) => (
                    <div key={i} className="leading-tight text-slate-300">
                      {line}
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500 italic">No calls logged yet. Start tracking a product!</div>
                )}
              </div>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-dark-950/70 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium transition"
          >
            Done
          </button>
        </div>

      </div>
    </div>
  );
}
