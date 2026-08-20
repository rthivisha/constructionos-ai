import React, { useState, useRef } from 'react';
import { api } from '../lib/api';
import ReasoningTrace from './ReasoningTrace';
import { Paperclip, X, FileText, Image, Sparkles, ArrowRight, ShieldAlert, AlertTriangle } from 'lucide-react';

export default function EventInput() {
  const [eventText, setEventText] = useState('');
  const [loading, setLoading] = useState(false);
  const [isVerifyingControls, setIsVerifyingControls] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  // File upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileBase64, setFileBase64] = useState<string | null>(null);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Predefined quick-test templates with 5 standard demo scenarios
  const templates = [
    {
      id: 'T-101',
      label: 'Crane Failure (T-101)',
      tag: 'HALT',
      tagColor: 'text-red-400 bg-red-950/60 border-red-800/60',
      text: 'Tower Crane Lift Failure at T-101: mechanical failure in the hoist system during structural steel lifting operations, all work halted.'
    },
    {
      id: 'T-103',
      label: 'Heavy Weather (T-103)',
      tag: 'HALT',
      tagColor: 'text-red-400 bg-red-950/60 border-red-800/60',
      text: 'Heavy monsoon weather warning issued for the site. Strong winds and heavy rainfall expected over the next 48 hours, affecting all open-site operations.'
    },
    {
      id: 'AMBIGUOUS',
      label: 'Ambiguous Incident',
      tag: 'HALT / UNVERIFIED',
      tagColor: 'text-amber-400 bg-amber-950/60 border-amber-800/60',
      text: 'Excavation crew reported minor soil instability and trench wall movement near an unspecified work area, task ID unverified.'
    },
    {
      id: 'T-104-CLEAR',
      label: 'Material Delay (T-104)',
      tag: 'CONTINUE',
      tagColor: 'text-emerald-400 bg-emerald-950/60 border-emerald-800/60',
      text: 'Minor electrical conduit material delivery delayed by one day due to supplier backlog. Work area is completely safe with no hazards. T-104 is not on critical path.'
    },
    {
      id: 'T-104-GAS',
      label: 'Ventilation / Gas (T-104)',
      tag: 'VERIFY GATE',
      tagColor: 'text-amber-400 bg-amber-950/60 border-amber-800/60',
      text: 'Workers report a strong chemical odor and mild dizziness near the ventilation shaft during electrical conduit installation, work area not yet cleared.'
    }
  ];

  const handleTemplateClick = (text: string) => {
    setEventText(text);
    setError(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAttachmentError(null);
    const file = e.target.files?.[0];
    if (!file) return;

    // 1. Restrict content_type to an explicit allowlist
    const allowedTypes = ['image/png', 'image/jpeg', 'application/pdf'];
    if (!allowedTypes.includes(file.type)) {
      setAttachmentError('Only PNG, JPEG, and PDF files are allowed.');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    // 2. Enforce 5MB limit
    const maxSizeBytes = 5 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      setAttachmentError('File size exceeds the maximum limit of 5MB.');
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setSelectedFile(file);

    // 3. Convert to base64
    const reader = new FileReader();
    reader.onloadend = () => {
      setFileBase64(reader.result as string);
    };
    reader.onerror = () => {
      setAttachmentError('Failed to read the file.');
      setSelectedFile(null);
      setFileBase64(null);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setFileBase64(null);
    setAttachmentError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventText.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    let attachmentPayload = null;
    if (selectedFile && fileBase64) {
      attachmentPayload = {
        filename: selectedFile.name,
        content_type: selectedFile.type,
        data: fileBase64
      };
    }

    try {
      const data = await api.processSiteEvent(eventText, attachmentPayload, false);
      setResult(data);
      handleRemoveFile();
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'An error occurred while submitting the event report.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmControlsVerified = async () => {
    if (!eventText.trim()) return;

    setIsVerifyingControls(true);
    setError(null);

    let attachmentPayload = null;
    if (selectedFile && fileBase64) {
      attachmentPayload = {
        filename: selectedFile.name,
        content_type: selectedFile.type,
        data: fileBase64
      };
    }

    try {
      const data = await api.processSiteEvent(eventText, attachmentPayload, true);
      setResult(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'An error occurred while verifying controls.');
    } finally {
      setIsVerifyingControls(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Modern Ingestion Card */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 sm:p-8 shadow-2xl backdrop-blur-xl transition-all">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-sky-500/30 to-transparent" />
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-sky-500/5 blur-3xl pointer-events-none" />

        {/* Card Header with Live Status Badge */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-slate-800/60">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-sky-500/10 border border-sky-500/30 text-sky-400">
                <Sparkles className="h-3.5 w-3.5" />
              </div>
              <h2 className="text-lg font-bold tracking-tight text-slate-100 sm:text-xl">
                Ingest Site Disruption Report
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Submit real-time field reports to trigger the multi-agent observation, compliance, and financial impact pipeline.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 self-start sm:self-auto rounded-full border border-slate-800 bg-slate-950/70 px-3 py-1 text-[11px] font-medium text-slate-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-mono text-slate-400">PIPELINE:</span> LIVE ACTIVE
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-5">
          {/* Text Area */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Event Description & Incident Context
              </label>
              <span className="text-[11px] font-mono text-slate-500">
                {eventText.length} characters
              </span>
            </div>
            <textarea
              value={eventText}
              onChange={(e) => setEventText(e.target.value)}
              placeholder="e.g. Mechanical failure on tower crane hoist at T-101 structural lifting zone, halting all operations..."
              className="w-full min-h-[110px] rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-3.5 text-sm text-slate-100 placeholder-slate-500 transition focus:border-sky-500/80 focus:bg-slate-950 focus:outline-none focus:ring-1 focus:ring-sky-500/50 shadow-inner"
              required
            />
          </div>

          {/* Quick-test Presets */}
          <div>
            <div className="flex items-center gap-1.5 mb-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Demo Presets & Field Scenarios:
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {templates.map((tpl) => (
                <button
                  key={tpl.id}
                  type="button"
                  onClick={() => handleTemplateClick(tpl.text)}
                  className="group relative flex flex-col items-start gap-1 rounded-xl border border-slate-800/80 bg-slate-950/60 p-2.5 text-left transition-all hover:border-sky-500/40 hover:bg-slate-800/40 focus:outline-none focus:ring-1 focus:ring-sky-500/40"
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="font-mono text-[11px] font-semibold text-sky-400 group-hover:text-sky-300">
                      {tpl.id}
                    </span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${tpl.tagColor}`}>
                      {tpl.tag}
                    </span>
                  </div>
                  <span className="text-xs font-medium text-slate-300 line-clamp-1 group-hover:text-slate-100">
                    {tpl.label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Attachment Error Banner */}
          {attachmentError && (
            <div className="rounded-xl border border-red-500/30 bg-red-950/20 px-4 py-2.5 text-xs text-red-400 font-medium flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
              <span>{attachmentError}</span>
            </div>
          )}

          {/* Action Row */}
          <div className="flex flex-col sm:flex-row gap-3.5 items-stretch sm:items-center justify-between pt-4 border-t border-slate-800/60">
            {/* Attachment Controls */}
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="image/png, image/jpeg, application/pdf"
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700/70 bg-slate-950/60 px-3.5 py-2 text-xs font-semibold text-slate-300 transition hover:bg-slate-800/70 hover:border-slate-600 hover:text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500/50"
              >
                <Paperclip className="h-3.5 w-3.5 text-slate-400" />
                Attach Site Map / Spec
              </button>
              
              {selectedFile && (
                <div className="flex items-center gap-2 rounded-xl bg-sky-950/40 border border-sky-500/30 px-3 py-1.5 text-xs text-sky-200">
                  {selectedFile.type.startsWith('image/') ? (
                    <Image className="h-3.5 w-3.5 text-sky-400 shrink-0" />
                  ) : (
                    <FileText className="h-3.5 w-3.5 text-sky-400 shrink-0" />
                  )}
                  <span className="font-medium max-w-[140px] truncate">{selectedFile.name}</span>
                  <span className="text-[10px] text-sky-400/80 font-mono">({(selectedFile.size / 1024).toFixed(0)} KB)</span>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="rounded p-0.5 text-sky-400 hover:bg-sky-900/60 hover:text-sky-100 focus:outline-none shrink-0"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )}
            </div>

            {/* Run Button */}
            <button
              type="submit"
              disabled={loading || !eventText.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-600 px-6 py-2.5 text-sm font-bold text-white shadow-lg shadow-sky-500/20 transition-all hover:from-sky-400 hover:via-blue-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
            >
              {loading ? (
                <>
                  <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Processing Reasoning Chain...
                </>
              ) : (
                <>
                  Run Multi-Agent Pipeline
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Error State Banner */}
      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-950/30 backdrop-blur-md p-4 text-sm text-red-300 shadow-xl flex items-start gap-3">
          <ShieldAlert className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-red-200 block mb-0.5">Pipeline Execution Error</span>
            <p className="text-xs text-red-300/90 leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* Pipeline Results Container */}
      {result && (
        <div className="space-y-8 animate-fadeIn">
          <ReasoningTrace 
            key={`${result.financial_assessment?.calculation_id || result.observation?.task_id || "trace-reset"}-${result.controls_verified}`}
            data={result} 
            rawText={eventText} 
            onReset={() => {
              setResult(null);
              setEventText('');
            }} 
            onConfirmControlsVerified={handleConfirmControlsVerified}
            isVerifyingControls={isVerifyingControls}
          />
        </div>
      )}
    </div>
  );
}
