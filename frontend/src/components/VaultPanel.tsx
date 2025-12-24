import { useState } from 'react';
import { Clock, FileText, GripVertical, Search, ShieldAlert, Upload, X } from 'lucide-react';
import type { ResearchItem } from './ResearchPanel';

export function VaultPanel(props: {
  isOpen: boolean;
  onClose: () => void;
  onDragStart: (e: React.MouseEvent<HTMLElement>, item: ResearchItem) => void;
}) {
  const [query, setQuery] = useState('');

  const files: ResearchItem[] = [
    { id: 'v1', title: 'Witness_Statement_A.pdf', type: 'Statement', size: '2.4 MB', date: '12 Oct 2023' },
    { id: 'v2', title: 'Crime_Scene_Photos.zip', type: 'Evidence', size: '156 MB', date: '12 Oct 2023' },
    { id: 'v3', title: 'Ballistics_Report_Final.pdf', type: 'Evidence', size: '4.1 MB', date: '14 Oct 2023' },
    { id: 'v4', title: 'CCTV_Footage_Cam04.mp4', type: 'Evidence', size: '840 MB', date: '12 Oct 2023' },
    { id: 'v5', title: 'Call_Logs_Dump.csv', type: 'Evidence', size: '12 KB', date: '13 Oct 2023' },
  ];

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
        <div className="border-2 border-dashed border-white/10 rounded-xl p-4 flex flex-col items-center justify-center text-slate-500 hover:text-legal-gold hover:border-legal-gold/30 hover:bg-white/5 transition-all cursor-pointer">
          <Upload size={20} className="mb-2" />
          <span className="text-[10px] font-medium uppercase tracking-wider">Upload New File</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        <div className="flex items-center gap-2 text-[10px] text-slate-500 font-medium mb-2">
          <FileText size={10} className="text-legal-gold" />
          <span>UPLOADED DOCUMENTS</span>
        </div>

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
