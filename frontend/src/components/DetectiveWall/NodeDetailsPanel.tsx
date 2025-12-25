import { useEffect, useMemo, useRef, useState } from 'react';
import { X } from 'lucide-react';
import type { NodeData, Connection } from '../../types';

type SourcePreview = {
  title: string;
  content: string;
  full_text_length: number;
  error?: string | null;
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

  return (
    <div className="fixed right-0 top-0 h-full w-full sm:w-[400px] glass-panel border-l border-white/10 flex flex-col z-50 shadow-2xl">
      <div className="p-5 border-b border-white/10 flex justify-between items-center bg-legal-surface/50">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">File</div>
          <h3 className="text-lg font-bold text-legal-text font-serif truncate tracking-tight">{props.node.title}</h3>
          <div className="mt-1 text-xs text-slate-400 flex items-center gap-2">
            <span className="px-2 py-0.5 bg-white/5 rounded border border-white/10">{props.node.type}</span>
            <span>•</span>
            <span>{props.node.status}</span>
            <span>•</span>
            <span>{props.node.date}</span>
          </div>
        </div>
        <button
          onClick={props.onClose}
          className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
          title="Close"
          aria-label="Close"
        >
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {props.node.source && (
          <div className="bg-legal-surface/40 border border-white/5 rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-medium mb-2">Source</div>
            <div className="text-sm text-slate-300 break-words leading-relaxed">{props.node.source}</div>
          </div>
        )}

        {firstDocumentUrl && (
          <div className="bg-legal-surface/40 border border-white/5 rounded-xl p-4">
            <div className="text-[10px] uppercase tracking-wider text-slate-500 font-medium mb-2">Document Preview</div>
            {documentHost && <div className="text-xs text-slate-400 mb-2">{documentHost}</div>}

            {previewState.status === 'loading' && previewState.url === firstDocumentUrl && (
              <div className="text-sm text-slate-500 italic">Loading preview…</div>
            )}

            {previewState.status === 'error' && previewState.url === firstDocumentUrl && (
              <div className="text-sm text-slate-500">
                Preview unavailable.
                <div className="mt-1 text-xs text-slate-600 break-words">{previewState.message}</div>
              </div>
            )}

            {previewState.status === 'ok' && previewState.url === firstDocumentUrl && (
              <div>
                <div className="text-sm text-legal-text font-semibold leading-snug">{previewState.data.title || 'Preview'}</div>
                <div className="mt-2 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">{previewState.data.content || 'No preview text available.'}</div>
                {typeof previewState.data.full_text_length === 'number' && previewState.data.full_text_length > 0 && (
                  <div className="mt-2 text-[11px] text-slate-500">Extracted length: {previewState.data.full_text_length.toLocaleString()} chars</div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="bg-legal-surface/40 border border-white/5 rounded-xl p-4">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-medium mb-3">Connections</div>
          {related.length === 0 ? (
            <div className="text-sm text-slate-500 italic">No links yet.</div>
          ) : (
            <div className="space-y-2">
              {related.map((c, i) => {
                const otherId = c.from === props.node.id ? c.to : c.from;
                const otherTitle = getTitle(otherId);
                const dir = c.from === props.node.id ? '→' : '←';
                return (
                  <div key={i} className="text-xs text-slate-300">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate">
                        {dir} {otherTitle}
                      </span>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full border font-mono ${
                          c.type === 'conflict'
                            ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                            : c.type === 'suggested'
                              ? 'bg-legal-gold/20 text-legal-gold border-legal-gold/40'
                              : 'bg-black/20 text-slate-300 border-white/10'
                        }`}
                        title={c.reason || c.label}
                      >
                        {c.label}
                      </span>
                    </div>
                    {c.reason && <div className="mt-1 text-[11px] text-slate-400">{c.reason}</div>}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-legal-surface/40 border border-white/5 rounded-xl p-4">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-medium mb-3">Attachments</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-black/20 border border-white/5 rounded-lg p-3">
              <div className="text-[10px] text-slate-500 font-medium">Photos</div>
              <div className="mt-1 text-legal-text font-bold">{byKind.photo.length}</div>
            </div>
            <div className="bg-black/20 border border-white/5 rounded-lg p-3">
              <div className="text-[10px] text-slate-500 font-medium">Videos</div>
              <div className="mt-1 text-legal-text font-bold">{byKind.video.length}</div>
            </div>
            <div className="bg-black/20 border border-white/5 rounded-lg p-3">
              <div className="text-[10px] text-slate-500 font-medium">Audios</div>
              <div className="mt-1 text-legal-text font-bold">{byKind.audio.length}</div>
            </div>
            <div className="bg-black/20 border border-white/5 rounded-lg p-3">
              <div className="text-[10px] text-slate-500 font-medium">Documents</div>
              <div className="mt-1 text-legal-text font-bold">{byKind.document.length}</div>
            </div>
          </div>

          {attachments.length > 0 && (
            <div className="mt-3 space-y-2">
              {attachments.map((a, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs text-slate-200 bg-slate-950/30 border border-slate-700/40 rounded-lg px-2 py-1">
                  <span className="truncate">{a.name}</span>
                  <div className="flex items-center gap-2">
                    {a.url && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          window.open(a.url, '_blank', 'noopener,noreferrer');
                        }}
                        className="text-[10px] px-2 py-1 rounded-md border border-white/10 bg-black/20 text-slate-300 hover:text-legal-gold hover:border-legal-gold/30 transition-colors"
                        aria-label={`Open ${a.name}`}
                        title="Open source"
                      >
                        OPEN
                      </button>
                    )}
                    <span className="text-[10px] text-slate-400 font-mono">{a.kind.toUpperCase()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {attachments.length === 0 && <div className="mt-2 text-xs text-slate-400">No attachments added.</div>}
        </div>
      </div>
    </div>
  );
}
