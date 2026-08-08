import React from 'react';

interface TradeoffCardProps {
  data: {
    decision: 'halt' | 'continue';
    reasoning: string;
    rejected_alternative: 'halt' | 'continue';
    rejected_because: string;
  } | null;
  financialStatus?: string;
}

export default function TradeoffCard({ data, financialStatus }: TradeoffCardProps) {
  if (!data) return null;

  const isHalt = data.decision === 'halt';
  const isFinanceUnavailable = financialStatus === 'unavailable' || financialStatus === 'insufficient_data';

  return (
    <div className={`relative overflow-hidden rounded-2xl border p-8 backdrop-blur-lg transition-all duration-500 hover:shadow-2xl ${
      isHalt 
        ? 'border-red-500/40 bg-red-950/10 hover:border-red-500/60 hover:shadow-red-500/10' 
        : 'border-emerald-500/40 bg-emerald-950/10 hover:border-emerald-500/60 hover:shadow-emerald-500/10'
    }`}>
      {/* Decorative gradient overlay */}
      <div className={`absolute -right-24 -top-24 h-48 w-48 rounded-full blur-3xl opacity-20 pointer-events-none ${
        isHalt ? 'bg-red-500' : 'bg-emerald-500'
      }`} />

      {/* Warning banner for safety-only decisions */}
      {isFinanceUnavailable && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border border-amber-950/60 bg-amber-950/30 p-3.5 text-xs text-amber-400">
          <svg className="h-5 w-5 shrink-0 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <span className="font-bold block">Safety-Only Decision Protocol Active</span>
            Financial cost exposure data was unavailable or insufficient. Decision was made strictly on safety information alone.
          </div>
        </div>
      )}

      {/* Main layout grid */}
      <div className="grid grid-cols-1 gap-8 md:grid-cols-12">
        {/* Left Column: Decision & Rationale */}
        <div className="md:col-span-7 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest block">Reconciliation Stage</span>
              <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border ${
                isHalt 
                  ? 'bg-red-950/20 text-red-400 border-red-900/50' 
                  : 'bg-emerald-950/20 text-emerald-400 border-emerald-900/50'
              }`}>
                Reconciled Decision
              </span>
            </div>
            
            <h2 className="text-sm font-semibold text-slate-400">Decision Rationale</h2>
            <p className="mt-2 text-base text-slate-200 leading-relaxed font-light">
              {data.reasoning}
            </p>
          </div>
        </div>

        {/* Right Column: Decision badges & explicit Rejected Alternative display */}
        <div className="md:col-span-5 flex flex-col gap-6 md:border-l md:border-slate-800 md:pl-8">
          
          {/* Decision badge */}
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">Final Action</span>
            <div className={`inline-flex items-center gap-3.5 px-6 py-4 rounded-xl border text-2xl font-black uppercase tracking-wider ${
              isHalt 
                ? 'bg-red-600/10 text-red-500 border-red-500/30 shadow-inner' 
                : 'bg-emerald-600/10 text-emerald-500 border-emerald-500/30 shadow-inner'
            }`}>
              <span className={`h-3 w-3 rounded-full ${isHalt ? 'bg-red-500 animate-ping' : 'bg-emerald-500'}`} />
              {data.decision}
            </div>
          </div>

          {/* Rejected alternative (visualized as prominently as the decision itself) */}
          <div className="border-t border-slate-800/80 pt-4">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">Rejected Alternative</span>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-sm text-slate-400 font-bold uppercase tracking-wider mb-3">
              ❌ {data.rejected_alternative}
            </div>
            
            <div>
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">Reason for Rejection</span>
              <p className="mt-1 text-sm font-medium text-slate-300">
                {data.rejected_because}
              </p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
