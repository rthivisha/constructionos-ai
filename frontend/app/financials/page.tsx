"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  DollarSign, 
  TrendingDown, 
  Clock, 
  Layers, 
  AlertCircle, 
  CheckCircle2, 
  ExternalLink,
  Zap,
  Users,
  Activity,
  ArrowRight
} from "lucide-react";
import { api } from "../lib/api";

interface Contractor {
  name: string;
  scope: string;
  daily_operating_cost: number;
  daily_delay_penalty: number;
  active_workers: number;
}

interface ScheduleTask {
  task_id: string;
  division_id: string;
  task_name: string;
  duration: number;
  is_critical_path: number;
  dependencies: string;
}

interface ProjectMeta {
  name: string;
  location: string;
  total_budget: number;
  spent_to_date: number;
}

export default function FinancialsPage() {
  const [meta, setMeta] = useState<ProjectMeta | null>(null);
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [tasks, setTasks] = useState<ScheduleTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadFinancialData() {
      try {
        const data = await api.getProjectSetup();
        setMeta(data.project_meta);
        setContractors(data.contractors || []);
        setTasks(data.schedule_tasks || []);
      } catch (err) {
        console.error("Failed to load financial & CPM data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadFinancialData();
  }, []);

  const totalDailyOperatingCost = contractors.reduce((sum, c) => sum + (c.daily_operating_cost || 0), 0);
  const totalDailyDelayPenalty = contractors.reduce((sum, c) => sum + (c.daily_delay_penalty || 0), 0);
  const totalActiveWorkers = contractors.reduce((sum, c) => sum + (c.active_workers || 0), 0);
  const criticalTasksCount = tasks.filter((t) => t.is_critical_path === 1).length;

  const totalBudget = meta?.total_budget || 750000000;
  const spentToDate = meta?.spent_to_date || 182000000;
  const remainingBudget = totalBudget - spentToDate;
  const spentPercentage = Math.round((spentToDate / totalBudget) * 100);

  return (
    <div className="min-h-full bg-slate-950 text-slate-100 py-8 sm:py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-10">
        
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-slate-800/80">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-400">
              <DollarSign className="h-3.5 w-3.5" />
              <span>CPM Engine & Financial Exposure Intelligence</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-100">
              Cost & CPM Delay{" "}
              <span className="bg-gradient-to-r from-sky-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
                Analytics
              </span>
            </h1>
            <p className="max-w-2xl text-xs sm:text-sm text-slate-400 leading-relaxed">
              Real-time Critical Path Method (CPM) delay calculations, contractor SLA standby burn rates, and project liquidated damages models.
            </p>
          </div>

          <Link
            href="/setup"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:border-sky-500/40 hover:text-white transition"
          >
            <span>Edit Project Budget & SLAs</span>
            <ExternalLink className="h-3.5 w-3.5 text-slate-400" />
          </Link>
        </div>

        {/* Top Financial KPI Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider">Daily Operating Standby</span>
              <Activity className="h-4 w-4 text-sky-400" />
            </div>
            <div className="text-2xl font-black text-slate-100 font-mono">
              ₹{totalDailyOperatingCost.toLocaleString("en-IN")}
              <span className="text-xs font-normal text-slate-400 font-sans"> / day</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Total contractor equipment & idling burn</p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider">Delay Liquidated Damages</span>
              <TrendingDown className="h-4 w-4 text-rose-400" />
            </div>
            <div className="text-2xl font-black text-rose-400 font-mono">
              ₹{totalDailyDelayPenalty.toLocaleString("en-IN")}
              <span className="text-xs font-normal text-slate-400 font-sans"> / day</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Contractual penalty for late critical path delivery</p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider">Active Site Workforce</span>
              <Users className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-black text-emerald-400 font-mono">
              {totalActiveWorkers}
              <span className="text-xs font-normal text-slate-400 font-sans"> workers</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Across {contractors.length} active trade contracts</p>
          </div>

          <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider">Critical Path Tasks</span>
              <Clock className="h-4 w-4 text-amber-400" />
            </div>
            <div className="text-2xl font-black text-amber-400 font-mono">
              {criticalTasksCount}
              <span className="text-xs font-normal text-slate-400 font-sans"> of {tasks.length}</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Zero-slack tasks that cause net project delay</p>
          </div>
        </div>

        {/* Budget Progress & Health Meter */}
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 sm:p-8 backdrop-blur-xl shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="text-lg font-bold text-slate-100">Project Capital Budget Health</h3>
              <p className="text-xs text-slate-400">{meta?.name || "Metro Phase 2 Line"} • {meta?.location || "Bengaluru"}</p>
            </div>
            <div className="text-right">
              <span className="text-xs font-bold text-slate-300">Spent to Date: </span>
              <span className="font-mono font-black text-sky-400">₹{spentToDate.toLocaleString("en-IN")}</span>
              <span className="text-xs text-slate-400"> / ₹{totalBudget.toLocaleString("en-IN")}</span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-1.5">
            <div className="h-3 w-full overflow-hidden rounded-full bg-slate-950 border border-slate-800 p-0.5">
              <div
                className="h-full rounded-full bg-gradient-to-r from-sky-500 via-blue-500 to-indigo-500 transition-all duration-500"
                style={{ width: `${Math.min(spentPercentage, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] font-mono text-slate-400">
              <span>{spentPercentage}% Capital Disbursed</span>
              <span className="text-emerald-400">Remaining Contingency: ₹{remainingBudget.toLocaleString("en-IN")}</span>
            </div>
          </div>
        </div>

        {/* Critical Path Tasks Grid */}
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 sm:p-8 backdrop-blur-xl shadow-xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Clock className="h-4 w-4 text-sky-400" />
                CPM Critical Path Schedule
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic DAG network with topological sort to evaluate exact project completion milestones.
              </p>
            </div>
            <span className="rounded-full bg-slate-950 border border-slate-800 px-3 py-1 text-xs font-mono text-slate-400">
              {tasks.length} Schedule Nodes
            </span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                  <th className="p-4">Task ID</th>
                  <th className="p-4">Task Name</th>
                  <th className="p-4">Division</th>
                  <th className="p-4">Duration</th>
                  <th className="p-4">Critical Path</th>
                  <th className="p-4">Predecessor Dependencies</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-400">Loading schedule...</td>
                  </tr>
                ) : tasks.map((task) => (
                  <tr key={task.task_id} className="hover:bg-slate-900/40 transition">
                    <td className="p-4 font-mono font-bold text-sky-400">{task.task_id}</td>
                    <td className="p-4 font-medium text-slate-200">{task.task_name}</td>
                    <td className="p-4 font-mono text-slate-400">{task.division_id}</td>
                    <td className="p-4 font-mono text-slate-300">{task.duration} Days</td>
                    <td className="p-4">
                      {task.is_critical_path === 1 ? (
                        <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 border border-amber-500/30 px-2.5 py-1 text-[10px] font-bold text-amber-400 font-mono">
                          CRITICAL PATH
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-md bg-slate-800/60 border border-slate-700/60 px-2.5 py-1 text-[10px] font-medium text-slate-400">
                          HAS FLOAT / SLACK
                        </span>
                      )}
                    </td>
                    <td className="p-4 font-mono text-slate-400">{task.dependencies || "None (Start Node)"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Contractor SLA & Operating Rates */}
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 sm:p-8 backdrop-blur-xl shadow-xl space-y-6">
          <div>
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Users className="h-4 w-4 text-indigo-400" />
              Contractor Operating Rates & Delay Penalties
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Parameters used by the Finance Agent to compute exact financial exposure during incident halts.
            </p>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                  <th className="p-4">Contractor</th>
                  <th className="p-4">Trade Scope</th>
                  <th className="p-4">Daily Standby Cost</th>
                  <th className="p-4">Daily Delay Penalty</th>
                  <th className="p-4">Labor Capacity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {contractors.map((c, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/40 transition">
                    <td className="p-4 font-bold text-slate-200">{c.name}</td>
                    <td className="p-4 text-slate-400">{c.scope}</td>
                    <td className="p-4 font-mono text-sky-400">₹{(c.daily_operating_cost || 0).toLocaleString("en-IN")} / day</td>
                    <td className="p-4 font-mono text-rose-400">₹{(c.daily_delay_penalty || 0).toLocaleString("en-IN")} / day</td>
                    <td className="p-4 font-mono text-emerald-400">{c.active_workers || 0} active workers</td>
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
