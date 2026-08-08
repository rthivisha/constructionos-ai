"use client";
import React from "react";
import { cn } from "@/app/lib/utils";
import { ShieldAlert, ShieldCheck, AlertTriangle, CheckCircle2, XCircle, Activity, DollarSign, Clock } from "lucide-react";

interface ReasoningTraceProps {
  data: {
    observation: {
      event_type: string | null;
      task_id: string | null;
      severity: number | null;
      task_not_matched: boolean;
      parse_error: boolean;
    };
    safety_assessment: {
      hard_stop: boolean;
      triggered_rules: { code: string; description: string }[];
      brief: string;
      advisory_considerations?: string;
      advisory_disclaimer?: string;
      fallback_mode_active: boolean;
      parse_error: boolean;
      status?: string;
    };
    financial_assessment: {
      status: string;
      task_id: string | null;
      delay_days_used: number | null;
      delay_source: string | null;
      cpm_result: {
        assigned_crew?: string;
        daily_operating_cost?: number;
        contractor_penalty_rate?: number;
        critical_path?: boolean;
        baseline_project_duration?: number;
        new_project_duration?: number;
        project_delay?: number;
        total_financial_exposure?: number;
        breakdown?: {
          operating_cost_exposure: number;
          penalty_exposure: number;
          shifted_tasks: string[];
          penalized_tasks: string[];
        };
        fallback_mode_active?: boolean;
        parse_error: boolean;
      } | null;
      summary: string;
    };
  } | null;
}

function SeverityBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(10, value ?? 0)) * 10;
  const color = value >= 8 ? "#ef4444" : value >= 5 ? "#f59e0b" : "#10b981";
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-sm font-bold tabular-nums" style={{ color }}>{value ?? 0}<span className="text-xs font-normal opacity-50">/10</span></span>
    </div>
  );
}

function Badge({ children, variant = "default" }: { children: React.ReactNode; variant?: "default"|"halt"|"ok"|"warn"|"muted" }) {
  const styles: Record<string, string> = {
    default: "bg-white/8 text-slate-400 border-white/10",
    halt: "bg-red-500/15 text-red-400 border-red-500/30",
    ok: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    warn: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    muted: "bg-white/5 text-slate-500 border-white/8",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide", styles[variant])}>
      {children}
    </span>
  );
}

