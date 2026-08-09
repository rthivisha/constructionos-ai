"use client";
import React, { useState } from "react";
import { cn } from "@/app/lib/utils";
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Activity, 
  DollarSign, 
  Send,
  ArrowRight,
  ArrowLeft,
  RotateCcw,
  MessageSquare,
  FileDown
} from "lucide-react";

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
      plain_reason: string;
      override_risk?: string;
      exception_mitigation?: string;
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
      cpm_result?: {
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
        };
      };
      cost_breakdown?: {
        scope?: string;
        halted_task_total?: number;
        idle_labour: { amount: number; formula: string; source: string };
        equipment_extension: { amount: number; formula?: string; source: string; warning?: string };
        delay_penalty: { amount: number; formula: string; source: string };
        recovery_overtime: { amount: number; formula?: string; source: string };
      };
      cost_coverage?: string;
      calculation_id?: string;
      summary: string;
    };
    tradeoff_reconciliation: {
      decision: "halt" | "continue";
      reasoning: string;
      rejected_alternative: "halt" | "continue";
      rejected_because: string;
    };
  };
  rawText?: string;
  onReset?: () => void;
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

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500 mb-1">{children}</p>;
}

function SeverityBar({ value }: { value: number }) {
  const rounded = Math.min(10, Math.max(0, value));
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] font-bold tracking-wider">
        <span className="text-slate-500">SEVERITY LEVEL</span>
        <span className={cn(
          rounded >= 7 ? "text-red-400" : rounded >= 4 ? "text-amber-400" : "text-emerald-400"
        )}>{rounded}/10</span>
      </div>
      <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
        <div 
          className={cn(
            "h-full rounded-full transition-all duration-500 bg-gradient-to-r",
            rounded >= 7 ? "from-red-500 to-rose-600" : rounded >= 4 ? "from-amber-400 to-orange-500" : "from-emerald-400 to-teal-500"
          )}
          style={{ width: `${rounded * 10}%` }}
        />
      </div>
    </div>
  );
}

