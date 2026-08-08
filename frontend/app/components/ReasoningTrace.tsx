import React from 'react';

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

export default function ReasoningTrace({ data }: ReasoningTraceProps) {
  if (!data) return null;

  const { observation, safety_assessment, financial_assessment } = data;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* 1. OBSERVE AGENT CARD (Gray Theme) */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-6 backdrop-blur-md transition-all duration-300 hover:border-slate-500 hover:shadow-lg hover:shadow-slate-500/5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="font-semibold text-slate-300">Stage 1: Observation</h3>
          <span className="rounded bg-slate-800 px-2.5 py-0.5 text-xs font-medium text-slate-400">Observe Agent</span>
        </div>
        
        <div className="mt-4 space-y-4">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Event Category</span>
            <p className="mt-1 text-lg font-medium text-slate-200 capitalize">
              {observation.event_type ? observation.event_type.replace('_', ' ') : 'Unknown'}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Matched Task</span>
              <p className="mt-1 font-mono text-sm font-medium text-slate-300">
                {observation.task_id || (observation.task_not_matched ? 'No Match Found' : 'N/A')}
              </p>
            </div>
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Severity</span>
              <div className="mt-1 flex items-center gap-2">
                <span className="text-sm font-bold text-slate-300">{observation.severity ?? 0}</span>
                <span className="text-xs text-slate-500">/ 10</span>
              </div>
            </div>
          </div>

          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Observation Status</span>
            <div className="mt-1 flex items-center gap-2">
              {observation.parse_error ? (
                <span className="inline-flex items-center rounded-full bg-red-900/20 px-2.5 py-0.5 text-xs font-medium text-red-400 border border-red-900/50">
                  Observe Parse Error
                </span>
              ) : observation.task_not_matched ? (
                <span className="inline-flex items-center rounded-full bg-amber-900/20 px-2.5 py-0.5 text-xs font-medium text-amber-400 border border-amber-900/50">
                  Unmatched Task ID
                </span>
              ) : (
                <span className="inline-flex items-center rounded-full bg-emerald-900/20 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-900/50">
                  Valid Match
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 2. SAFETY AGENT CARD (Red/Orange Alert Gradient Theme) */}
      <div className="rounded-xl border border-red-900/40 bg-slate-900/60 p-6 backdrop-blur-md transition-all duration-300 hover:border-red-500/40 hover:shadow-lg hover:shadow-red-500/5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="font-semibold text-red-400">Stage 2: Safety & Compliance</h3>
          <span className="rounded bg-red-950/40 px-2.5 py-0.5 text-xs font-medium text-red-400 border border-red-900/30">Safety Agent</span>
        </div>
        
        <div className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Hard Stop Status</span>
            {safety_assessment.status === 'unavailable' ? (
              <span className="rounded-full bg-red-950/60 px-3 py-1 text-xs font-bold text-red-400 border border-red-500/50 animate-pulse">
                UNAVAILABLE
              </span>
            ) : safety_assessment.hard_stop ? (
              <span className="rounded-full bg-red-600 px-3 py-1 text-xs font-bold text-white uppercase tracking-wider">
                TRIGGERED (HALT)
              </span>
            ) : (
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-bold text-slate-400">
                NONE ACTIVE
              </span>
            )}
          </div>

          {safety_assessment.triggered_rules && safety_assessment.triggered_rules.length > 0 ? (
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Triggered Regulations</span>
              <div className="mt-1.5 space-y-1.5">
                {safety_assessment.triggered_rules.map((rule, idx) => (
                  <div key={idx} className="rounded bg-red-950/20 border border-red-950/50 p-2 text-xs text-red-300">
                    <span className="font-mono font-bold text-red-400 block mb-0.5">{rule.code}</span>
                    {rule.description}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Triggered Regulations</span>
              <p className="mt-1 text-sm text-slate-400 italic">No regulatory violations identified.</p>
            </div>
          )}

          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Safety Brief</span>
            <p className="mt-1 text-sm text-slate-300 leading-relaxed bg-slate-950/40 rounded p-2.5 border border-slate-800/80">
              {safety_assessment.brief}
            </p>
          </div>

          {safety_assessment.advisory_considerations && (
            <div className="border-t border-slate-850 pt-3.5 space-y-1">
              <span className="text-xs font-semibold text-amber-500 uppercase tracking-wider block">
                AI Advisory considerations
              </span>
              <div className="rounded bg-slate-950/30 border border-slate-850 p-2.5 text-xs text-slate-300 whitespace-pre-line leading-relaxed">
                {safety_assessment.advisory_considerations}
              </div>
              {safety_assessment.advisory_disclaimer && (
                <span className="text-[10px] text-slate-500 italic leading-normal block">
                  {safety_assessment.advisory_disclaimer}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 3. FINANCE AGENT CARD (Blue/Teal Financial Theme) */}
      <div className="rounded-xl border border-blue-900/40 bg-slate-900/60 p-6 backdrop-blur-md transition-all duration-300 hover:border-blue-500/40 hover:shadow-lg hover:shadow-blue-500/5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="font-semibold text-blue-400">Stage 3: Cost & Schedule</h3>
          <span className="rounded bg-blue-950/40 px-2.5 py-0.5 text-xs font-medium text-blue-400 border border-blue-900/30">Finance Agent</span>
        </div>
        
        <div className="mt-4 space-y-4">
          {financial_assessment.status === 'unavailable' || financial_assessment.status === 'insufficient_data' ? (
            <div className="rounded-lg bg-blue-950/20 border border-blue-950/40 p-4 text-center">
              <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider block mb-1">Financial Assessment Status</span>
              <span className="inline-block rounded-full bg-blue-900/40 px-3 py-1 text-xs font-bold text-blue-300 border border-blue-800">
                {financial_assessment.status === 'insufficient_data' ? 'INSUFFICIENT DATA' : 'UNAVAILABLE'}
              </span>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                {financial_assessment.summary || 'Financial exposure cost details could not be calculated due to unmatched task or agent crash.'}
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Delay Days</span>
                  <div className="mt-1 flex items-baseline gap-1.5">
                    <span className="text-lg font-bold text-slate-200">{financial_assessment.delay_days_used ?? 0}</span>
                    <span className="text-xs text-slate-500">Days</span>
                  </div>
                  <span className="text-[10px] text-slate-500 leading-none">
                    Source: {financial_assessment.delay_source === 'extracted_from_text' ? 'Text' : 'Fallback'}
                  </span>
                </div>
                <div>
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">Project Impact</span>
                  <div className="mt-1 flex items-baseline gap-1">
                    <span className="text-lg font-bold text-slate-200">
                      +{financial_assessment.cpm_result?.project_delay ?? 0}
                    </span>
                    <span className="text-xs text-slate-500">Days</span>
                  </div>
                  {financial_assessment.cpm_result?.critical_path ? (
                    <span className="text-[10px] font-bold text-amber-500 leading-none">Critical Path</span>
                  ) : (
                    <span className="text-[10px] text-slate-500 leading-none">Non-Critical Path</span>
                  )}
                </div>
              </div>

              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">INR Exposure</span>
                <p className="mt-1 text-xl font-black text-blue-400">
                  ₹{financial_assessment.cpm_result?.total_financial_exposure?.toLocaleString('en-IN') ?? '0'}
                </p>
                {financial_assessment.cpm_result?.breakdown && (
                  <div className="mt-1.5 grid grid-cols-2 gap-2 text-[10px] bg-slate-950/30 p-2 rounded border border-slate-800/60">
                    <div className="text-slate-400">
                      Ops Cost: <span className="font-mono font-medium text-slate-200">₹{financial_assessment.cpm_result.breakdown.operating_cost_exposure.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="text-slate-400">
                      Penalties: <span className="font-mono font-medium text-slate-200">₹{financial_assessment.cpm_result.breakdown.penalty_exposure.toLocaleString('en-IN')}</span>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Financial Brief</span>
                <p className="mt-1 text-sm text-slate-300 leading-relaxed bg-slate-950/40 rounded p-2.5 border border-slate-800/80">
                  {financial_assessment.summary}
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
