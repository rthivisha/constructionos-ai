"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Search, 
  BookOpen, 
  Layers, 
  CheckCircle2, 
  ExternalLink,
  Lock,
  Flame,
  ArrowRight,
  Filter
} from "lucide-react";
import { api } from "../lib/api";

interface RegulatoryRule {
  code: string;
  description: string;
  trigger_condition: string;
}

export default function CompliancePage() {
  const [rules, setRules] = useState<RegulatoryRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCondition, setSelectedCondition] = useState<string>("ALL");

  useEffect(() => {
    async function fetchRules() {
      try {
        const data = await api.getProjectSetup();
        setRules(data.regulatory_kb || []);
      } catch (err) {
        console.error("Failed to load regulatory rules:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchRules();
  }, []);

  const triggerConditions = ["ALL", "excavation", "work_at_height", "toxic_gas", "extreme_weather"];

  const filteredRules = rules.filter((r) => {
    const matchesSearch =
      r.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCondition =
      selectedCondition === "ALL" || r.trigger_condition.toLowerCase() === selectedCondition.toLowerCase();
    return matchesSearch && matchesCondition;
  });

  const safetyTiers = [
    {
      name: "SAFE / CLEAR",
      tagColor: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
      dotColor: "bg-emerald-400",
      description: "No statutory safety rule breached. Trade-off allows work to proceed without stop.",
      sampleAction: "Material shipment delays with zero hazardous activity in progress."
    },
    {
      name: "CONDITIONAL",
      tagColor: "bg-amber-500/10 text-amber-400 border-amber-500/30",
      dotColor: "bg-amber-400",
      description: "Requires physical verification of site controls by Site Manager before continuation.",
      sampleAction: "Chemical odors requiring ventilation sign-off before electricians enter shaft."
    },
    {
      name: "BLOCKED / HARD STOP",
      tagColor: "bg-red-500/10 text-red-400 border-red-500/30",
      dotColor: "bg-red-400 animate-ping",
      description: "Immediate mandatory suspension of operations under statutory safety acts.",
      sampleAction: "Crane hoist brake failure, untrenched deep excavations, extreme gale warnings."
    },
    {
      name: "ESCALATE",
      tagColor: "bg-purple-500/10 text-purple-300 border-purple-500/30",
      dotColor: "bg-purple-400 animate-pulse",
      description: "High-consequence emergency requiring external project director & safety auditor intervention.",
      sampleAction: "Structural foundation cracking or major hazardous chemical leakage."
    },
    {
      name: "UNKNOWN / AMBIGUOUS",
      tagColor: "bg-blue-500/10 text-blue-400 border-blue-500/30",
      dotColor: "bg-blue-400",
      description: "Event text lacks verified task ID or location. Defaults to conservative safety hold.",
      sampleAction: "Vague incident report submitted without specifying zone or task code."
    }
  ];

  return (
    <div className="min-h-full bg-slate-950 text-slate-100 py-8 sm:py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-10">
        
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-slate-800/80">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>Statutory Knowledge Base & OSHA Governance</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-100">
              Safety & Regulatory{" "}
              <span className="bg-gradient-to-r from-emerald-400 via-teal-400 to-sky-400 bg-clip-text text-transparent">
                Compliance Matrix
              </span>
            </h1>
            <p className="max-w-2xl text-xs sm:text-sm text-slate-400 leading-relaxed">
              ConstructionOS enforces strict regulatory boundaries derived from the Building and Other Construction Workers Act (BOCW 1996), Factory Act 1948, and OSHA CFR 1926 standards.
            </p>
          </div>

          <Link
            href="/setup"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:border-emerald-500/40 hover:text-white transition"
          >
            <span>Manage Regulatory KB</span>
            <ExternalLink className="h-3.5 w-3.5 text-slate-400" />
          </Link>
        </div>

        {/* 5-Tier Safety Classification Taxonomy */}
        <div className="space-y-4">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Pipeline Protocol</span>
            <h2 className="text-xl font-extrabold text-slate-100">5-Tier Action Classification Filter</h2>
            <p className="text-xs text-slate-400 mt-0.5">Every site disruption event is mapped into one of these strict safety decision tiers:</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {safetyTiers.map((tier, idx) => (
              <div
                key={idx}
                className="relative overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-900/40 p-5 backdrop-blur-md transition-all hover:border-slate-700"
              >
                <div className="flex items-center justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${tier.dotColor}`} />
                    <span className="font-extrabold text-sm text-slate-200">{tier.name}</span>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${tier.tagColor}`}>
                    Tier {idx + 1}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed mb-3">{tier.description}</p>
                <div className="rounded-lg bg-slate-950/60 border border-slate-800/60 p-2.5 text-[11px] text-slate-400">
                  <span className="font-semibold text-slate-300 block mb-0.5">Example:</span>
                  {tier.sampleAction}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Interactive Regulatory Rules Table */}
        <div className="space-y-5 rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 sm:p-8 backdrop-blur-xl shadow-xl">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-emerald-400" />
                Active Regulatory Knowledge Base
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Statutory safety rules indexed in the SQLite knowledge base used during live Gemini reasoning.
              </p>
            </div>

            {/* Filter and Search */}
            <div className="flex flex-wrap items-center gap-3">
              {/* Search Bar */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search rules, codes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="rounded-xl border border-slate-800 bg-slate-950 px-3.5 py-2 pl-9 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500/80 focus:outline-none focus:ring-1 focus:ring-emerald-500/40 w-48 sm:w-56"
                />
              </div>

              {/* Trigger Filter Tabs */}
              <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950 p-1">
                {triggerConditions.map((cond) => (
                  <button
                    key={cond}
                    type="button"
                    onClick={() => setSelectedCondition(cond)}
                    className={`rounded-lg px-2.5 py-1 text-[10px] font-bold uppercase transition ${
                      selectedCondition === cond
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {cond}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                  <th className="p-4">Statutory Code</th>
                  <th className="p-4">Regulatory Description</th>
                  <th className="p-4">Trigger Condition</th>
                  <th className="p-4">Hard-Stop Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loading ? (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-slate-400">
                      <div className="inline-flex items-center gap-2">
                        <div className="h-4 w-4 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin" />
                        <span>Loading regulatory database...</span>
                      </div>
                    </td>
                  </tr>
                ) : filteredRules.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-slate-400">
                      No regulatory rules match your filter criteria.
                    </td>
                  </tr>
                ) : (
                  filteredRules.map((rule, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/40 transition">
                      <td className="p-4 font-mono font-bold text-emerald-400 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Lock className="h-3 w-3 text-emerald-500" />
                          <span>{rule.code}</span>
                        </div>
                      </td>
                      <td className="p-4 text-slate-200 leading-relaxed max-w-md">
                        {rule.description}
                      </td>
                      <td className="p-4 whitespace-nowrap">
                        <span className="rounded-md border border-slate-700/80 bg-slate-900 px-2.5 py-1 text-[10px] font-mono font-semibold text-slate-300 uppercase">
                          {rule.trigger_condition}
                        </span>
                      </td>
                      <td className="p-4 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-400 bg-red-950/50 border border-red-800/50 px-2.5 py-1 rounded-md">
                          <ShieldAlert className="h-3 w-3" />
                          MANDATORY HALT
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400 pt-2">
            <span>Showing {filteredRules.length} statutory rule definitions</span>
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-sky-400 hover:text-sky-300 font-bold"
            >
              <span>Test against live event report on Dashboard</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
