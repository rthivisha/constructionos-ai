"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  ShieldCheck, 
  DollarSign, 
  Sliders, 
  History, 
  Menu, 
  X, 
  Sparkles,
  Layers
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    // Ping backend root to check live status
    const ping = async () => {
      try {
        const rawBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${rawBaseUrl.replace(/\/+$/, '')}/`, { cache: 'no-store' });
        setApiOnline(res.ok);
      } catch {
        setApiOnline(false);
      }
    };
    ping();
    const interval = setInterval(ping, 15000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard, tag: "Live" },
    { href: "/compliance", label: "Safety & Compliance", icon: ShieldCheck, tag: "OSHA" },
    { href: "/financials", label: "Cost & CPM", icon: DollarSign, tag: "CPM" },
    { href: "/setup", label: "Project Setup", icon: Sliders, tag: "Config" },
    { href: "/audit", label: "Audit & Telemetry", icon: History, tag: "Logs" },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl transition-all">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">
          
          {/* Logo & Brand */}
          <Link href="/" className="flex items-center gap-3 group shrink-0">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 via-blue-600 to-indigo-600 text-white font-black text-sm shadow-lg shadow-sky-500/20 transition-transform duration-300 group-hover:scale-105">
              <Layers className="h-4 w-4" />
              <div className="absolute inset-0 rounded-xl bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold tracking-wider text-sm text-slate-100 group-hover:text-white transition">
                  CONSTRUCTION<span className="text-sky-400">OS</span>
                </span>
                <span className="rounded bg-sky-500/10 border border-sky-500/20 px-1.5 py-0.2 text-[9px] font-bold text-sky-400 font-mono uppercase">
                  v2.6
                </span>
              </div>
              <span className="text-[10px] text-slate-400 block leading-none font-medium">
                Multi-Agent Cockpit
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href;

              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`relative flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                    isActive
                      ? "text-sky-400 bg-sky-500/10 border border-sky-500/25 shadow-[0_0_15px_-3px_rgba(56,189,248,0.2)]"
                      : "text-slate-400 hover:text-slate-100 hover:bg-slate-900/60 border border-transparent"
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${isActive ? "text-sky-400" : "text-slate-400"}`} />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Status Badge & Mobile Hamburger */}
          <div className="flex items-center gap-3">
            {/* Live Backend Telemetry Pill */}
            <div className="hidden sm:inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/80 px-3 py-1 text-[11px] font-medium">
              <span
                className={`h-2 w-2 rounded-full ${
                  apiOnline === true
                    ? "bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]"
                    : apiOnline === false
                    ? "bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.8)]"
                    : "bg-amber-400 animate-ping"
                }`}
              />
              <span className="font-mono text-slate-400 text-[10px]">
                {apiOnline === true ? "BACKEND ONLINE" : apiOnline === false ? "BACKEND OFFLINE" : "CHECKING..."}
              </span>
            </div>

            {/* Mobile Menu Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden inline-flex items-center justify-center p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-900 border border-slate-800 focus:outline-none"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>

        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-800/80 bg-slate-950/95 px-4 py-4 space-y-1.5 backdrop-blur-2xl">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href;

            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center justify-between px-4 py-3 rounded-xl text-sm font-semibold transition ${
                  isActive
                    ? "text-sky-400 bg-sky-500/10 border border-sky-500/25"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  <span>{link.label}</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                  {link.tag}
                </span>
              </Link>
            );
          })}
          
          <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400 px-2">
            <span>System Pipeline:</span>
            <span className="font-mono text-emerald-400 font-bold">ACTIVE (GEMINI 3.5)</span>
          </div>
        </div>
      )}
    </header>
  );
}
