import { ChevronRight, Plus } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { CaseData } from '../types';

type ApiCase = {
  id: string;
  case_number: string;
  title: string;
  court: string;
  bench?: string | null;
  status: string;
  filing_date: string;
};

function formatCourt(court: string): string {
  const text = String(court || '').replace(/_/g, ' ').trim();
  return text ? text.toUpperCase() : 'OTHER';
}

function formatDate(raw: string): string {
  if (!raw) return 'Unknown';
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleDateString('en-IN', { month: 'short', day: '2-digit', year: 'numeric' });
}

function mapStatus(raw: string): 'Active' | 'Pending' | 'Closed' {
  const s = String(raw || '').toLowerCase();
  if (s === 'disposed' || s === 'closed' || s === 'decided') return 'Closed';
  if (s === 'listed' || s === 'reserved' || s === 'adjourned') return 'Pending';
  return 'Active';
}

export function CaseSelection(props: { onSelectCase: (c: CaseData) => void; onNewCase: () => void }) {
  const [apiCases, setApiCases] = useState<ApiCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadCases = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch('/api/v1/cases/');
        if (!res.ok) {
          throw new Error(`Failed to load cases (${res.status})`);
        }

        const payload = await res.json() as { cases?: ApiCase[] };
        if (!cancelled) {
          setApiCases(Array.isArray(payload.cases) ? payload.cases : []);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load cases');
          setApiCases([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void loadCases();
    return () => {
      cancelled = true;
    };
  }, []);

  const cases: CaseData[] = useMemo(
    () =>
      apiCases.map((c, idx) => ({
        id: c.id || String(idx + 1),
        title: c.title || c.case_number || `Case ${idx + 1}`,
        type: formatCourt(c.court),
        date: formatDate(c.filing_date),
        status: mapStatus(c.status),
        caseNumber: c.case_number,
        court: c.court,
        bench: c.bench ?? null,
      })),
    [apiCases],
  );

  const filteredCases = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return cases;
    return cases.filter((c) => {
      const hay = [c.title, c.caseNumber || '', c.court || '', c.type, c.status].join(' ').toLowerCase();
      return hay.includes(q);
    });
  }, [cases, search]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        const el = document.getElementById('case-search-input') as HTMLInputElement | null;
        el?.focus();
        el?.select();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen w-full text-legal-text relative overflow-hidden bg-legal-bg">
      <div className="absolute inset-0 container-bg z-0 opacity-50"></div>
      <div className="z-10 w-full max-w-4xl px-4 sm:px-8">
        <h2 className="text-4xl font-bold font-serif mb-12 text-center tracking-tight">Your Cases</h2>
        <div className="mb-6 flex items-center justify-center">
          <div className="w-full max-w-xl">
            <input
              id="case-search-input"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, case number, court, status (Ctrl+K)"
              className="w-full glass-input rounded-xl px-4 py-3 text-sm text-slate-200 border border-white/10 focus:border-legal-gold/40 outline-none"
              aria-label="Search cases"
            />
          </div>
        </div>
        {loading && <p className="text-center text-slate-400 mb-6 text-sm">Loading live cases...</p>}
        {!loading && error && <p className="text-center text-rose-300 mb-6 text-sm">{error}</p>}
        {!loading && !error && filteredCases.length === 0 && (
          <p className="text-center text-slate-400 mb-6 text-sm">No cases found yet. Add or upload documents to create case history.</p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCases.map((c) => (
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
