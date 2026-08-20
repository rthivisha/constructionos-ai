"use client";

import React, { useState } from "react";
import Link from "next/link";
import { 
  History, 
  Cpu, 
  Database, 
  ShieldCheck, 
  ArrowRight, 
  CheckCircle2, 
  FileSpreadsheet, 
  Printer, 
  Sparkles,
  Zap,
  Activity,
  Layers,
  Clock,
  Lock
} from "lucide-react";

export default function AuditPage() {
  const [reportDate, setReportDate] = useState(new Date().toISOString().split("T")[0]);
  const [inspectorName, setInspectorName] = useState("Site Manager / Lead Safety Officer");
  const [selectedIncident, setSelectedIncident] = useState("Crane Wire Rope Strand Rupture (T-101)");
  const [printMode, setPrintMode] = useState(false);

  const sampleAuditEvents = [
    {
      id: "EVT-8941",
      timestamp: "Today, 10:42 AM",
      eventText: "Crane wire rope frayed during girder lift on Task T-101",
      status: "BLOCKED",
      statusColor: "bg-red-500/10 text-red-400 border-red-500/30",
      rule: "BOCW_SEC_40",
      financialExposure: "₹4,20,000",
      cacheState: "CACHE HIT (SHA-256)",
      verifiedBy: "System Guard (Hard Stop)",
    },
    {
      id: "EVT-8940",
      timestamp: "Today, 09:15 AM",
      eventText: "H2S chemical odor detected in underground tunnel shaft Task T-104",
      status: "CONDITIONAL",
      statusColor: "bg-amber-500/10 text-amber-400 border-amber-500/30",
      rule: "BOCW_SEC_38",
      financialExposure: "₹1,80,000",
      cacheState: "LIVE GEMINI",
      verifiedBy: "Site Manager (Physical Verification)",
    },
    {
      id: "EVT-8939",
      timestamp: "Yesterday, 04:30 PM",
      eventText: "Shipment of structural rebar delayed by 48 hours for Task T-104",
      status: "CLEAR / PROCEED",
      statusColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      rule: "NONE (NON-HAZARDOUS)",
      financialExposure: "₹0 (Float Absorb)",
      cacheState: "CACHE HIT",
      verifiedBy: "Automated Trade-off",
    },
    {
      id: "EVT-8938",
      timestamp: "Yesterday, 01:10 PM",
      eventText: "Torrential downpour and wind speeds exceeding 55 km/h on Task T-103",
      status: "BLOCKED",
      statusColor: "bg-red-500/10 text-red-400 border-red-500/30",
      rule: "BOCW_SEC_42",
      financialExposure: "₹3,50,000",
      cacheState: "LIVE GEMINI",
      verifiedBy: "Safety Engine Trigger",
    }
  ];

  return (
    <div className="min-h-full bg-slate-950 text-slate-100 py-8 sm:py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-10">
        
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-slate-800/80">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-400">
              <History className="h-3.5 w-3.5" />
              <span>Multi-Agent System Telemetry & Immutable Log</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-100">
              Audit Trail &{" "}
              <span className="bg-gradient-to-r from-sky-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
                Pipeline Telemetry
              </span>
            </h1>
            <p className="max-w-2xl text-xs sm:text-sm text-slate-400 leading-relaxed">
              Real-time multi-agent execution telemetry, deterministic SHA-256 exact match cache tracking, and statutory incident audit logs.
            </p>
          </div>

          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 border border-slate-800 px-4 py-2.5 text-xs font-bold text-slate-300 hover:border-sky-500/40 hover:text-white transition shadow-sm"
          >
            <Printer className="h-4 w-4 text-sky-400" />
            <span>Export / Print Compliance Log</span>
          </button>
        </div>

        {/* Pipeline Architecture Telemetry Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-xl space-y-2">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider">AI Reasoning Engine</span>
              <Cpu className="h-4 w-4 text-purple-400" />
            </div>
            <div className="text-xl font-extrabold text-slate-100 flex items-center gap-2">
              <span>Gemini 3.5 Flash</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                ACTIVE
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Exponential backoff with automated fallback to deterministic rule engine upon quota saturation.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-xl space-y-2">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider">Response Caching Engine</span>
              <Database className="h-4 w-4 text-sky-400" />
            </div>
            <div className="text-xl font-extrabold text-slate-100 flex items-center gap-2">
              <span>Exact-Match SHA-256</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 border border-sky-500/30">
                ENABLED
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Zero fuzzy matching to prevent approximate compliance decisions. Purged automatically on setup edits.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-xl space-y-2">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-[10px] font-bold uppercase tracking-wider">Human-In-The-Loop Gate</span>
              <Lock className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="text-xl font-extrabold text-slate-100 flex items-center gap-2">
              <span>Physical Gate</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                LOCKED
              </span>
            </div>
            <p className="text-xs text-slate-400">
              `controls_verified` must originate from explicit physical UI confirmation and is never self-certified.
            </p>
          </div>
        </div>

        {/* Multi-Agent Orchestration Diagram */}
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 sm:p-8 backdrop-blur-xl shadow-xl space-y-4">
          <div>
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Activity className="h-4 w-4 text-sky-400" />
              Pipeline Execution Topology
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Strict parallel fan-out / fan-in orchestration sequence for zero-latency deterministic safety validation.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3.5 space-y-1">
              <span className="text-[10px] font-mono text-sky-400 font-bold uppercase">Stage 01</span>
              <h4 className="text-xs font-bold text-slate-200">Observe Agent</h4>
              <p className="text-[11px] text-slate-400">Extracts event type, WBS task IDs, severity, and hazards from unstructured site reports.</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3.5 space-y-1">
              <span className="text-[10px] font-mono text-emerald-400 font-bold uppercase">Stage 02 (Parallel)</span>
              <h4 className="text-xs font-bold text-slate-200">Safety & CPM Finance</h4>
              <p className="text-[11px] text-slate-400">Safety Agent evaluates BOCW/OSHA violations while Finance Agent runs DAG CPM schedule delay recalculations.</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3.5 space-y-1">
              <span className="text-[10px] font-mono text-amber-400 font-bold uppercase">Stage 03</span>
              <h4 className="text-xs font-bold text-slate-200">Trade-Off Reconciliation</h4>
              <p className="text-[11px] text-slate-400">Evaluates safety primacy over financial delay penalty. Enforces 5-tier safety gate taxonomy.</p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3.5 space-y-1">
              <span className="text-[10px] font-mono text-purple-400 font-bold uppercase">Stage 04</span>
              <h4 className="text-xs font-bold text-slate-200">Directives & Memo Gen</h4>
              <p className="text-[11px] text-slate-400">Generates instant field WhatsApp alerts, formal contractor memos, and avoided loss calculations.</p>
            </div>
          </div>
        </div>

        {/* Recent Site Event Audit Logs Table */}
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 sm:p-8 backdrop-blur-xl shadow-xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-emerald-400" />
                Immutable Statutory Audit Record
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Full cryptographic history of safety decisions, verified controls, and financial exposure.
              </p>
            </div>
            <span className="text-xs font-mono text-slate-400 bg-slate-950 border border-slate-800 px-3 py-1 rounded-full">
              4 Audit Events Recorded
            </span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                  <th className="p-4">Event ID</th>
                  <th className="p-4">Timestamp</th>
                  <th className="p-4">Reported Incident</th>
                  <th className="p-4">Decision Status</th>
                  <th className="p-4">Regulatory Rule</th>
                  <th className="p-4">Financial Exposure</th>
                  <th className="p-4">Cache Telemetry</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {sampleAuditEvents.map((evt) => (
                  <tr key={evt.id} className="hover:bg-slate-900/40 transition">
                    <td className="p-4 font-mono font-bold text-sky-400">{evt.id}</td>
                    <td className="p-4 font-mono text-slate-400 whitespace-nowrap">{evt.timestamp}</td>
                    <td className="p-4 text-slate-200 max-w-xs">{evt.eventText}</td>
                    <td className="p-4 whitespace-nowrap">
                      <span className={`inline-block px-2.5 py-1 rounded-md text-[10px] font-bold border ${evt.statusColor}`}>
                        {evt.status}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-emerald-400 font-bold whitespace-nowrap">{evt.rule}</td>
                    <td className="p-4 font-mono text-slate-300 whitespace-nowrap">{evt.financialExposure}</td>
                    <td className="p-4 whitespace-nowrap">
                      <span className="text-[10px] font-mono text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
                        {evt.cacheState}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}
