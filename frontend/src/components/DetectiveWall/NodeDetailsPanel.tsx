import { useEffect, useMemo, useRef, useState } from 'react';
import { X, FileText, AlertCircle, Share2, Paperclip, Image, Video, Mic, ExternalLink, Brain, Scale, Calendar, User, Hash, Search, Copy, GitCompare } from 'lucide-react';
import type { NodeData, Connection } from '../../types';

type SourcePreview = {
  title: string;
  content: string;
  full_text_length: number;
  error?: string | null;
  summary_ai?: string;
  key_points?: string[];
  quotes?: string[];
  metadata?: {
    court?: string;
    date?: string;
    case_number?: string;
    judge?: string;
    parties?: string;
  };
  connections?: Array<{
    title: string;
    type: string;
    reason: string;
  }>;
};

export function NodeDetailsPanel(props: {
  isOpen: boolean;
  onClose: () => void;
  node: NodeData;
  connections: Connection[];
  nodes: NodeData[];
}) {
  if (!props.isOpen) return null;

  const related = props.connections.filter((c) => c.from === props.node.id || c.to === props.node.id);
  const getTitle = (id: number) => props.nodes.find((n) => n.id === id)?.title || String(id);

  const attachments = props.node.attachments ?? [];
  const byKind = {
    photo: attachments.filter((a) => a.kind === 'photo'),
    video: attachments.filter((a) => a.kind === 'video'),
    audio: attachments.filter((a) => a.kind === 'audio'),
    document: attachments.filter((a) => a.kind === 'document'),
    other: attachments.filter((a) => a.kind === 'other'),
  };

  const firstDocumentUrl = useMemo(() => {
    const doc = (props.node.attachments ?? []).find((a) => a.kind === 'document' && typeof a.url === 'string' && a.url.trim());
    return doc?.url?.trim() || null;
  }, [props.node]);

  const [previewState, setPreviewState] = useState<
    | { status: 'idle' }
    | { status: 'loading'; url: string }
    | { status: 'ok'; url: string; data: SourcePreview }
    | { status: 'error'; url: string; message: string }
  >({ status: 'idle' });

  const previewCacheRef = useRef<Map<string, { kind: 'ok'; data: SourcePreview } | { kind: 'error'; message: string }>>(
    new Map()
  );

  useEffect(() => {
    if (!firstDocumentUrl) {
      setPreviewState({ status: 'idle' });
      return;
    }

    const cached = previewCacheRef.current.get(firstDocumentUrl);
    if (cached?.kind === 'ok') {
      setPreviewState({ status: 'ok', url: firstDocumentUrl, data: cached.data });
      return;
    }
    if (cached?.kind === 'error') {
      setPreviewState({ status: 'error', url: firstDocumentUrl, message: cached.message });
      return;
    }

    const controller = new AbortController();
    setPreviewState({ status: 'loading', url: firstDocumentUrl });

    (async () => {
      try {
        const res = await fetch('/api/v1/research/sources/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: firstDocumentUrl }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const detail = await res.text();
          throw new Error(detail || `API error: ${res.status}`);
        }

        const data = (await res.json()) as SourcePreview;
        if (data?.error) {
          const message = String(data.error);
          previewCacheRef.current.set(firstDocumentUrl, { kind: 'error', message });
          setPreviewState({ status: 'error', url: firstDocumentUrl, message });
          return;
        }

        previewCacheRef.current.set(firstDocumentUrl, { kind: 'ok', data });
        setPreviewState({ status: 'ok', url: firstDocumentUrl, data });
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') return;
        const message = e instanceof Error ? e.message : 'Preview failed';
        previewCacheRef.current.set(firstDocumentUrl, { kind: 'error', message });
        setPreviewState({ status: 'error', url: firstDocumentUrl, message });
      }
    })();

    return () => controller.abort();
  }, [firstDocumentUrl]);

  const documentHost = useMemo(() => {
    if (!firstDocumentUrl) return null;
    try {
      return new URL(firstDocumentUrl).hostname;
    } catch {
      return null;
    }
  }, [firstDocumentUrl]);

  const handleAskAI = () => {
    if (previewState.status === 'ok' && previewState.data.summary_ai) {
      navigator.clipboard.writeText(`Context from ${previewState.data.title}:\n${previewState.data.summary_ai}`);
      alert("Summary copied to clipboard! You can now paste it in the chat.");
    } else {
      alert("Wait for analysis to complete first.");
    }
  };

  const handleFindSimilar = () => {
    const el = document.getElementById('smart-connections');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
    else alert("No similar cases found in analysis.");
  };

  const handleExtractQuotes = () => {
    const el = document.getElementById('key-quotes');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
    else alert("No quotes extracted yet.");
  };

  const handleCompare = () => {
    const brief = [
      `Node: ${props.node.title}`,
      `Type: ${props.node.type}`,
      `Status: ${props.node.status}`,
      '',
      'Connected Nodes:',
      ...related.slice(0, 8).map((c) => {
        const other = c.from === props.node.id ? c.to : c.from;
        return `- ${getTitle(other)} (${c.type})`;
      }),
      '',
      'Use this as baseline and compare with another node in your wall.',
    ].join('\n');
    navigator.clipboard.writeText(brief);
    alert('Comparison brief copied. Open another node and compare the two briefs.');
  };

  return (
    <div className="fixed right-0 top-0 h-full w-full sm:w-[500px] bg-slate-900/95 backdrop-blur-xl border-l border-white/10 flex flex-col z-50 shadow-2xl transition-all duration-300 ease-in-out">
      {/* Header */}
      <div className="p-6 border-b border-white/10 flex justify-between items-start bg-white/5">
        <div className="flex-1 min-w-0 mr-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-legal-gold/10 text-legal-gold rounded border border-legal-gold/20">
              {props.node.type}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">{props.node.date}</span>
          </div>
          <h3 className="text-xl font-bold text-white font-serif leading-tight break-words">{props.node.title}</h3>
          <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
            <div className={`w-2 h-2 rounded-full ${props.node.status === 'Verified' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            <span className="capitalize">{props.node.status}</span>
          </div>
        </div>
        <button
          onClick={props.onClose}
          className="p-2 hover:bg-white/10 rounded-full text-slate-400 hover:text-white transition-all duration-200 group"
          title="Close Panel"
          aria-label="Close Panel"
        >
          <X size={24} className="group-hover:rotate-90 transition-transform duration-200" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
        
        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-2">
          <button onClick={handleAskAI} className="flex items-center justify-center gap-2 p-2 bg-legal-gold/10 hover:bg-legal-gold/20 border border-legal-gold/20 rounded-lg text-xs font-medium text-legal-gold transition-colors">
            <Brain size={14} />
            Ask AI about this
          </button>
          <button onClick={handleFindSimilar} className="flex items-center justify-center gap-2 p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-medium text-slate-300 transition-colors">
            <Search size={14} />
            Find similar cases
          </button>
          <button onClick={handleExtractQuotes} className="flex items-center justify-center gap-2 p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-medium text-slate-300 transition-colors">
            <Copy size={14} />
            Extract quotes
          </button>
          <button onClick={handleCompare} className="flex items-center justify-center gap-2 p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-medium text-slate-300 transition-colors">
            <GitCompare size={14} />
            Compare
          </button>
        </div>

        {/* Document Analysis */}
        {props.node.content && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
              <FileText size={12} />
              Case File Content
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-4">
              <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap font-serif">
                {props.node.content}
              </div>
            </div>
          </div>
        )}

        {firstDocumentUrl && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <FileText size={12} />
                Document Analysis
              </div>
              {documentHost && <span className="text-[10px] text-slate-500 bg-white/5 px-2 py-0.5 rounded-full">{documentHost}</span>}
            </div>
            
            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
              {previewState.status === 'loading' && previewState.url === firstDocumentUrl && (
                <div className="p-8 flex flex-col items-center justify-center text-slate-500 gap-2">
                  <div className="w-4 h-4 border-2 border-legal-gold/50 border-t-legal-gold rounded-full animate-spin" />
                  <span className="text-xs italic">Analyzing document with AI...</span>
                </div>
              )}

              {previewState.status === 'error' && previewState.url === firstDocumentUrl && (
                <div className="p-4 bg-rose-950/10 text-rose-200/80 text-sm flex items-start gap-3">
                  <AlertCircle size={16} className="mt-0.5 shrink-0" />
                  <div>
                    <div className="font-medium">Analysis unavailable</div>
                    <div className="text-xs opacity-70 mt-1">{previewState.message}</div>
                  </div>
                </div>
              )}

              {previewState.status === 'ok' && previewState.url === firstDocumentUrl && (
                <div className="divide-y divide-white/5">
                  {/* AI Summary */}
                  {previewState.data.summary_ai && (
                    <div className="p-4 bg-legal-gold/5">
                      <div className="flex items-center gap-2 text-xs font-bold text-legal-gold mb-2">
                        <Brain size={12} />
                        AI SUMMARY
                      </div>
                      <div className="text-sm text-slate-200 leading-relaxed font-serif whitespace-pre-wrap">
                        {previewState.data.summary_ai}
                      </div>
                    </div>
                  )}

                  {/* Key Points */}
                  {previewState.data.key_points && previewState.data.key_points.length > 0 && (
                    <div className="p-4 bg-white/5">
                      <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                        <AlertCircle size={12} />
                        Key Points
                      </div>
                      <ul className="list-disc list-inside space-y-1 text-sm text-slate-300 font-serif">
                        {previewState.data.key_points.map((point, i) => (
                          <li key={i}>{point}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Quotes */}
                  {previewState.data.quotes && previewState.data.quotes.length > 0 && (
                    <div id="key-quotes" className="p-4 bg-white/5">
                      <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                        <Copy size={12} />
                        Significant Quotes
                      </div>
                      <div className="space-y-2">
                        {previewState.data.quotes.map((quote, i) => (
                          <blockquote key={i} className="border-l-2 border-legal-gold/30 pl-3 text-sm text-slate-400 italic font-serif">
                            "{quote}"
                          </blockquote>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Metadata Grid */}
                  {previewState.data.metadata && (
                    <div className="p-4 grid grid-cols-2 gap-4 text-xs">
                      <div>
                        <div className="text-slate-500 mb-1 flex items-center gap-1"><Scale size={10} /> Court</div>
                        <div className="text-slate-200 font-medium">{previewState.data.metadata.court || 'Unknown'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 mb-1 flex items-center gap-1"><Calendar size={10} /> Date</div>
                        <div className="text-slate-200 font-medium">{previewState.data.metadata.date || 'Unknown'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 mb-1 flex items-center gap-1"><Hash size={10} /> Case No</div>
                        <div className="text-slate-200 font-medium">{previewState.data.metadata.case_number || 'Unknown'}</div>
                      </div>
                      <div>
                        <div className="text-slate-500 mb-1 flex items-center gap-1"><User size={10} /> Judge</div>
                        <div className="text-slate-200 font-medium">{previewState.data.metadata.judge || 'Unknown'}</div>
                      </div>
                    </div>
                  )}

                  {/* Smart Connections */}
                  {previewState.data.connections && previewState.data.connections.length > 0 && (
                    <div id="smart-connections" className="p-4 bg-black/20">
                      <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Smart Connections</div>
                      <div className="space-y-2">
                        {previewState.data.connections.map((conn, idx) => (
                          <div key={idx} className="flex items-start gap-2 text-xs">
                            <div className={`mt-0.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                              conn.type === 'contradiction' ? 'bg-rose-500' : 'bg-blue-500'
                            }`} />
                            <div>
                              <div className="text-slate-300 font-medium">{conn.title}</div>
                              <div className="text-slate-500 text-[10px]">{conn.reason}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Raw Content Preview */}
                  <div className="p-6 bg-white text-slate-900 max-h-[400px] overflow-y-auto custom-scrollbar">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-200 pb-2">
                      Document Preview
                    </div>
                    <div className="text-sm leading-relaxed whitespace-pre-wrap font-serif selection:bg-legal-gold/30">
                      {previewState.data.content || <span className="italic text-slate-400">No text content extracted.</span>}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Graph Connections */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
            <Share2 size={12} />
            Graph Connections
          </div>
          
          {related.length === 0 ? (
            <div className="text-sm text-slate-600 italic px-2">No connected nodes.</div>
          ) : (
            <div className="grid gap-2">
              {related.map((c, i) => {
                const otherId = c.from === props.node.id ? c.to : c.from;
                const otherTitle = getTitle(otherId);
                const isOutgoing = c.from === props.node.id;
                
                return (
                  <div key={i} className="group flex flex-col bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10 rounded-lg p-3 transition-all">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-black/30 text-slate-400 font-mono`}>
                          {isOutgoing ? 'OUT' : 'IN'}
                        </span>
                        <span className="text-sm text-slate-200 truncate font-medium">{otherTitle}</span>
                      </div>
                      <span
                        className={`shrink-0 text-[10px] px-2 py-0.5 rounded-full border font-medium ${
                          c.type === 'conflict'
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            : c.type === 'suggested'
                              ? 'bg-legal-gold/10 text-legal-gold border-legal-gold/20'
                              : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
                        }`}
                      >
                        {c.label}
                      </span>
                    </div>
                    {c.reason && (
                      <div className="text-xs text-slate-400 pl-2 border-l-2 border-white/5 group-hover:border-white/10 transition-colors">
                        {c.reason}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Attachments Grid */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
            <Paperclip size={12} />
            Attachments
          </div>
          
          <div className="grid grid-cols-4 gap-2">
            {[
              { label: 'Photos', count: byKind.photo.length, icon: Image },
              { label: 'Videos', count: byKind.video.length, icon: Video },
              { label: 'Audio', count: byKind.audio.length, icon: Mic },
              { label: 'Docs', count: byKind.document.length, icon: FileText },
            ].map((stat, idx) => (
              <div key={idx} className="bg-white/5 border border-white/5 rounded-lg p-2 flex flex-col items-center justify-center gap-1">
                <stat.icon size={14} className="text-slate-500" />
                <div className="text-lg font-bold text-white leading-none">{stat.count}</div>
                <div className="text-[9px] text-slate-500 uppercase tracking-wide">{stat.label}</div>
              </div>
            ))}
          </div>

          {attachments.length > 0 && (
            <div className="space-y-1 mt-2">
              {attachments.map((a, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs text-slate-300 bg-black/20 hover:bg-black/30 border border-white/5 rounded-lg px-3 py-2 transition-colors group">
                  <div className="flex items-center gap-3 min-w-0">
                    {a.kind === 'photo' && <Image size={14} className="text-slate-500" />}
                    {a.kind === 'video' && <Video size={14} className="text-slate-500" />}
                    {a.kind === 'audio' && <Mic size={14} className="text-slate-500" />}
                    {a.kind === 'document' && <FileText size={14} className="text-slate-500" />}
                    <span className="truncate">{a.name}</span>
                  </div>
                  
                  {a.url && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        window.open(a.url, '_blank', 'noopener,noreferrer');
                      }}
                      className="opacity-0 group-hover:opacity-100 flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-legal-gold/10 text-legal-gold hover:bg-legal-gold/20 transition-all"
                    >
                      OPEN <ExternalLink size={10} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