function Card({ children, className, glow }: { children: React.ReactNode; className?: string; glow?: "halt"|"ok"|"none" }) {
  const glowStyles: Record<string, string> = {
    halt: "shadow-[0_0_40px_-12px_rgba(239,68,68,0.25)] border-red-500/20 hover:border-red-500/35",
    ok: "shadow-[0_0_40px_-12px_rgba(16,185,129,0.2)] border-emerald-500/20 hover:border-emerald-500/35",
    none: "border-white/8 hover:border-white/16",
  };
  return (
    <div className={cn(
      "relative rounded-2xl border p-6 transition-all duration-300",
      "bg-white/[0.03] backdrop-blur-xl",
      glowStyles[glow ?? "none"],
      className
    )}>
      {children}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500 mb-1">{children}</p>;
}

export default function ReasoningTrace({ data }: ReasoningTraceProps) {
  if (!data) return null;
  const { observation, safety_assessment, financial_assessment } = data;
  const isHardStop = safety_assessment.hard_stop && safety_assessment.status !== "unavailable";
  const isFinanceOk = financial_assessment.status === "success";

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      {/* ── OBSERVE CARD ── */}
      <Card>
        <div className="flex items-start justify-between gap-3 pb-4 mb-4 border-b border-white/6">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-0.5">Stage 1</p>
            <h3 className="text-base font-semibold text-slate-100">Observation</h3>
          </div>
          <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-slate-700/40 shrink-0">
            <Activity className="w-4 h-4 text-slate-400" />
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <SectionLabel>Event Category</SectionLabel>
            <p className="text-base font-semibold text-slate-100 capitalize mt-1">
              {observation.event_type ? observation.event_type.replace(/_/g, " ") : <span className="text-slate-500 italic">Unknown</span>}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <SectionLabel>Matched Task</SectionLabel>
              <p className={cn("text-sm font-mono font-semibold mt-1", observation.task_id ? "text-slate-200" : "text-slate-500 italic")}>
                {observation.task_id || (observation.task_not_matched ? "No Match" : "N/A")}
              </p>
            </div>
            <div>
              <SectionLabel>Severity</SectionLabel>
              <div className="mt-1">
                <SeverityBar value={observation.severity ?? 0} />
              </div>
            </div>
          </div>

          <div>
            <SectionLabel>Status</SectionLabel>
            <div className="mt-1">
              {observation.parse_error ? (
                <Badge variant="halt"><XCircle className="w-3 h-3 mr-1" />Parse Error</Badge>
              ) : observation.task_not_matched ? (
                <Badge variant="warn"><AlertTriangle className="w-3 h-3 mr-1" />Unmatched Task</Badge>
              ) : (
                <Badge variant="ok"><CheckCircle2 className="w-3 h-3 mr-1" />Valid Match</Badge>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* ── SAFETY CARD ── */}
      <Card glow={isHardStop ? "halt" : "none"}>
        <div className="flex items-start justify-between gap-3 pb-4 mb-4 border-b border-white/6">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-0.5">Stage 2</p>
            <h3 className="text-base font-semibold text-slate-100">Safety & Compliance</h3>
          </div>
          <div className={cn("flex items-center justify-center w-9 h-9 rounded-xl shrink-0",
            isHardStop ? "bg-red-500/20" : "bg-emerald-500/10"
          )}>
            {isHardStop
              ? <ShieldAlert className="w-4 h-4 text-red-400" />
              : <ShieldCheck className="w-4 h-4 text-emerald-400" />}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <SectionLabel>Hard Stop</SectionLabel>
            {safety_assessment.status === "unavailable"
              ? <Badge variant="halt">UNAVAILABLE</Badge>
              : isHardStop
                ? <Badge variant="halt"><span className="mr-1.5 inline-block w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />HALT TRIGGERED</Badge>
                : <Badge variant="ok">NONE ACTIVE</Badge>
            }
          </div>

          {safety_assessment.triggered_rules?.length > 0 ? (
            <div>
              <SectionLabel>Triggered Regulations</SectionLabel>
              <div className="mt-1.5 space-y-2">
                {safety_assessment.triggered_rules.map((rule, idx) => (
                  <div key={idx} className="rounded-lg bg-red-500/8 border border-red-500/20 p-3">
                    <span className="font-mono text-xs font-bold text-red-400 block mb-0.5">{rule.code}</span>
                    <span className="text-xs text-slate-400 leading-relaxed">{rule.description}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <SectionLabel>Triggered Regulations</SectionLabel>
              <p className="mt-1 text-sm text-slate-500 italic">No regulatory violations identified.</p>
            </div>
          )}

          <div>
            <SectionLabel>Safety Brief</SectionLabel>
            <p className="mt-1 text-sm text-slate-300 leading-relaxed bg-white/[0.02] rounded-xl p-3 border border-white/6">
              {safety_assessment.brief}
            </p>
          </div>

          {safety_assessment.advisory_considerations && (
            <div className="pt-3 border-t border-white/6 space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-widest text-amber-500">
                AI Advisory Considerations
              </p>
              <div className="rounded-xl bg-amber-500/5 border border-amber-500/15 p-3 text-xs text-slate-300 whitespace-pre-line leading-relaxed">
                {safety_assessment.advisory_considerations}
              </div>
              {safety_assessment.advisory_disclaimer && (
                <p className="text-[10px] text-slate-500 italic leading-relaxed">
                  {safety_assessment.advisory_disclaimer}
                </p>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* ── FINANCE CARD ── */}
      <Card glow={isFinanceOk ? "ok" : "none"}>
        <div className="flex items-start justify-between gap-3 pb-4 mb-4 border-b border-white/6">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-slate-500 mb-0.5">Stage 3</p>
            <h3 className="text-base font-semibold text-slate-100">Cost & Schedule</h3>
          </div>
          <div className={cn("flex items-center justify-center w-9 h-9 rounded-xl shrink-0",
            isFinanceOk ? "bg-sky-500/20" : "bg-white/5"
          )}>
            <DollarSign className={cn("w-4 h-4", isFinanceOk ? "text-sky-400" : "text-slate-500")} />
          </div>
        </div>

        {!isFinanceOk ? (
          <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-slate-600" />
            </div>
            <div>
              <Badge variant="muted" >
                {financial_assessment.status === "insufficient_data" ? "INSUFFICIENT DATA" : "UNAVAILABLE"}
              </Badge>
              <p className="mt-2 text-xs text-slate-500 leading-relaxed max-w-[220px]">
                {financial_assessment.summary || "Financial exposure could not be calculated due to unmatched task or missing data."}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-white/[0.03] border border-white/6 p-3">
                <SectionLabel>Delay Used</SectionLabel>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-2xl font-black text-slate-100 tabular-nums">{financial_assessment.delay_days_used ?? 0}</span>
                  <span className="text-xs text-slate-500">days</span>
                </div>
                <p className="text-[10px] text-slate-600 mt-0.5">
                  {financial_assessment.delay_source === "extracted_from_text" ? "from report" : "severity fallback"}
                </p>
              </div>
              <div className="rounded-xl bg-white/[0.03] border border-white/6 p-3">
                <SectionLabel>Project Impact</SectionLabel>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-2xl font-black text-slate-100 tabular-nums">
                    +{financial_assessment.cpm_result?.project_delay ?? 0}
                  </span>
                  <span className="text-xs text-slate-500">days</span>
                </div>
                {financial_assessment.cpm_result?.critical_path ? (
                  <p className="text-[10px] font-bold text-amber-500 mt-0.5">Critical Path</p>
                ) : (
                  <p className="text-[10px] text-slate-600 mt-0.5">Non-Critical</p>
                )}
              </div>
            </div>

            <div>
              <SectionLabel>Total INR Exposure</SectionLabel>
              <p className="text-2xl font-black text-sky-400 mt-1 tabular-nums">
                ₹{financial_assessment.cpm_result?.total_financial_exposure?.toLocaleString("en-IN") ?? "0"}
              </p>
              {financial_assessment.cpm_result?.breakdown && (
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs bg-white/[0.02] rounded-xl p-3 border border-white/6">
                  <div>
                    <span className="text-slate-500">Ops Cost</span>
                    <p className="font-mono font-semibold text-slate-300">
                      ₹{financial_assessment.cpm_result.breakdown.operating_cost_exposure.toLocaleString("en-IN")}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500">Penalties</span>
                    <p className="font-mono font-semibold text-slate-300">
                      ₹{financial_assessment.cpm_result.breakdown.penalty_exposure.toLocaleString("en-IN")}
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div>
              <SectionLabel>Financial Brief</SectionLabel>
              <p className="mt-1 text-sm text-slate-300 leading-relaxed bg-white/[0.02] rounded-xl p-3 border border-white/6">
                {financial_assessment.summary}
              </p>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
