import React, { useState, useRef } from 'react';
import { api } from '../lib/api';
import ReasoningTrace from './ReasoningTrace';
import { Paperclip, X, FileText, Image } from 'lucide-react';

export default function EventInput() {
  const [eventText, setEventText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  // File upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileBase64, setFileBase64] = useState<string | null>(null);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Predefined quick-test templates
  const templates = [
    {
      label: 'Tower Crane Lift Failure (T-101)',
      text: 'The tower crane lift system experienced a mechanical failure during structural material hoisting, halting all lifts.'
    },
    {
      label: 'Heavy Weather (T-103)',
      text: 'We need to coordinate the labor crews, but heavy rain has made the soil unstable.'
    },
    {
      label: 'Ambiguous Dispatch Report',
      text: 'Worker displacement noted due to local crew conflicts near the station.'
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
      const data = await api.processSiteEvent(eventText, attachmentPayload);
      setResult(data);
      // Clear file selection on successful process
      handleRemoveFile();
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'An error occurred while submitting the event report.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Event Input Box */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 shadow-xl backdrop-blur-md">
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2.5">
          <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
          Ingest Site Disruption Report
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Input site event reports manually to run real-time observe, safety compliance, and CPM delay assessments.
        </p>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">
              Event Description Report
            </label>
            <textarea
              value={eventText}
              onChange={(e) => setEventText(e.target.value)}
              placeholder="e.g. Mechanical failure on tower crane lift at DIV-CIVIL civil works..."
              className="w-full min-h-[100px] rounded-lg border border-slate-700 bg-slate-950 px-4.5 py-3 text-sm text-slate-100 placeholder-slate-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              required
            />
          </div>

          {/* Quick-test templates */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 mr-1 uppercase">Examples:</span>
            {templates.map((tpl, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleTemplateClick(tpl.text)}
                className="rounded-md border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-800 hover:text-slate-100 focus:outline-none"
              >
                {tpl.label}
              </button>
            ))}
          </div>

          {attachmentError && (
            <div className="rounded-lg bg-red-950/20 border border-red-500/20 px-4 py-2.5 text-xs text-red-400 font-medium">
              ⚠ {attachmentError}
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between pt-3 border-t border-slate-800">
            {/* Attachment Button & File Preview info */}
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
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-950/60 px-3.5 py-2 text-xs font-semibold text-slate-300 transition hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <Paperclip className="h-3.5 w-3.5 text-slate-400" />
                Attach Site Map / Document
              </button>
              
              {selectedFile && (
                <div className="flex items-center gap-2 rounded-lg bg-slate-850 border border-slate-700 px-3 py-1.5 text-xs text-slate-200">
                  {selectedFile.type.startsWith('image/') ? (
                    <Image className="h-3.5 w-3.5 text-blue-400 shrink-0" />
                  ) : (
                    <FileText className="h-3.5 w-3.5 text-blue-400 shrink-0" />
                  )}
                  <span className="font-medium max-w-[130px] truncate">{selectedFile.name}</span>
                  <span className="text-[10px] text-slate-500 font-mono">({(selectedFile.size / 1024).toFixed(0)} KB)</span>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="rounded p-0.5 text-slate-400 hover:bg-slate-700 hover:text-slate-200 focus:outline-none shrink-0"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !eventText.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-bold text-white transition hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Processing...
                </>
              ) : (
                <>
                  Run Pipeline
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-950/20 p-4 text-sm text-red-400">
          <span className="font-bold">Error Processing Event:</span> {error}
        </div>
      )}

      {/* pipeline results */}
      {result && (
        <div className="space-y-8 animate-fadeIn">
          <ReasoningTrace 
            key={result.financial_assessment?.calculation_id || result.observation?.task_id || "trace-reset"}
            data={result} 
            rawText={eventText} 
            onReset={() => {
              setResult(null);
              setEventText('');
            }} 
          />
        </div>
      )}
    </div>
  );
}
