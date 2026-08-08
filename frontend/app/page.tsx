"use client";

import React from "react";
import Link from "next/link";
import EventInput from "./components/EventInput";
import BeamsBackground from "./components/kokonut/BeamsBackground";
import { Settings } from "lucide-react";

export default function DashboardPage() {
  return (
    <BeamsBackground intensity="subtle" className="min-h-screen text-slate-100 flex flex-col">
      {/* Sticky nav */}
      <header className="sticky top-0 z-50 border-b border-white/6 bg-white/[0.03] backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center font-black text-white text-sm shadow-lg shadow-sky-500/25">
              C
            </div>
            <div>
              <span className="font-black text-slate-100 tracking-wider text-sm block leading-tight">CONSTRUCTION OS</span>
              <span className="text-[10px] text-sky-400 block leading-none font-semibold uppercase tracking-widest">AI Operations Manager</span>
            </div>
          </div>

          <nav>
            <Link
              href="/setup"
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-semibold text-slate-300 transition-all hover:bg-white/8 hover:text-slate-100 hover:border-white/20 focus:outline-none"
            >
              <Settings className="h-3.5 w-3.5" />
              Configure Project DB
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 space-y-10">
          <div className="space-y-3">
            <h1 className="text-4xl font-black tracking-tight sm:text-5xl text-slate-100 leading-none">
              Operations Control{" "}
              <span className="bg-gradient-to-r from-sky-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
                Dashboard
              </span>
            </h1>
            <p className="max-w-2xl text-sm text-slate-400 font-light leading-relaxed">
              Observe and resolve jobsite disruptions. Run structured compliance and schedule impact analysis via the multi-agent reasoning chain.
            </p>
          </div>

          <EventInput />
        </div>
      </main>

      <footer className="border-t border-white/6 py-6 bg-white/[0.01]">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
          <p>© 2026 ConstructionOS. All rights reserved.</p>
          <div className="flex gap-4">
            <span className="hover:text-slate-400 cursor-pointer transition-colors">Security Protocol</span>
            <span className="hover:text-slate-400 cursor-pointer transition-colors">API Integration Docs</span>
          </div>
        </div>
      </footer>
    </BeamsBackground>
  );
}
