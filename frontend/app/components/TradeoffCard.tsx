"use client";
import React from "react";
import { cn } from "@/app/lib/utils";
import { AlertTriangle, CheckCircle2, XCircle, ArrowRight } from "lucide-react";

interface TradeoffCardProps {
  data: {
    decision: "halt" | "continue";
    reasoning: string;
    rejected_alternative: "halt" | "continue";
    rejected_because: string;
  } | null;
  financialStatus?: string;
}

export default function TradeoffCard({ data, financialStatus }: TradeoffCardProps) {
  if (!data) return null;
  const isHalt = data.decision === "halt";
  const isFinanceUnavailable = financialStatus === "unavailable" || financialStatus === "insufficient_data";

  return (
    <div className={cn(
      "relative overflow-hidden rounded-2xl border p-8 transition-all duration-500",
      "bg-white/[0.03] backdrop-blur-xl",
      isHalt
        ? "border-red-500/25 shadow-[0_0_60px_-20px_rgba(239,68,68,0.3)] hover:border-red-500/40"
        : "border-emerald-500/25 shadow-[0_0_60px_-20px_rgba(16,185,129,0.25)] hover:border-emerald-500/40"
    )}>
      {/* Ambient glow orb */}
      <div className={cn(
        "absolute -right-32 -top-32 w-64 h-64 rounded-full blur-3xl pointer-events-none opacity-20 transition-colors duration-500",
        isHalt ? "bg-red-500" : "bg-emerald-500"
      )} />

      {/* Safety-only protocol warning */}
      {isFinanceUnavailable && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/8 p-4">
          <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-bold text-amber-400 mb-0.5">Safety-Only Decision Protocol Active</p>
            <p className="text-xs text-amber-400/70 leading-relaxed">
              Financial cost data was unavailable or insufficient. This decision was made strictly on safety information alone.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-8 md:grid-cols-12">
        {/* Left: Reasoning */}
        <div className="md:col-span-7 flex flex-col gap-5">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Reconciliation Stage</p>
              <span className={cn(
                "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-wider",
                isHalt ? "bg-red-500/10 text-red-400 border-red-500/25" : "bg-emerald-500/10 text-emerald-400 border-emerald-500/25"
              )}>RECONCILED</span>
            </div>
            <h2 className="text-sm font-semibold text-slate-400 mb-2">Decision Rationale</h2>
            <p className="text-base text-slate-200 leading-relaxed font-light">{data.reasoning}</p>
          </div>
        </div>

        {/* Right: Decision + Rejected Alternative */}
        <div className="md:col-span-5 flex flex-col gap-6 md:border-l md:border-white/6 md:pl-8">
          {/* Final Action badge */}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500 mb-3">Final Action</p>
            <div className={cn(
              "inline-flex items-center gap-3 rounded-2xl border px-6 py-4",
              isHalt
                ? "bg-red-500/10 border-red-500/30 text-red-400"
                : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
            )}>
              <span className={cn(
                "h-3 w-3 rounded-full",
                isHalt ? "bg-red-500 animate-ping" : "bg-emerald-500"
              )} />
              <span className="text-2xl font-black uppercase tracking-wider">{data.decision}</span>
            </div>
          </div>

          {/* Rejected alternative */}
          <div className="pt-5 border-t border-white/6">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500 mb-2">Rejected Alternative</p>
            <div className="flex items-center gap-2 mb-3">
              <XCircle className="w-4 h-4 text-slate-600 shrink-0" />
              <span className="text-sm font-bold uppercase tracking-wider text-slate-500 line-through">
                {data.rejected_alternative}
              </span>
            </div>
            <div className="rounded-xl bg-white/[0.02] border border-white/6 p-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1">Reason for Rejection</p>
              <p className="text-sm text-slate-300 leading-relaxed">{data.rejected_because}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
