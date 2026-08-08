"use client";

import React from 'react';
import Link from 'next/link';
import EventInput from './components/EventInput';

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Sleek Top Navigation Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
              C
            </div>
            <div>
              <span className="font-extrabold text-slate-100 tracking-wider text-sm block">CONSTRUCTION OS</span>
              <span className="text-[10px] text-blue-400 block leading-none font-semibold uppercase tracking-wider">AI Operations Manager</span>
            </div>
          </div>
          
          <nav className="flex items-center gap-4">
            <Link 
              href="/setup" 
              className="inline-flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-xs font-semibold text-slate-300 transition hover:bg-slate-800 hover:text-slate-100 focus:outline-none"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Configure Project DB
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Body Grid Background */}
      <main className="flex-1 relative">
        {/* Subtle grid accent background */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b12_1px,transparent_1px),linear-gradient(to_bottom,#1e293b12_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
        
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-10 space-y-10 relative">
          
          {/* Dashboard Header */}
          <div className="space-y-2">
            <h1 className="text-3xl font-black tracking-tight sm:text-4xl text-slate-100">
              Operations Control <span className="bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">Dashboard</span>
            </h1>
            <p className="max-w-2xl text-sm text-slate-400 font-light">
              Observe and resolve jobsite disruptions. Run structured compliance and schedule impact analysis via the multi-agent reasoning chain.
            </p>
          </div>

          {/* Event pipeline container */}
          <EventInput />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 bg-slate-950">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <p>© 2026 ConstructionOS. All rights reserved.</p>
          <div className="flex gap-4">
            <span className="hover:text-slate-300 cursor-pointer">Security Protocol</span>
            <span className="hover:text-slate-300 cursor-pointer">API Integration Docs</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
