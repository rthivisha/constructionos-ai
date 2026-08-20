"use client";

import React from "react";
import Link from "next/link";
import { Shield, Cpu, Database, CheckCircle2 } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-slate-800/80 bg-slate-950/60 py-8 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          
          {/* Brand & Mission */}
          <div className="space-y-1 text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2">
              <span className="font-extrabold text-sm text-slate-200 tracking-wider">
                CONSTRUCTION<span className="text-sky-400">OS</span>
              </span>
              <span className="text-xs text-slate-400">• Multi-Agent Site Intelligence</span>
            </div>
            <p className="text-xs text-slate-400 max-w-md">
              Autonomous orchestration for OSHA/BOCW safety compliance, CPM schedule impacts, and real-time trade-off resolution.
            </p>
          </div>

          {/* System Protocols & Metrics */}
          <div className="flex flex-wrap items-center justify-center gap-4 text-xs font-medium text-slate-400">
            <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5">
              <Shield className="h-3.5 w-3.5 text-emerald-400" />
              <span>OSHA / BOCW Compliant</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5">
              <Database className="h-3.5 w-3.5 text-sky-400" />
              <span>SQLite Cache Enabled</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5">
              <Cpu className="h-3.5 w-3.5 text-purple-400" />
              <span>Gemini 3.5 Flash Active</span>
            </div>
          </div>

          {/* Copyright & Links */}
          <div className="flex flex-col sm:flex-row items-center gap-4 text-xs text-slate-400">
            <p>© 2026 ConstructionOS</p>
            <div className="flex items-center gap-3">
              <Link href="/setup" className="hover:text-sky-400 transition">Setup</Link>
              <span>•</span>
              <Link href="/compliance" className="hover:text-sky-400 transition">Rules</Link>
              <span>•</span>
              <Link href="/audit" className="hover:text-sky-400 transition">Audit</Link>
            </div>
          </div>

        </div>
      </div>
    </footer>
  );
}
