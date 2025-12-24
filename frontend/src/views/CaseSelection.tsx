import { ChevronRight, Plus } from 'lucide-react';
import type { CaseData } from '../types';

export function CaseSelection(props: { onSelectCase: (c: CaseData) => void; onNewCase: () => void }) {
  const cases: CaseData[] = [
    { id: 1, title: 'State vs. Sharma', type: 'Criminal', date: 'Oct 12, 2023', status: 'Active' },
    { id: 2, title: 'Mehta Property Dispute', type: 'Civil', date: 'Sep 28, 2023', status: 'Pending' },
    { id: 3, title: 'TechCorp Merger', type: 'Corporate', date: 'Aug 15, 2023', status: 'Closed' },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-screen w-full text-legal-text relative overflow-hidden bg-legal-bg">
      <div className="absolute inset-0 container-bg z-0 opacity-50"></div>
      <div className="z-10 w-full max-w-4xl px-4 sm:px-8">
        <h2 className="text-4xl font-bold font-serif mb-12 text-center tracking-tight">Your Cases</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cases.map((c) => (
            <button
              type="button"
              key={c.id}
              onClick={() => props.onSelectCase(c)}
              className="text-left glass-panel border border-white/5 hover:border-legal-gold/50 rounded-xl p-6 cursor-pointer transition-all duration-300 hover:bg-legal-surface/80 hover:shadow-xl hover:-translate-y-1 group"
              aria-label={`Open case ${c.title}`}
            >
              <div className="flex justify-between items-start mb-4">
                <div
                  className={`w-2 h-2 rounded-full ${
                    c.status === 'Active' ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : c.status === 'Pending' ? 'bg-legal-gold shadow-[0_0_8px_rgba(212,175,55,0.6)]' : 'bg-slate-500'
                  }`}
                ></div>
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-medium">{c.type}</span>
              </div>
              <h3 className="text-xl font-bold text-legal-text mb-2 group-hover:text-legal-gold transition-colors font-serif">{c.title}</h3>
              <p className="text-xs text-slate-400 mb-6">Last updated: {c.date}</p>
              <div className="flex items-center text-xs text-slate-500 font-medium group-hover:text-legal-gold transition-colors">
                <span>Open Case</span>
                <ChevronRight size={14} className="ml-1" />
              </div>
            </button>
          ))}

          <button
            type="button"
            onClick={props.onNewCase}
            className="border-2 border-dashed border-white/10 hover:border-legal-gold/50 rounded-xl p-6 cursor-pointer transition-all duration-300 hover:bg-white/5 flex flex-col items-center justify-center text-slate-500 hover:text-legal-gold min-h-[180px] group"
            aria-label="Add new case"
          >
            <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform border border-white/10 group-hover:border-legal-gold/30">
              <Plus size={24} />
            </div>
            <span className="font-medium tracking-wide">Add New Case</span>
          </button>
        </div>
      </div>
    </div>
  );
}
