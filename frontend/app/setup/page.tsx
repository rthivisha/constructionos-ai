"use client";

import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

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
    }, 6000);
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
    // Validate negative values
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

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100 font-sans">
        <div className="w-16 h-16 border-4 border-cyan-500/20 border-t-cyan-400 rounded-full animate-spin mb-4"></div>
        <p className="text-cyan-400 tracking-wider text-sm font-semibold uppercase animate-pulse">Loading Workspace State...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 md:p-12 relative overflow-hidden">
      
      {/* Background Decorative Glows */}
      <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] bg-cyan-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

      {/* Floating Notification */}
      {notification && (
        <div className={`fixed top-6 right-6 z-50 p-4 rounded-xl shadow-2xl backdrop-blur-md border flex items-center gap-3 animate-slide-in max-w-md ${
          notification.type === 'success' 
            ? 'bg-emerald-950/80 border-emerald-500/30 text-emerald-300' 
            : 'bg-rose-950/80 border-rose-500/30 text-rose-300'
        }`}>
          <span>
            {notification.type === 'success' ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            )}
          </span>
          <p className="text-sm font-medium">{notification.message}</p>
        </div>
      )}

      {/* Main Header */}
      <header className="mb-10 max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="bg-cyan-500/15 text-cyan-400 text-xs px-2.5 py-1 rounded-full border border-cyan-500/25 font-semibold tracking-wider uppercase">Setup Module</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-slate-100 via-slate-100 to-cyan-300 bg-clip-text text-transparent">
            ConstructionOS Setup
          </h1>
          <p className="text-slate-400 text-sm mt-1">Configure project metadata, contractors SLAs, divisions, regulatory libraries, and critical path schedules.</p>
        </div>
        
        {/* Navigation / Main Page Link */}
        <a 
          href="/" 
          className="flex items-center justify-center gap-2 bg-slate-900 border border-slate-700/60 text-slate-300 hover:text-cyan-300 px-5 py-2.5 rounded-xl hover:border-cyan-500/30 transition duration-300 text-sm font-medium hover:shadow-[0_0_15px_rgba(34,211,238,0.05)] cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2a4 4 0 00-4-4H5m0 0l3-3m-3 3l3 3m12 3v-2a4 4 0 00-4-4h-3m0 0l3-3m-3 3l3 3" /></svg>
          Go to Dashboard
        </a>
      </header>

      {/* Tabs Menu */}
      <div className="max-w-7xl mx-auto mb-8 bg-slate-900/60 border border-slate-800/80 p-1.5 rounded-2xl flex flex-wrap gap-1 backdrop-blur-md">
        {(['meta', 'contractors', 'divisions', 'regulatory', 'tasks'] as const).map((tab) => {
          const labels = {
            meta: 'Metadata',
            contractors: 'Contractor SLAs',
            divisions: 'Divisions',
            regulatory: 'Regulatory KB',
            tasks: 'Schedule Tasks',
          };
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 min-w-[120px] py-3 text-center text-sm font-semibold rounded-xl transition duration-300 ${
                isActive 
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-[0_0_20px_rgba(6,182,212,0.3)]' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              {labels[tab]}
            </button>
          );
        })}
      </div>

      {/* Main Workspace Panels */}
      <main className="max-w-7xl mx-auto bg-slate-900/40 border border-slate-800/60 backdrop-blur-md rounded-3xl p-6 md:p-8 min-h-[500px] shadow-[0_20px_50px_rgba(0,0,0,0.3)]">
        
        {/* TAB 1: METADATA */}
        {activeTab === 'meta' && (
          <div className="animate-fade-in space-y-6">
            <div className="border-b border-slate-800/80 pb-4">
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <span className="w-1.5 h-6 bg-cyan-400 rounded-full" />
                Project Metadata
              </h2>
              <p className="text-slate-400 text-xs mt-1">Configure global details including location and total budget state.</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Project Name</label>
                <input 
                  type="text" 
                  value={meta.name}
                  onChange={(e) => handleMetaChange('name', e.target.value)}
                  className="bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-cyan-500 rounded-xl px-4 py-3 text-slate-100 outline-none transition duration-300 text-sm font-medium"
                  placeholder="e.g. Metro Line Extension"
                />
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Location</label>
                <input 
                  type="text" 
                  value={meta.location}
                  onChange={(e) => handleMetaChange('location', e.target.value)}
                  className="bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-cyan-500 rounded-xl px-4 py-3 text-slate-100 outline-none transition duration-300 text-sm font-medium"
                  placeholder="e.g. Bengaluru, India"
                />
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Total Budget (₹ / $)</label>
                <input 
                  type="number" 
                  value={meta.total_budget || ''}
                  onChange={(e) => handleMetaChange('total_budget', e.target.value)}
                  className="bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-cyan-500 rounded-xl px-4 py-3 text-slate-100 outline-none transition duration-300 text-sm font-medium"
                  placeholder="e.g. 50000000"
                />
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Spent to Date (₹ / $)</label>
                <input 
                  type="number" 
                  value={meta.spent_to_date || ''}
                  onChange={(e) => handleMetaChange('spent_to_date', e.target.value)}
                  className="bg-slate-950 border border-slate-800 hover:border-slate-700 focus:border-cyan-500 rounded-xl px-4 py-3 text-slate-100 outline-none transition duration-300 text-sm font-medium"
                  placeholder="e.g. 12000000"
                />
              </div>
            </div>

            <div className="pt-6 border-t border-slate-800/80 flex justify-end">
              <button 
                onClick={saveMeta}
                disabled={saving}
                className="bg-cyan-500 text-slate-950 hover:bg-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] disabled:bg-cyan-800 text-sm font-extrabold px-6 py-3 rounded-xl transition duration-300"
              >
                {saving ? 'Saving...' : 'Save Metadata'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 2: CONTRACTORS */}
        {activeTab === 'contractors' && (
          <div className="animate-fade-in space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-cyan-400 rounded-full" />
                  Contractor SLAs
                </h2>
                <p className="text-slate-400 text-xs mt-1">Configure operating parameters, daily penalties, and active labor capacity.</p>
              </div>
              <button
                onClick={() => addRow({ name: '', scope: '', daily_operating_cost: 0, daily_delay_penalty: 0, active_workers: 0 }, contractors, setContractors)}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 text-cyan-400 hover:text-cyan-300 px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition duration-300"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
                Add Contractor
              </button>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-950/30">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-slate-950/80 text-slate-400 uppercase text-xs font-bold tracking-wider border-b border-slate-800/60">
                    <th className="p-4">Name</th>
                    <th className="p-4">Scope</th>
                    <th className="p-4">Daily Cost (₹)</th>
                    <th className="p-4">Daily Penalty (₹)</th>
                    <th className="p-4">Active Workers</th>
                    <th className="p-4 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {contractors.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-slate-500 font-medium">No contractors defined. Add one above.</td>
                    </tr>
                  ) : (
                    contractors.map((c, i) => (
                      <tr key={i} className="hover:bg-slate-900/30 transition duration-150">
                        <td className="p-4 min-w-[200px]">
                          <input 
                            type="text" 
                            value={c.name}
                            onChange={(e) => updateRow(contractors, i, 'name', e.target.value, setContractors)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-full"
                            placeholder="L&T Construction"
                          />
                        </td>
                        <td className="p-4 min-w-[220px]">
                          <input 
                            type="text" 
                            value={c.scope}
                            onChange={(e) => updateRow(contractors, i, 'scope', e.target.value, setContractors)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-full"
                            placeholder="Civil structures"
                          />
                        </td>
                        <td className="p-4">
                          <input 
                            type="number" 
                            value={c.daily_operating_cost || ''}
                            onChange={(e) => updateRow(contractors, i, 'daily_operating_cost', parseFloat(e.target.value) || 0, setContractors)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-32"
                          />
                        </td>
                        <td className="p-4">
                          <input 
                            type="number" 
                            value={c.daily_delay_penalty || ''}
                            onChange={(e) => updateRow(contractors, i, 'daily_delay_penalty', parseFloat(e.target.value) || 0, setContractors)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-32"
                          />
                        </td>
                        <td className="p-4">
                          <input 
                            type="number" 
                            value={c.active_workers || ''}
                            onChange={(e) => updateRow(contractors, i, 'active_workers', parseInt(e.target.value) || 0, setContractors)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-24"
                          />
                        </td>
                        <td className="p-4 text-center">
                          <button
                            onClick={() => removeRow(i, contractors, setContractors)}
                            className="text-rose-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 transition duration-200"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="pt-6 border-t border-slate-800/80 flex justify-end">
              <button 
                onClick={saveContractors}
                disabled={saving}
                className="bg-cyan-500 text-slate-950 hover:bg-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] disabled:bg-cyan-800 text-sm font-extrabold px-6 py-3 rounded-xl transition duration-300"
              >
                {saving ? 'Saving...' : 'Save SLAs'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 3: DIVISIONS */}
        {activeTab === 'divisions' && (
          <div className="animate-fade-in space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-cyan-400 rounded-full" />
                  Divisions
                </h2>
                <p className="text-slate-400 text-xs mt-1">Configure project divisions and assign lead contractors (foreign-key referenced).</p>
              </div>
              <button
                onClick={() => addRow({ id: '', name: '', lead_contractor: contractors[0]?.name || '' }, divisions, setDivisions)}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 text-cyan-400 hover:text-cyan-300 px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition duration-300"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
                Add Division
              </button>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-950/30">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-slate-950/80 text-slate-400 uppercase text-xs font-bold tracking-wider border-b border-slate-800/60">
                    <th className="p-4">Division ID</th>
                    <th className="p-4">Division Name</th>
                    <th className="p-4">Lead Contractor</th>
                    <th className="p-4 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {divisions.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="p-8 text-center text-slate-500 font-medium">No divisions defined. Add one above.</td>
                    </tr>
                  ) : (
                    divisions.map((d, i) => (
                      <tr key={i} className="hover:bg-slate-900/30 transition duration-150">
                        <td className="p-4">
                          <input 
                            type="text" 
                            value={d.id}
                            onChange={(e) => updateRow(divisions, i, 'id', e.target.value.toUpperCase().replace(/\s+/g, ''), setDivisions)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-semibold w-40"
                            placeholder="DIV-CIVIL"
                          />
                        </td>
                        <td className="p-4">
                          <input 
                            type="text" 
                            value={d.name}
                            onChange={(e) => updateRow(divisions, i, 'name', e.target.value, setDivisions)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-full"
                            placeholder="Civil & Structural"
                          />
                        </td>
                        <td className="p-4">
                          <select
                            value={d.lead_contractor}
                            onChange={(e) => updateRow(divisions, i, 'lead_contractor', e.target.value, setDivisions)}
                            className="bg-slate-950 border border-slate-800 focus:border-cyan-500 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-full md:w-64 cursor-pointer"
                          >
                            <option value="">-- Choose Contractor --</option>
                            {contractors.map((c, idx) => (
                              <option key={idx} value={c.name}>{c.name}</option>
                            ))}
                          </select>
                        </td>
                        <td className="p-4 text-center">
                          <button
                            onClick={() => removeRow(i, divisions, setDivisions)}
                            className="text-rose-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 transition duration-200"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="pt-6 border-t border-slate-800/80 flex justify-end">
              <button 
                onClick={saveDivisions}
                disabled={saving}
                className="bg-cyan-500 text-slate-950 hover:bg-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] disabled:bg-cyan-800 text-sm font-extrabold px-6 py-3 rounded-xl transition duration-300"
              >
                {saving ? 'Saving...' : 'Save Divisions'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 4: REGULATORY */}
        {activeTab === 'regulatory' && (
          <div className="animate-fade-in space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-cyan-400 rounded-full" />
                  Regulatory KB
                </h2>
                <p className="text-slate-400 text-xs mt-1">Configure regulatory codes, text, and triggering parameters.</p>
              </div>
              <button
                onClick={() => addRow({ code: '', description: '', trigger_condition: triggerConditions[0] }, regulatory, setRegulatory)}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 text-cyan-400 hover:text-cyan-300 px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition duration-300"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
                Add Rule
              </button>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-950/30">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-slate-950/80 text-slate-400 uppercase text-xs font-bold tracking-wider border-b border-slate-800/60">
                    <th className="p-4">Rule Code</th>
                    <th className="p-4">Description</th>
                    <th className="p-4">Trigger Condition</th>
                    <th className="p-4 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {regulatory.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="p-8 text-center text-slate-500 font-medium">No regulatory rules defined. Add one above.</td>
                    </tr>
                  ) : (
                    regulatory.map((r, i) => (
                      <tr key={i} className="hover:bg-slate-900/30 transition duration-150">
                        <td className="p-4">
                          <input 
                            type="text" 
                            value={r.code}
                            onChange={(e) => updateRow(regulatory, i, 'code', e.target.value.toUpperCase().replace(/\s+/g, ''), setRegulatory)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-semibold w-44"
                            placeholder="BOCW_SEC_40"
                          />
                        </td>
                        <td className="p-4">
                          <textarea 
                            value={r.description}
                            onChange={(e) => updateRow(regulatory, i, 'description', e.target.value, setRegulatory)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-full h-10 min-h-[40px] max-h-[120px]"
                            placeholder="Rule description..."
                          />
                        </td>
                        <td className="p-4">
                          <select
                            value={r.trigger_condition}
                            onChange={(e) => updateRow(regulatory, i, 'trigger_condition', e.target.value, setRegulatory)}
                            className="bg-slate-950 border border-slate-800 focus:border-cyan-500 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-full md:w-56 cursor-pointer"
                          >
                            {triggerConditions.map((tc, idx) => (
                              <option key={idx} value={tc}>{tc}</option>
                            ))}
                          </select>
                        </td>
                        <td className="p-4 text-center">
                          <button
                            onClick={() => removeRow(i, regulatory, setRegulatory)}
                            className="text-rose-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 transition duration-200"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="pt-6 border-t border-slate-800/80 flex justify-end">
              <button 
                onClick={saveRegulatory}
                disabled={saving}
                className="bg-cyan-500 text-slate-950 hover:bg-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] disabled:bg-cyan-800 text-sm font-extrabold px-6 py-3 rounded-xl transition duration-300"
              >
                {saving ? 'Saving...' : 'Save Regulatory KB'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 5: TASKS */}
        {activeTab === 'tasks' && (
          <div className="animate-fade-in space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-cyan-400 rounded-full" />
                  Schedule Tasks
                </h2>
                <p className="text-slate-400 text-xs mt-1">Configure project schedule tasks, critical path status, and dependencies.</p>
              </div>
              <button
                onClick={() => addRow({ task_id: '', division_id: divisions[0]?.id || '', task_name: '', duration: 1, is_critical_path: 0, dependencies: '' }, tasks, setTasks)}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 text-cyan-400 hover:text-cyan-300 px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition duration-300"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
                Add Task
              </button>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-950/30">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-slate-950/80 text-slate-400 uppercase text-xs font-bold tracking-wider border-b border-slate-800/60">
                    <th className="p-4">Task ID</th>
                    <th className="p-4">Division ID</th>
                    <th className="p-4">Task Name</th>
                    <th className="p-4">Duration (Days)</th>
                    <th className="p-4">Critical Path</th>
                    <th className="p-4">Dependencies (IDs)</th>
                    <th className="p-4 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {tasks.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500 font-medium">No schedule tasks defined. Add one above.</td>
                    </tr>
                  ) : (
                    tasks.map((t, i) => (
                      <tr key={i} className="hover:bg-slate-900/30 transition duration-150">
                        <td className="p-4">
                          <input 
                            type="text" 
                            value={t.task_id}
                            onChange={(e) => updateRow(tasks, i, 'task_id', e.target.value.toUpperCase().replace(/\s+/g, ''), setTasks)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-semibold w-24"
                            placeholder="T1"
                          />
                        </td>
                        <td className="p-4">
                          <select
                            value={t.division_id}
                            onChange={(e) => updateRow(tasks, i, 'division_id', e.target.value, setTasks)}
                            className="bg-slate-950 border border-slate-800 focus:border-cyan-500 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-40 cursor-pointer"
                          >
                            <option value="">-- Choose Division --</option>
                            {divisions.map((d, idx) => (
                              <option key={idx} value={d.id}>{d.id} ({d.name})</option>
                            ))}
                          </select>
                        </td>
                        <td className="p-4 min-w-[200px]">
                          <input 
                            type="text" 
                            value={t.task_name}
                            onChange={(e) => updateRow(tasks, i, 'task_name', e.target.value, setTasks)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-full"
                            placeholder="Excavation works"
                          />
                        </td>
                        <td className="p-4">
                          <input 
                            type="number" 
                            value={t.duration || ''}
                            onChange={(e) => updateRow(tasks, i, 'duration', parseInt(e.target.value) || 0, setTasks)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-24"
                          />
                        </td>
                        <td className="p-4 text-center">
                          <input 
                            type="checkbox" 
                            checked={t.is_critical_path === 1}
                            onChange={(e) => updateRow(tasks, i, 'is_critical_path', e.target.checked ? 1 : 0, setTasks)}
                            className="w-4 h-4 rounded border-slate-800 text-cyan-500 focus:ring-cyan-500/20 bg-slate-950 accent-cyan-500 cursor-pointer"
                          />
                        </td>
                        <td className="p-4 min-w-[150px]">
                          <input 
                            type="text" 
                            value={t.dependencies}
                            onChange={(e) => updateRow(tasks, i, 'dependencies', e.target.value.toUpperCase().replace(/\s+/g, ''), setTasks)}
                            className="bg-slate-950/80 border border-slate-800/60 focus:border-cyan-500/60 outline-none rounded-lg px-3 py-2 text-slate-200 text-sm font-medium w-full"
                            placeholder="e.g. T1,T2"
                          />
                        </td>
                        <td className="p-4 text-center">
                          <button
                            onClick={() => removeRow(i, tasks, setTasks)}
                            className="text-rose-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-500/10 transition duration-200"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="pt-6 border-t border-slate-800/80 flex justify-end">
              <button 
                onClick={saveTasks}
                disabled={saving}
                className="bg-cyan-500 text-slate-950 hover:bg-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] disabled:bg-cyan-800 text-sm font-extrabold px-6 py-3 rounded-xl transition duration-300"
              >
                {saving ? 'Saving...' : 'Save Schedule'}
              </button>
            </div>
          </div>
        )}

      </main>

      {/* Embedded CSS Animations */}
      <style jsx global>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideIn {
          from { transform: translateX(120%); }
          to { transform: translateX(0); }
        }
        .animate-fade-in {
          animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .animate-slide-in {
          animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}</style>
    </div>
  );
}
