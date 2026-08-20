"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import EventInput from "./components/EventInput";
import BeamsBackground from "./components/kokonut/BeamsBackground";
import { 
  Activity, 
  ShieldCheck, 
  DollarSign, 
  Sliders, 
  ArrowRight,
  TrendingUp,
  AlertOctagon,
  Clock,
  Sparkles
} from "lucide-react";
import { api } from "./lib/api";

export default function DashboardPage() {
  const [projectMeta, setProjectMeta] = useState<any>(null);
  const [taskCount, setTaskCount] = useState<number>(0);
  const [contractorCount, setContractorCount] = useState<number>(0);

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await api.getProjectSetup();
        setProjectMeta(data.project_meta);
        setTaskCount(data.schedule_tasks?.length || 0);
        setContractorCount(data.contractors?.length || 0);
      } catch (err) {
        // Fallback default numbers if backend not yet ready
      }
    }
    loadStats();
  }, []);

  return (
    <BeamsBackground intensity="subtle" className="min-h-full text-slate-100 flex flex-col">
      <main className="flex-1">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
          
          {/* Hero Section */}
          <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6 pb-2 border-b border-slate-800/60">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-400">
                <Sparkles className="h-3.5 w-3.5" />
                <span>AI Multi-Agent Operations Command</span>
              </div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-slate-100 leading-tight">
                Operations Control{" "}
                <span className="bg-gradient-to-r from-sky-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
                  Dashboard
                </span>
              </h1>
              <p className="max-w-2xl text-xs sm:text-sm text-slate-400 font-normal leading-relaxed">
                Ingest real-time jobsite disruptions. The multi-agent pipeline analyzes safety regulations, evaluates CPM cost exposure, and determines optimal trade-off actions.
              </p>
            </div>

            {/* Quick Navigation Action Pills */}
            <div className="flex flex-wrap items-center gap-2.5">
              <Link
                href="/compliance"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:border-sky-500/40 hover:text-white transition shadow-sm"
              >
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                Safety Standards
              </Link>
              <Link
                href="/financials"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:border-sky-500/40 hover:text-white transition shadow-sm"
              >
                <DollarSign className="h-4 w-4 text-sky-400" />
                CPM Exposure
              </Link>
              <Link
                href="/setup"
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-sky-500/20 hover:from-sky-500 hover:to-blue-500 transition"
              >
                <Sliders className="h-4 w-4" />
                Project Setup
              </Link>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Metric 1: Project Name & Location */}
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 backdrop-blur-xl shadow-lg">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-[10px] font-bold uppercase tracking-wider">Active Site</span>
                <Activity className="h-3.5 w-3.5 text-sky-400" />
              </div>
              <p className="text-base font-extrabold text-slate-100 truncate">
                {projectMeta?.name || "Metro Phase 2 Line"}
              </p>
              <p className="text-[11px] text-slate-400 truncate mt-0.5">
                {projectMeta?.location || "Bengaluru Metro Corridor"}
              </p>
            </div>

            {/* Metric 2: Total Budget */}
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 backdrop-blur-xl shadow-lg">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-[10px] font-bold uppercase tracking-wider">Total Project Budget</span>
                <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
              </div>
              <p className="text-base font-extrabold text-emerald-400 font-mono">
                ₹{(projectMeta?.total_budget || 750000000).toLocaleString("en-IN")}
              </p>
              <p className="text-[11px] text-slate-400 truncate mt-0.5">
                Spent: ₹{(projectMeta?.spent_to_date || 182000000).toLocaleString("en-IN")}
              </p>
            </div>

            {/* Metric 3: Active Schedule Tasks */}
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 backdrop-blur-xl shadow-lg">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-[10px] font-bold uppercase tracking-wider">CPM Tasks Tracked</span>
                <Clock className="h-3.5 w-3.5 text-blue-400" />
              </div>
              <p className="text-base font-extrabold text-slate-100 font-mono">
                {taskCount || 5} Tasks Active
              </p>
              <p className="text-[11px] text-slate-400 truncate mt-0.5">
                Across {contractorCount || 3} Trade Contractors
              </p>
            </div>

            {/* Metric 4: Safety Gate Protocol */}
            <div className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 backdrop-blur-xl shadow-lg">
              <div className="flex items-center justify-between text-slate-400 mb-1">
                <span className="text-[10px] font-bold uppercase tracking-wider">Safety Governance</span>
                <ShieldCheck className="h-3.5 w-3.5 text-purple-400" />
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm font-bold text-slate-100">5-Tier Filter Live</span>
              </div>
              <p className="text-[11px] text-slate-400 truncate mt-0.5">
                Physical Gate Confirmation
              </p>
            </div>
          </div>

          {/* Core Event Intake & Multi-Agent Reasoning Component */}
          <EventInput />

        </div>
      </main>
    </BeamsBackground>
  );
}
