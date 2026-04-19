import { useEffect, useRef, useState } from 'react';
import { Clock, FileText, GripVertical, Search, ShieldAlert, Upload, X } from 'lucide-react';
import type { ResearchItem } from './ResearchPanel';

type VaultDocument = ResearchItem;

export function VaultPanel(props: {
  isOpen: boolean;
  onClose: () => void;
  onDragStart: (e: React.MouseEvent<HTMLElement>, item: ResearchItem) => void;
}) {
  const [query, setQuery] = useState('');
  const [files, setFiles] = useState<VaultDocument[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  const loadVaultFiles = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await fetch('/api/v1/documents/?limit=200');
      if (!res.ok) throw new Error(`Failed to load vault files (${res.status})`);
      const data = (await res.json()) as { documents?: VaultDocument[] };
      setFiles(Array.isArray(data.documents) ? data.documents : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load vault files');
      setFiles([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!props.isOpen) return;
    void loadVaultFiles();
  }, [props.isOpen]);

  const onPickUpload = () => uploadInputRef.current?.click();

  const onFilesSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files;
    if (!selected || selected.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      for (const file of Array.from(selected)) {
        const form = new FormData();
        form.append('file', file);
        form.append('title', file.name.replace(/\.pdf$/i, ''));

        const res = await fetch('/api/v1/documents/upload', {
          method: 'POST',
          body: form,
        });
        if (!res.ok) {
          const detail = await res.text();
          throw new Error(detail || `Upload failed (${res.status})`);
        }
      }

      await loadVaultFiles();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setIsUploading(false);
      if (uploadInputRef.current) uploadInputRef.current.value = '';
    }
  };

  const filtered = files.filter((item) => item.title.toLowerCase().includes(query.toLowerCase()));

  if (!props.isOpen) return null;

  return (
    <div className="fixed left-4 right-4 top-20 bottom-4 sm:left-28 sm:right-auto sm:top-20 sm:bottom-8 sm:w-80 glass-panel border border-white/10 rounded-2xl shadow-2xl flex flex-col z-40 overflow-hidden animate-fade-in-left">
      <div className="p-5 border-b border-white/10 flex justify-between items-center bg-legal-surface/50">
        <div className="flex items-center gap-2 text-legal-gold">
          <ShieldAlert size={18} />
          <h3 className="font-serif font-bold text-base tracking-wide text-legal-text">Case Vault</h3>
        </div>
        <button onClick={props.onClose} className="text-slate-400 hover:text-white transition-colors" title="Close" aria-label="Close">
          <X size={18} />
        </button>
      </div>

      <div className="p-5 space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
          <input
            type="text"
            placeholder="Search files..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-black/20 border border-white/10 rounded-lg pl-9 pr-4 py-2.5 text-xs text-slate-200 focus:border-legal-gold/50 outline-none glass-input transition-all"
          />
        </div>
        <button
          type="button"
          onClick={onPickUpload}
          disabled={isUploading}
          className="w-full border-2 border-dashed border-white/10 rounded-xl p-4 flex flex-col items-center justify-center text-slate-500 hover:text-legal-gold hover:border-legal-gold/30 hover:bg-white/5 transition-all cursor-pointer disabled:opacity-60"
        >
          <Upload size={20} className="mb-2" />
          <span className="text-[10px] font-medium uppercase tracking-wider">{isUploading ? 'Uploading...' : 'Upload New File'}</span>
        </button>
        <input
          ref={uploadInputRef}
          type="file"
          aria-label="Upload case documents"
          accept="application/pdf"
          multiple
          className="hidden"
          onChange={onFilesSelected}
        />
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        <div className="flex items-center gap-2 text-[10px] text-slate-500 font-medium mb-2">
          <FileText size={10} className="text-legal-gold" />
          <span>UPLOADED DOCUMENTS</span>
        </div>

        {isLoading && <div className="text-xs text-slate-500">Loading vault files...</div>}
        {!isLoading && error && <div className="text-xs text-rose-300">{error}</div>}
        {!isLoading && !error && filtered.length === 0 && <div className="text-xs text-slate-500">No uploaded files yet.</div>}

        {filtered.map((item) => (
          <button
            type="button"
            key={item.id}
            onMouseDown={(e) => props.onDragStart(e, item)}
            className="w-full text-left bg-legal-surface/40 border border-white/5 rounded-xl p-4 cursor-grab active:cursor-grabbing hover:border-legal-gold/30 hover:bg-legal-surface/60 transition-all group select-none"
            aria-label={`Drag ${item.title}`}
          >
            <div className="flex justify-between items-start mb-1">
              <span className="text-[10px] px-1.5 py-0.5 rounded border text-slate-400 border-white/10 bg-white/5">
                {item.type}
              </span>
              <GripVertical size={14} className="text-slate-600 group-hover:text-slate-400" />
            </div>
            <h4 className="text-sm font-bold text-legal-text mb-1 truncate font-serif">{item.title}</h4>
            <div className="flex justify-between items-center mt-2">
              <div className="flex items-center gap-1 text-[10px] text-slate-500 font-mono">
                <Clock size={10} />
                <span>{item.date}</span>
              </div>
              <span className="text-[10px] text-slate-600 font-mono">{item.size}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
