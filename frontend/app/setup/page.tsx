"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '../lib/api';
import { 
  Building2, 
  Users, 
  Layers, 
  ShieldCheck, 
  CalendarClock, 
  Plus, 
  Trash2, 
  Save, 
  CheckCircle2, 
  AlertCircle, 
  ArrowLeft,
  DollarSign,
  MapPin,
  FileText
} from 'lucide-react';

interface ProjectMeta {
  name: string;
  location: string;
  total_budget: number;
  spent_to_date: number;
}

interface Contractor {
  name: string;
  scope: string;
  daily_operating_cost: number;
  daily_delay_penalty: number;
  active_workers: number;
}

interface Division {
  id: string;
  name: string;
  lead_contractor: string;
}

interface RegulatoryKb {
  code: string;
  description: string;
  trigger_condition: string;
}

interface ScheduleTask {
  task_id: string;
  division_id: string;
  task_name: string;
  duration: number;
  is_critical_path: number; // 0 or 1
  dependencies: string;
}

export default function SetupPage() {
  const [activeTab, setActiveTab] = useState<'meta' | 'contractors' | 'divisions' | 'regulatory' | 'tasks'>('meta');
  
  // States for database entities
  const [meta, setMeta] = useState<ProjectMeta>({ name: '', location: '', total_budget: 0, spent_to_date: 0 });
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [divisions, setDivisions] = useState<Division[]>([]);
  const [regulatory, setRegulatory] = useState<RegulatoryKb[]>([]);
  const [tasks, setTasks] = useState<ScheduleTask[]>([]);
  
  // Loading & notification states
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Trigger conditions list (shared vocabulary enum values)
  const triggerConditions = ["excavation", "work_at_height", "toxic_gas", "extreme_weather"];

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await api.getProjectSetup();
      setMeta(data.project_meta);
      setContractors(data.contractors);
      setDivisions(data.divisions);
      setRegulatory(data.regulatory_kb);
      setTasks(data.schedule_tasks);
    } catch (err: any) {
      showNotification('error', `Failed to load data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => {
      setNotification(null);
    }, 5000);
  };

  // Generic change handler for Project Metadata
  const handleMetaChange = (field: keyof ProjectMeta, value: any) => {
    setMeta((prev) => ({
      ...prev,
      [field]: field === 'total_budget' || field === 'spent_to_date' ? parseFloat(value) || 0 : value
    }));
  };

  // Generic handlers for tables (add, remove, update)
  const updateRow = <T,>(list: T[], index: number, field: keyof T, value: any, setter: (val: T[]) => void) => {
    const updated = [...list];
    updated[index] = {
      ...updated[index],
      [field]: value
    };
    setter(updated);
  };

  const addRow = <T,>(emptyObj: T, list: T[], setter: (val: T[]) => void) => {
    setter([...list, emptyObj]);
  };

  const removeRow = <T,>(index: number, list: T[], setter: (val: T[]) => void) => {
    setter(list.filter((_, i) => i !== index));
  };

  // API save methods
  const saveMeta = async () => {
    if (meta.total_budget < 0 || meta.spent_to_date < 0) {
      showNotification('error', 'Budget and spent values must be non-negative.');
      return;
    }
    setSaving(true);
    try {
      await api.updateProjectMeta(meta);
      showNotification('success', 'Project metadata updated successfully.');
    } catch (err: any) {
      showNotification('error', err.message);
    } finally {
      setSaving(false);
    }
  };

  const saveContractors = async () => {
    for (const c of contractors) {
      if (!c.name.trim()) {
        showNotification('error', 'Contractor name cannot be empty.');
        return;
      }
      if (c.daily_operating_cost < 0 || c.daily_delay_penalty < 0 || c.active_workers < 0) {
        showNotification('error', 'Contractor values (costs, workers) must be non-negative.');
        return;
      }
    }
    setSaving(true);
    try {
      await api.updateContractors(contractors);
      showNotification('success', 'Contractor SLAs saved successfully.');
    } catch (err: any) {
      showNotification('error', err.message);
    } finally {
      setSaving(false);
    }
  };

  const saveDivisions = async () => {
    for (const d of divisions) {
      if (!d.id.trim() || !d.name.trim()) {
        showNotification('error', 'Division ID and Name cannot be empty.');
        return;
      }
    }
    setSaving(true);
    try {
      await api.updateDivisions(divisions);
      showNotification('success', 'Project divisions saved successfully.');
    } catch (err: any) {
      showNotification('error', err.message);
    } finally {
      setSaving(false);
    }
  };

  const saveRegulatory = async () => {
    for (const r of regulatory) {
      if (!r.code.trim() || !r.description.trim()) {
        showNotification('error', 'Regulatory compliance code and description cannot be empty.');
        return;
      }
    }
    setSaving(true);
    try {
      await api.updateRegulatory(regulatory);
      showNotification('success', 'Regulatory knowledge base saved successfully.');
    } catch (err: any) {
      showNotification('error', err.message);
    } finally {
      setSaving(false);
    }
  };

  const saveTasks = async () => {
    for (const t of tasks) {
      if (!t.task_id.trim() || !t.task_name.trim()) {
        showNotification('error', 'Task ID and Task Name cannot be empty.');
        return;
      }
      if (t.duration < 0) {
        showNotification('error', 'Task duration must be non-negative.');
        return;
      }
    }
    setSaving(true);
    try {
      await api.updateTasks(tasks);
      showNotification('success', 'Schedule tasks saved successfully.');
    } catch (err: any) {
      showNotification('error', err.message);
    } finally {
      setSaving(false);
    }
  };

  const tabs = [
    { id: 'meta', label: 'Project Metadata', icon: Building2 },
    { id: 'contractors', label: 'Contractor SLAs', icon: Users },
    { id: 'divisions', label: 'Divisions', icon: Layers },
    { id: 'regulatory', label: 'Regulatory KB', icon: ShieldCheck },
    { id: 'tasks', label: 'Schedule Tasks', icon: CalendarClock },
  ] as const;

  if (loading) {
    return (
      <div className="min-h-[70vh] bg-slate-950 flex flex-col items-center justify-center text-slate-100 font-sans">
        <div className="w-12 h-12 border-4 border-sky-500/20 border-t-sky-400 rounded-full animate-spin mb-4"></div>
        <p className="text-sky-400 tracking-wider text-xs font-semibold uppercase animate-pulse">Loading Workspace Configuration...</p>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-slate-950 text-slate-100 py-8 sm:py-12 relative overflow-hidden">
      
      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-20 right-6 z-50 p-4 rounded-xl shadow-2xl backdrop-blur-xl border flex items-center gap-3 animate-fade-in max-w-md ${
          notification.type === 'success' 
            ? 'bg-emerald-950/90 border-emerald-500/40 text-emerald-300' 
            : 'bg-rose-950/90 border-rose-500/40 text-rose-300'
        }`}>
          {notification.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
          <p className="text-xs font-medium">{notification.message}</p>
        </div>
      )}

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-slate-800/80">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-400">
              <Building2 className="h-3.5 w-3.5" />
              <span>Project Configuration Core</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-100">
              Project Data &{" "}
              <span className="bg-gradient-to-r from-sky-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
                System Setup
              </span>
            </h1>
            <p className="max-w-2xl text-xs sm:text-sm text-slate-400 leading-relaxed">
              Configure project scope, assign contractor operating parameters, maintain statutory compliance libraries, and define CPM task dependencies.
            </p>
          </div>

          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:border-sky-500/40 hover:text-white transition"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to Dashboard</span>
          </Link>
        </div>

        {/* Tab Navigation */}
        <div className="flex flex-wrap gap-2 rounded-2xl border border-slate-800/80 bg-slate-900/40 p-1.5 backdrop-blur-xl">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition ${
                  isActive
                    ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white font-bold shadow-lg shadow-sky-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Container */}
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 sm:p-8 backdrop-blur-xl shadow-xl">
          
          {/* TAB 1: METADATA */}
          {activeTab === 'meta' && (
            <div className="space-y-6">
              <div className="border-b border-slate-800 pb-4">
                <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-sky-400" />
                  General Project Information
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">Primary project identity, physical site coordinates, and macro financial boundaries.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <FileText className="h-3 w-3 text-sky-400" />
                    Project Name
                  </label>
                  <input
                    type="text"
                    value={meta.name}
                    onChange={(e) => handleMetaChange('name', e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                    placeholder="e.g. Metro Line Extension"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <MapPin className="h-3 w-3 text-sky-400" />
                    Site Location
                  </label>
                  <input
                    type="text"
                    value={meta.location}
                    onChange={(e) => handleMetaChange('location', e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-100 placeholder-slate-600 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                    placeholder="e.g. Bengaluru, India"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <DollarSign className="h-3 w-3 text-emerald-400" />
                    Total Project Budget (₹)
                  </label>
                  <input
                    type="number"
                    value={meta.total_budget || ''}
                    onChange={(e) => handleMetaChange('total_budget', e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-100 font-mono focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                    placeholder="e.g. 750000000"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <DollarSign className="h-3 w-3 text-amber-400" />
                    Capital Spent to Date (₹)
                  </label>
                  <input
                    type="number"
                    value={meta.spent_to_date || ''}
                    onChange={(e) => handleMetaChange('spent_to_date', e.target.value)}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-xs text-slate-100 font-mono focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
                    placeholder="e.g. 182000000"
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end">
                <button
                  type="button"
                  onClick={saveMeta}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-sky-500/20 hover:from-sky-500 hover:to-blue-500 disabled:opacity-50 transition"
                >
                  <Save className="h-3.5 w-3.5" />
                  <span>{saving ? 'Saving...' : 'Save Project Metadata'}</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: CONTRACTORS */}
          {activeTab === 'contractors' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <Users className="h-4 w-4 text-sky-400" />
                    Contractor SLAs & Delay Rates
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">Parameters applied during multi-agent financial impact assessments.</p>
                </div>
                <button
                  type="button"
                  onClick={() => addRow({ name: '', scope: '', daily_operating_cost: 0, daily_delay_penalty: 0, active_workers: 0 }, contractors, setContractors)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-sky-500/30 bg-sky-500/10 px-3.5 py-2 text-xs font-bold text-sky-400 hover:bg-sky-500/20 transition"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Contractor</span>
                </button>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                      <th className="p-4">Contractor Name</th>
                      <th className="p-4">Scope of Work</th>
                      <th className="p-4">Daily Cost (₹)</th>
                      <th className="p-4">Delay Penalty (₹)</th>
                      <th className="p-4">Active Labor</th>
                      <th className="p-4 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {contractors.map((c, i) => (
                      <tr key={i} className="hover:bg-slate-900/40 transition">
                        <td className="p-4 min-w-[180px]">
                          <input
                            type="text"
                            value={c.name}
                            onChange={(e) => updateRow(contractors, i, 'name', e.target.value, setContractors)}
                            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 focus:border-sky-500 focus:outline-none"
                            placeholder="e.g. L&T Construction"
                          />
                        </td>
                        <td className="p-4 min-w-[200px]">
                          <input
                            type="text"
                            value={c.scope}
                            onChange={(e) => updateRow(contractors, i, 'scope', e.target.value, setContractors)}
                            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 focus:border-sky-500 focus:outline-none"
                            placeholder="e.g. Civil & Structural"
                          />
                        </td>
                        <td className="p-4">
                          <input
                            type="number"
                            value={c.daily_operating_cost || ''}
                            onChange={(e) => updateRow(contractors, i, 'daily_operating_cost', parseFloat(e.target.value) || 0, setContractors)}
                            className="w-28 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
                          />
                        </td>
                        <td className="p-4">
                          <input
                            type="number"
                            value={c.daily_delay_penalty || ''}
                            onChange={(e) => updateRow(contractors, i, 'daily_delay_penalty', parseFloat(e.target.value) || 0, setContractors)}
                            className="w-28 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
                          />
                        </td>
                        <td className="p-4">
                          <input
                            type="number"
                            value={c.active_workers || ''}
                            onChange={(e) => updateRow(contractors, i, 'active_workers', parseInt(e.target.value) || 0, setContractors)}
                            className="w-20 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
                          />
                        </td>
                        <td className="p-4 text-center">
                          <button
                            type="button"
                            onClick={() => removeRow(i, contractors, setContractors)}
                            className="p-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-lg transition"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end">
                <button
                  type="button"
                  onClick={saveContractors}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-sky-500/20 hover:from-sky-500 hover:to-blue-500 disabled:opacity-50 transition"
                >
                  <Save className="h-3.5 w-3.5" />
                  <span>{saving ? 'Saving...' : 'Save Contractor SLAs'}</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: DIVISIONS */}
          {activeTab === 'divisions' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <Layers className="h-4 w-4 text-sky-400" />
                    Project Divisions
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">WBS divisions and assigned lead trade contractors.</p>
                </div>
                <button
                  type="button"
                  onClick={() => addRow({ id: '', name: '', lead_contractor: contractors[0]?.name || '' }, divisions, setDivisions)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-sky-500/30 bg-sky-500/10 px-3.5 py-2 text-xs font-bold text-sky-400 hover:bg-sky-500/20 transition"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Division</span>
                </button>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                      <th className="p-4">Division Code</th>
                      <th className="p-4">Division Name</th>
                      <th className="p-4">Lead Trade Contractor</th>
                      <th className="p-4 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {divisions.map((d, i) => (
                      <tr key={i} className="hover:bg-slate-900/40 transition">
                        <td className="p-4">
                          <input
                            type="text"
                            value={d.id}
                            onChange={(e) => updateRow(divisions, i, 'id', e.target.value.toUpperCase().replace(/\s+/g, ''), setDivisions)}
                            className="w-36 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 font-mono font-bold focus:border-sky-500 focus:outline-none"
                            placeholder="DIV-CIVIL"
                          />
                        </td>
                        <td className="p-4">
                          <input
                            type="text"
                            value={d.name}
                            onChange={(e) => updateRow(divisions, i, 'name', e.target.value, setDivisions)}
                            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 focus:border-sky-500 focus:outline-none"
                            placeholder="Civil & Structural Works"
                          />
                        </td>
                        <td className="p-4">
                          <select
                            value={d.lead_contractor}
                            onChange={(e) => updateRow(divisions, i, 'lead_contractor', e.target.value, setDivisions)}
                            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 focus:border-sky-500 focus:outline-none"
                          >
                            <option value="">-- Assign Contractor --</option>
                            {contractors.map((c, idx) => (
                              <option key={idx} value={c.name}>{c.name}</option>
                            ))}
                          </select>
                        </td>
                        <td className="p-4 text-center">
                          <button
                            type="button"
                            onClick={() => removeRow(i, divisions, setDivisions)}
                            className="p-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-lg transition"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end">
                <button
                  type="button"
                  onClick={saveDivisions}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-sky-500/20 hover:from-sky-500 hover:to-blue-500 disabled:opacity-50 transition"
                >
                  <Save className="h-3.5 w-3.5" />
                  <span>{saving ? 'Saving...' : 'Save Divisions'}</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 4: REGULATORY */}
          {activeTab === 'regulatory' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    Regulatory Compliance Rules
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">Statutory codes and triggers checked by the Safety Agent.</p>
                </div>
                <button
                  type="button"
                  onClick={() => addRow({ code: '', description: '', trigger_condition: triggerConditions[0] }, regulatory, setRegulatory)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2 text-xs font-bold text-emerald-400 hover:bg-emerald-500/20 transition"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Rule</span>
                </button>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                      <th className="p-4">Statutory Code</th>
                      <th className="p-4">Description</th>
                      <th className="p-4">Trigger Condition</th>
                      <th className="p-4 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {regulatory.map((r, i) => (
                      <tr key={i} className="hover:bg-slate-900/40 transition">
                        <td className="p-4">
                          <input
                            type="text"
                            value={r.code}
                            onChange={(e) => updateRow(regulatory, i, 'code', e.target.value.toUpperCase().replace(/\s+/g, ''), setRegulatory)}
                            className="w-40 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-emerald-400 font-mono font-bold focus:border-emerald-500 focus:outline-none"
                            placeholder="BOCW_SEC_40"
                          />
                        </td>
                        <td className="p-4">
                          <textarea
                            value={r.description}
                            onChange={(e) => updateRow(regulatory, i, 'description', e.target.value, setRegulatory)}
                            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none min-h-[44px]"
                            placeholder="Rule requirement details..."
                          />
                        </td>
                        <td className="p-4">
                          <select
                            value={r.trigger_condition}
                            onChange={(e) => updateRow(regulatory, i, 'trigger_condition', e.target.value, setRegulatory)}
                            className="w-44 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 font-mono uppercase focus:border-emerald-500 focus:outline-none"
                          >
                            {triggerConditions.map((tc, idx) => (
                              <option key={idx} value={tc}>{tc}</option>
                            ))}
                          </select>
                        </td>
                        <td className="p-4 text-center">
                          <button
                            type="button"
                            onClick={() => removeRow(i, regulatory, setRegulatory)}
                            className="p-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-lg transition"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end">
                <button
                  type="button"
                  onClick={saveRegulatory}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-emerald-500/20 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 transition"
                >
                  <Save className="h-3.5 w-3.5" />
                  <span>{saving ? 'Saving...' : 'Save Regulatory KB'}</span>
                </button>
              </div>
            </div>
          )}

          {/* TAB 5: TASKS */}
          {activeTab === 'tasks' && (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <CalendarClock className="h-4 w-4 text-sky-400" />
                    CPM Schedule Tasks
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">Tasks, durations, critical path status, and dependency sequences.</p>
                </div>
                <button
                  type="button"
                  onClick={() => addRow({ task_id: '', division_id: divisions[0]?.id || '', task_name: '', duration: 1, is_critical_path: 0, dependencies: '' }, tasks, setTasks)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-sky-500/30 bg-sky-500/10 px-3.5 py-2 text-xs font-bold text-sky-400 hover:bg-sky-500/20 transition"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Add Task</span>
                </button>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                      <th className="p-4">Task ID</th>
                      <th className="p-4">Division</th>
                      <th className="p-4">Task Name</th>
                      <th className="p-4">Duration (Days)</th>
                      <th className="p-4 text-center">Critical Path</th>
                      <th className="p-4">Predecessors</th>
                      <th className="p-4 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {tasks.map((t, i) => (
                      <tr key={i} className="hover:bg-slate-900/40 transition">
                        <td className="p-4">
                          <input
                            type="text"
                            value={t.task_id}
                            onChange={(e) => updateRow(tasks, i, 'task_id', e.target.value.toUpperCase().replace(/\s+/g, ''), setTasks)}
                            className="w-24 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-sky-400 font-mono font-bold focus:border-sky-500 focus:outline-none"
                            placeholder="T1"
                          />
                        </td>
                        <td className="p-4">
                          <select
                            value={t.division_id}
                            onChange={(e) => updateRow(tasks, i, 'division_id', e.target.value, setTasks)}
                            className="w-36 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
                          >
                            <option value="">-- Division --</option>
                            {divisions.map((d, idx) => (
                              <option key={idx} value={d.id}>{d.id}</option>
                            ))}
                          </select>
                        </td>
                        <td className="p-4 min-w-[180px]">
                          <input
                            type="text"
                            value={t.task_name}
                            onChange={(e) => updateRow(tasks, i, 'task_name', e.target.value, setTasks)}
                            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 focus:border-sky-500 focus:outline-none"
                            placeholder="Task Name"
                          />
                        </td>
                        <td className="p-4">
                          <input
                            type="number"
                            value={t.duration || ''}
                            onChange={(e) => updateRow(tasks, i, 'duration', parseInt(e.target.value) || 0, setTasks)}
                            className="w-20 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
                          />
                        </td>
                        <td className="p-4 text-center">
                          <input
                            type="checkbox"
                            checked={t.is_critical_path === 1}
                            onChange={(e) => updateRow(tasks, i, 'is_critical_path', e.target.checked ? 1 : 0, setTasks)}
                            className="h-4 w-4 rounded border-slate-800 bg-slate-950 text-sky-500 focus:ring-sky-500"
                          />
                        </td>
                        <td className="p-4">
                          <input
                            type="text"
                            value={t.dependencies}
                            onChange={(e) => updateRow(tasks, i, 'dependencies', e.target.value.toUpperCase().replace(/\s+/g, ''), setTasks)}
                            className="w-28 rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-100 font-mono focus:border-sky-500 focus:outline-none"
                            placeholder="e.g. T1,T2"
                          />
                        </td>
                        <td className="p-4 text-center">
                          <button
                            type="button"
                            onClick={() => removeRow(i, tasks, setTasks)}
                            className="p-1.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-lg transition"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end">
                <button
                  type="button"
                  onClick={saveTasks}
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-sky-500/20 hover:from-sky-500 hover:to-blue-500 disabled:opacity-50 transition"
                >
                  <Save className="h-3.5 w-3.5" />
                  <span>{saving ? 'Saving...' : 'Save Schedule Tasks'}</span>
                </button>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