export default function ReasoningTrace({ data, rawText, onReset }: ReasoningTraceProps) {
  const [activeStage, setActiveStage] = useState<1 | 2 | 3 | 4>(1);
  const [toast, setToast] = useState<string | null>(null);

  if (!data) return null;
  const { observation, safety_assessment, financial_assessment, tradeoff_reconciliation } = data;
  const isHardStop = safety_assessment.hard_stop && safety_assessment.status !== "unavailable";
  const isFinanceOk = financial_assessment.status === "success";

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const steps = [
    { stage: 1, label: "Observation", icon: Activity },
    { stage: 2, label: "Safety & Compliance", icon: ShieldAlert },
    { stage: 3, label: "Cost & Schedule", icon: DollarSign },
    { stage: 4, label: "Resolution & Directives", icon: CheckCircle2 },
  ];

  // Helper formatting for Stage 4
  const getWhatsAppMessage = () => {
    const task = observation.task_id || "N/A";
    const category = observation.event_type || "N/A";
    const rule = safety_assessment.triggered_rules?.[0]?.code || "Safety Guideline";
    const decision = tradeoff_reconciliation?.decision?.toUpperCase() || "HALT";
    
    return `⚠️ *SAFETY DEVIATION DIRECTIVE* ⚠️\nTask: *${task}* (${category.toUpperCase().replace(/_/g, " ")})\nDirective: *MANDATORY ${decision}*\nReason: Violation of regulatory rule ${rule}.\nDo not attempt local override. Remobilization requires field safety check clearance.`;
  };

  const getContractorMemo = () => {
    const contractor = financial_assessment.cpm_result?.assigned_crew || "L&T Construction";
    const task = observation.task_id || "T-101";
    const category = observation.event_type || "N/A";
    const ruleCode = safety_assessment.triggered_rules?.[0]?.code || "BOCW_SEC_40";
    const ruleDesc = safety_assessment.triggered_rules?.[0]?.description || "Regulatory safety check required.";
    const decision = tradeoff_reconciliation?.decision === "halt" ? "Mandatory suspension of work" : "Heightened surveillance continuation";
    
    return `MEMORANDUM\n\nTo: ${contractor} (Main Contractor)\nFrom: ConstructionOS AI Operations Manager\nDate: August 9, 2026\nSubject: AI Safety Directive - ${task} (${category.toUpperCase().replace(/_/g, " ")})\n\nYou are hereby directed to implement the following action: ${decision}.\n\nUnder rule code ${ruleCode} (${ruleDesc}), mandatory Standby and compliance guidelines apply. Re-mobilization requires official sign-off.`;
  };

  const handleFinish = () => {
    showToast("Audit log saved and safety checks recorded successfully!");
    setTimeout(() => {
      if (onReset) onReset();
    }, 1500);
  };

  return (
    <div className="relative rounded-2xl border border-white/6 bg-white/[0.02] backdrop-blur-xl shadow-2xl overflow-hidden flex flex-col">
      {/* ── PERSISTENT TOP STEPPER NAVIGATION BAR ── */}
      <div className="border-b border-white/6 bg-white/[0.01] px-6 py-4">
        <div className="flex items-center justify-between gap-2 max-w-4xl mx-auto">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            const isActive = activeStage === step.stage;
            const isCompleted = step.stage < activeStage;
            const isDisabled = step.stage > activeStage;
            
            return (
              <React.Fragment key={step.stage}>
                <button
                  type="button"
                  disabled={isDisabled}
                  onClick={() => !isDisabled && setActiveStage(step.stage as any)}
                  className={cn(
                    "flex flex-col sm:flex-row items-center gap-2.5 px-4 py-2.5 rounded-xl border transition-all text-left focus:outline-none",
                    isActive
                      ? "border-sky-500/30 text-sky-400 bg-sky-500/10 shadow-[0_0_20px_-5px_rgba(56,189,248,0.15)] font-semibold"
                      : isCompleted
                        ? "border-emerald-500/20 text-emerald-400 bg-emerald-500/5 cursor-pointer hover:bg-emerald-500/10"
                        : "border-white/5 text-slate-500 cursor-not-allowed opacity-50"
                  )}
                >
                  <div className={cn(
                    "flex items-center justify-center w-6 h-6 rounded-lg text-xs shrink-0",
                    isActive
                      ? "bg-sky-500/20 text-sky-400"
                      : isCompleted
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-white/5 text-slate-500"
                  )}>
                    {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}
                  </div>
                  <div className="text-center sm:text-left">
                    <p className="text-[9px] uppercase tracking-widest opacity-60">Stage {step.stage}</p>
                    <p className="text-xs font-bold hidden md:block leading-tight">{step.label}</p>
                  </div>
                </button>
                {idx < steps.length - 1 && (
                  <div className={cn(
                    "hidden sm:block h-px flex-1 border-t border-dashed transition-colors duration-300",
                    isCompleted ? "border-emerald-500/30" : "border-white/6"
                  )} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* ── STAGE VIEWS CONTENT ── */}
      <div className="p-6 flex-1 min-h-[400px]">
        
        {/* ── STAGE 1: OBSERVATION ── */}
        {activeStage === 1 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div>
              <p className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">STAGE 1</p>
              <h2 className="text-2xl font-black text-slate-100">Observation & Intake</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <Card className="md:col-span-2 space-y-4">
                <div>
                  <SectionLabel>Event Category</SectionLabel>
                  <p className="text-lg font-extrabold text-slate-100 capitalize">
                    {observation.event_type ? observation.event_type.replace(/_/g, " ") : "Unknown Category"}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-2 border-t border-white/5">
                  <div>
                    <SectionLabel>Matched Task ID</SectionLabel>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="font-mono text-sm font-bold text-slate-200">
                        {observation.task_id || "N/A"}
                      </span>
                      {observation.task_not_matched ? (
                        <Badge variant="warn">Unmatched</Badge>
                      ) : (
                        <Badge variant="ok">Valid Match</Badge>
                      )}
                    </div>
                  </div>
                  <div>
                    <SectionLabel>Severity</SectionLabel>
                    <div className="mt-1">
                      <SeverityBar value={observation.severity ?? 0} />
                    </div>
                  </div>
                </div>
              </Card>

              <Card className="flex flex-col justify-between">
                <div>
                  <SectionLabel>Status</SectionLabel>
                  <div className="mt-1">
                    {observation.parse_error ? (
                      <Badge variant="halt"><XCircle className="w-3.5 h-3.5 mr-1" />Parse Error</Badge>
                    ) : observation.task_not_matched ? (
                      <Badge variant="warn"><AlertTriangle className="w-3.5 h-3.5 mr-1" />Unmatched</Badge>
                    ) : (
                      <Badge variant="ok"><CheckCircle2 className="w-3.5 h-3.5 mr-1" />Ready</Badge>
                    )}
                  </div>
                </div>
                <p className="text-[10px] text-slate-500 leading-relaxed mt-4">
                  Observational agent completed classification of ingested disruption text against verified schedule tables.
                </p>
              </Card>
            </div>

            <div>
              <SectionLabel>Raw Incident Stream Panel</SectionLabel>
              <div className="mt-1 rounded-xl bg-slate-950 border border-white/6 p-4">
                <pre className="font-mono text-xs text-slate-400 whitespace-pre-wrap leading-relaxed">
                  {rawText || "No raw text provided."}
                </pre>
              </div>
            </div>

            {/* Bottom Action Bar */}
            <div className="pt-4 border-t border-white/6 flex justify-between items-center">
              <button
                type="button"
                onClick={onReset}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.02] px-4 py-2 text-xs font-bold text-slate-400 hover:bg-white/5 hover:text-slate-200 transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset Run
              </button>
              <button
                type="button"
                onClick={() => setActiveStage(2)}
                className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-sky-500 transition shadow-lg shadow-sky-600/20"
              >
                Proceed to Safety & Compliance
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ── STAGE 2: SAFETY & COMPLIANCE ── */}
        {activeStage === 2 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">STAGE 2</p>
                <h2 className="text-2xl font-black text-slate-100">Safety & Compliance</h2>
              </div>
              <div>
                {safety_assessment.status === "unavailable" ? (
                  <Badge variant="halt">UNAVAILABLE</Badge>
                ) : isHardStop ? (
                  <Badge variant="halt">
                    <span className="mr-1.5 inline-block w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
                    HALT TRIGGERED
                  </Badge>
                ) : (
                  <Badge variant="ok">NONE ACTIVE</Badge>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
              {/* Triggered rules */}
              <div className="md:col-span-4">
                <Card className="h-full flex flex-col justify-between">
                  <div>
                    <SectionLabel>Triggered Regulations</SectionLabel>
                    {safety_assessment.triggered_rules && safety_assessment.triggered_rules.length > 0 ? (
                      <div className="mt-2 space-y-2">
                        {safety_assessment.triggered_rules.map((rule, idx) => (
                          <div key={idx} className="rounded-lg bg-red-500/8 border border-red-500/20 p-3">
                            <span className="font-mono text-xs font-black text-red-400 block mb-0.5">{rule.code}</span>
                            <span className="text-[11px] text-slate-400 leading-relaxed">{rule.description}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic mt-2">No regulatory rules violated.</p>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-500 mt-4">
                    Strict check against legal directives (e.g. BOCW Act 1996, Factory Act 1948).
                  </p>
                </Card>
              </div>

              {/* Rationale Cards */}
              <div className="md:col-span-8 space-y-4">
                {/* Why Operations Stopped */}
                {safety_assessment.plain_reason && (
                  <div className="rounded-xl bg-white/[0.02] border border-white/6 p-4">
                    <p className="text-[10px] font-bold tracking-widest text-slate-500 uppercase mb-1">Why Operations Stopped</p>
                    <p className="text-sm text-slate-300 leading-relaxed">{safety_assessment.plain_reason}</p>
                  </div>
                )}

                {/* Risk If Override Attempted */}
                {isHardStop && safety_assessment.override_risk && (
                  <div className="rounded-xl bg-red-500/5 border border-red-500/15 p-4">
                    <p className="text-[10px] font-bold tracking-widest text-red-500 uppercase mb-1">Risk if Override Attempted</p>
                    <p className="text-sm text-red-300/80 leading-relaxed">{safety_assessment.override_risk}</p>
                  </div>
                )}

                {/* Advisory Considerations */}
                {safety_assessment.advisory_considerations && (
                  <div className="rounded-xl bg-amber-500/5 border border-amber-500/15 p-4 space-y-2">
                    <p className="text-[10px] font-bold tracking-widest text-amber-500 uppercase">AI Advisory Considerations</p>
                    <p className="text-xs text-slate-300 whitespace-pre-line leading-relaxed">
                      {safety_assessment.advisory_considerations}
                    </p>
                    {safety_assessment.advisory_disclaimer && (
                      <p className="text-[9px] text-slate-500 italic">
                        {safety_assessment.advisory_disclaimer}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Bottom Action Bar */}
            <div className="pt-4 border-t border-white/6 flex justify-between items-center">
              <button
                type="button"
                onClick={() => setActiveStage(1)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.02] px-4 py-2 text-xs font-bold text-slate-400 hover:bg-white/5 hover:text-slate-200 transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Observation
              </button>
              <button
                type="button"
                onClick={() => setActiveStage(3)}
                className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-sky-500 transition shadow-lg shadow-sky-600/20"
              >
                Proceed to Cost & Schedule
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ── STAGE 3: COST & SCHEDULE ── */}
        {activeStage === 3 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div>
              <p className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">STAGE 3</p>
              <h2 className="text-2xl font-black text-slate-100">Cost & Schedule Impact</h2>
            </div>

            {!isFinanceOk ? (
              <Card className="py-12 flex flex-col items-center justify-center text-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-slate-500" />
                </div>
                <div>
                  <Badge variant="muted">
                    {financial_assessment.status === "insufficient_data" ? "INSUFFICIENT DATA" : "UNAVAILABLE"}
                  </Badge>
                  <p className="mt-2 text-xs text-slate-500 leading-relaxed max-w-[320px]">
                    {financial_assessment.summary || "Financial calculations skipped because no active database task was matched."}
                  </p>
                </div>
              </Card>
            ) : (
              <div className="space-y-6">
                {/* Metrics Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-xl bg-white/[0.03] border border-white/6 p-4">
                    <SectionLabel>Delay Used</SectionLabel>
                    <div className="flex items-baseline gap-1 mt-1">
                      <span className="text-3xl font-black text-slate-100 tabular-nums">{financial_assessment.delay_days_used ?? 0}</span>
                      <span className="text-xs text-slate-500">days</span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1 leading-snug">
                      {financial_assessment.delay_source === "extracted_from_text"
                        ? "Number of days explicitly stated in the event report"
                        : "Estimated from event severity — no explicit delay in report"}
                    </p>
                  </div>

                  <div className="rounded-xl bg-white/[0.03] border border-white/6 p-4">
                    <SectionLabel>Project Impact</SectionLabel>
                    <div className="flex items-baseline gap-1 mt-1">
                      <span className="text-3xl font-black text-slate-100 tabular-nums">
                        +{financial_assessment.cpm_result?.project_delay ?? 0}
                      </span>
                      <span className="text-xs text-slate-500">days</span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1 leading-snug">
                      {financial_assessment.cpm_result?.critical_path
                        ? <span className="font-bold text-amber-500">On critical path — every day added pushes the project end date</span>
                        : "Off critical path — project end date unchanged by this task alone"}
                    </p>
                  </div>
                </div>

                {/* Exposure Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {/* Halted Task Only */}
                  <div className="rounded-xl bg-white/[0.02] border border-white/6 p-5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Halted Task Only</span>
                      <span className="text-[9px] bg-slate-500/10 text-slate-400 px-2 py-0.5 rounded-full border border-white/5 uppercase font-medium">Local Standby</span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1 mb-3 leading-relaxed">Direct standby labor + local contractor penalties on this task alone</p>
                    <p className="text-3xl font-black text-amber-400 tabular-nums">
                      ₹{financial_assessment.cost_breakdown?.halted_task_total?.toLocaleString("en-IN") ?? "0"}
                    </p>
                    
                    {financial_assessment.cost_breakdown && (
                      <div className="mt-4 space-y-2 text-xs text-slate-400 border-t border-white/5 pt-3">
                        <div className="flex justify-between">
                          <span>Standby Labor:</span>
                          <span className="font-mono text-slate-300">₹{financial_assessment.cost_breakdown.idle_labour.amount.toLocaleString("en-IN")}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Equip. Extension:</span>
                          <span className="font-mono text-slate-300">₹{financial_assessment.cost_breakdown.equipment_extension.amount.toLocaleString("en-IN")}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Halt Penalty:</span>
                          <span className="font-mono text-slate-300">₹{financial_assessment.cost_breakdown.delay_penalty.amount.toLocaleString("en-IN")}</span>
                        </div>
                        {financial_assessment.cost_breakdown.equipment_extension.warning && (
                          <p className="text-[10px] text-amber-500 leading-snug bg-amber-500/5 border border-amber-500/10 p-2.5 rounded-md mt-2">
                            ⚠ {financial_assessment.cost_breakdown.equipment_extension.warning}
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Full Project Impact */}
                  <div className="rounded-xl bg-white/[0.02] border border-white/6 p-5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-sky-400">Full Project Impact</span>
                      <span className="text-[9px] bg-sky-500/10 text-sky-400 px-2 py-0.5 rounded-full border border-white/5 uppercase font-medium">Cascaded</span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1 mb-3 leading-relaxed">Combined daily operating costs + delay penalties across all shifted critical path tasks</p>
                    <p className="text-3xl font-black text-sky-400 tabular-nums">
                      ₹{financial_assessment.cpm_result?.total_financial_exposure?.toLocaleString("en-IN") ?? "0"}
                    </p>
                    
                    {financial_assessment.cpm_result?.breakdown && (
                      <div className="mt-4 space-y-2 text-xs text-slate-400 border-t border-white/5 pt-3">
                        <div className="flex justify-between">
                          <span>Daily operating cost overhead:</span>
                          <span className="font-mono text-slate-300">₹{financial_assessment.cpm_result.breakdown.operating_cost_exposure.toLocaleString("en-IN")}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Downstream delay penalty:</span>
                          <span className="font-mono text-slate-300">₹{financial_assessment.cpm_result.breakdown.penalty_exposure.toLocaleString("en-IN")}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Brief & metadata */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center text-xs text-slate-500 bg-white/[0.01] px-4 py-2.5 rounded-xl border border-white/5 gap-2">
                  <span>Calculation ID: <span className="font-mono font-bold text-slate-400">{financial_assessment.calculation_id}</span></span>
                  <span>Cost Coverage: <span className="font-mono font-bold text-slate-400">{financial_assessment.cost_coverage}</span></span>
                </div>

                <div className="rounded-xl bg-white/[0.02] border border-white/6 p-4">
                  <SectionLabel>Financial Brief</SectionLabel>
                  <p className="text-sm text-slate-300 leading-relaxed mt-1">
                    {financial_assessment.summary}
                  </p>
                </div>
              </div>
            )}

            {/* Bottom Action Bar */}
            <div className="pt-4 border-t border-white/6 flex justify-between items-center">
              <button
                type="button"
                onClick={() => setActiveStage(2)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.02] px-4 py-2 text-xs font-bold text-slate-400 hover:bg-white/5 hover:text-slate-200 transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Safety & Compliance
              </button>
              <button
                type="button"
                onClick={() => setActiveStage(4)}
                className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-sky-500 transition shadow-lg shadow-sky-600/20"
              >
                Proceed to Resolution & Directives
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* ── STAGE 4: RESOLUTION & DIRECTIVES ── */}
        {activeStage === 4 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div>
              <p className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">STAGE 4</p>
              <h2 className="text-2xl font-black text-slate-100">Trade-Off Resolution & Field Action</h2>
            </div>

            {/* Reconciler */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
              <div className="md:col-span-8 flex flex-col gap-4">
                <div className="rounded-xl bg-white/[0.02] border border-white/6 p-5">
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Reconciliation Stage</p>
                    <span className={cn(
                      "inline-flex items-center rounded-full border px-2 py-0.5 text-[9px] font-bold tracking-wider",
                      tradeoff_reconciliation.decision === "halt" ? "bg-red-500/10 text-red-400 border-red-500/25" : "bg-emerald-500/10 text-emerald-400 border-emerald-500/25"
                    )}>RECONCILED</span>
                  </div>
                  <h3 className="text-xs font-bold text-slate-400 mb-1">Decision Rationale</h3>
                  <p className="text-sm text-slate-200 leading-relaxed font-light">{tradeoff_reconciliation.reasoning}</p>
                </div>
              </div>

              {/* Decision Action & Rejected Alternative */}
              <div className="md:col-span-4 flex flex-col gap-4">
                <div className="rounded-xl bg-white/[0.02] border border-white/6 p-5">
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500 mb-2">Final Action</p>
                  <div className={cn(
                    "inline-flex items-center gap-3 rounded-2xl border px-5 py-3.5",
                    tradeoff_reconciliation.decision === "halt"
                      ? "bg-red-500/10 border-red-500/30 text-red-400"
                      : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                  )}>
                    <span className={cn(
                      "h-2.5 w-2.5 rounded-full",
                      tradeoff_reconciliation.decision === "halt" ? "bg-red-500 animate-ping" : "bg-emerald-500"
                    )} />
                    <span className="text-xl font-black uppercase tracking-wider">{tradeoff_reconciliation.decision}</span>
                  </div>
                </div>

                <div className="rounded-xl bg-white/[0.02] border border-white/6 p-5">
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500 mb-2">Rejected Alternative</p>
                  <div className="flex items-center gap-2 mb-2">
                    <XCircle className="w-4 h-4 text-slate-600 shrink-0" />
                    <span className="text-sm font-bold uppercase tracking-wider text-slate-500 line-through">
                      {tradeoff_reconciliation.rejected_alternative}
                    </span>
                  </div>
                  <div className="rounded-lg bg-white/[0.01] border border-white/5 p-3 text-[11px] text-slate-400 leading-relaxed">
                    {tradeoff_reconciliation.rejected_because}
                  </div>
                </div>
              </div>
            </div>

            {/* Directives grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
              {/* WhatsApp Broadcast */}
              <div className="rounded-xl bg-white/[0.02] border border-white/6 p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <MessageSquare className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Field Broadcast Dispatcher</span>
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">WHATSAPP_ALERT</span>
                  </div>
                  <div className="rounded-lg bg-slate-950/70 border border-white/5 p-3.5 font-mono text-[11px] text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {getWhatsAppMessage()}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => showToast("WhatsApp alert broadcast successfully dispatched to field supervisor crew.")}
                  className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 text-xs transition"
                >
                  <Send className="w-3.5 h-3.5" />
                  Send WhatsApp Broadcast
                </button>
              </div>

              {/* Contractor Directive Memo */}
              <div className="rounded-xl bg-white/[0.02] border border-white/6 p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <FileDown className="w-4 h-4 text-sky-400 shrink-0" />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Contractual Directive</span>
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 font-semibold border border-sky-500/20">CONTRACTOR_MEMO</span>
                  </div>
                  <div className="rounded-lg bg-slate-950/70 border border-white/5 p-3.5 font-mono text-[11px] text-slate-300 leading-relaxed whitespace-pre-wrap h-[120px] overflow-y-auto">
                    {getContractorMemo()}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => showToast("Contractor Directive Memo PDF generated and downloaded successfully.")}
                  className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold py-2.5 text-xs transition"
                >
                  <FileDown className="w-3.5 h-3.5" />
                  Download Official Memo PDF
                </button>
              </div>
            </div>

            {/* Bottom Action Bar */}
            <div className="pt-4 border-t border-white/6 flex justify-between items-center">
              <button
                type="button"
                onClick={() => setActiveStage(3)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.02] px-4 py-2 text-xs font-bold text-slate-400 hover:bg-white/5 hover:text-slate-200 transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to Cost & Schedule
              </button>
              <button
                type="button"
                onClick={handleFinish}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-emerald-500 transition shadow-lg shadow-emerald-600/20"
              >
                Finish & Save Audit Log
                <CheckCircle2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

      </div>

      {/* ── TOAST NOTIFICATION ── */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-xl bg-slate-900 border border-emerald-500/30 text-emerald-400 px-4 py-3 shadow-2xl animate-in fade-in slide-in-from-bottom-5 duration-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span className="text-xs font-semibold">{toast}</span>
        </div>
      )}
    </div>
  );
}
