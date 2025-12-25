import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ResearchPanel, ResearchItem } from './components/ResearchPanel';
import { RadialMenu } from './components/RadialMenu';
import { ChatPanel } from './components/ChatPanel';
import { ToolsDock } from './components/ToolsDock';
import { VaultPanel } from './components/VaultPanel';
import { DocumentNode } from './components/DetectiveWall/DocumentNode';
import { ConnectionLine } from './components/DetectiveWall/ConnectionLine';
import { NodeDetailsPanel } from './components/DetectiveWall/NodeDetailsPanel';
import { LandingPage } from './views/LandingPage';
import { CaseSelection } from './views/CaseSelection';
import {
  AlertTriangle,
  ChevronRight,
  Gavel,
  MessageSquare,
  Plus,
  ShieldAlert,
  Sparkles,
  Upload,
  X,
} from 'lucide-react';
import type {
  View,
  ActiveTab,
  ToolId,
  AnalyticsMode,
  DevilsAdvocateResponse,
  CaseData,
  NodeData,
  Connection,
  WallInsightSeverity,
  WallAnalyzeResponse,
  ChatMessage,
  CourtValue,
  DocumentTemplate,
  FormattingRules,
  ShepardizeStatus,
  ShepardizeResult,
} from './types';

type ChatLanguage = 'en' | 'hi' | 'mr';
type OutputScript = 'native' | 'roman';

type GlossaryResponse = {
  term?: string;
  definition?: string;
  category?: string | null;
};

function escapeRegExp(input: string) {
  return input.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function useLegalTermRenderer() {
  const cacheRef = useRef<Record<string, GlossaryResponse | null>>({});

  // Fallback list (used when backend doesn't provide preservedTerms).
  const FALLBACK_TERMS = useMemo(
    () => [
      'Anticipatory Bail',
      'Writ Petition',
      'Special Leave Petition',
      'Stay Order',
      'Interim Relief',
      'Habeas Corpus',
      'Mandamus',
      'Certiorari',
      'Quo Warranto',
      'Res Judicata',
      'Prima Facie',
      'FIR',
      'IPC',
      'CrPC',
      'CPC',
    ],
    []
  );

  const fetchDefinition = useCallback(async (term: string) => {
    const key = term.toLowerCase();
    if (Object.prototype.hasOwnProperty.call(cacheRef.current, key)) return;
    cacheRef.current[key] = null;
    try {
      const res = await fetch(`/api/v1/translate/glossary/${encodeURIComponent(term)}`);
      if (!res.ok) return;
      const data = (await res.json()) as GlossaryResponse;
      cacheRef.current[key] = data;
    } catch {
      // ignore
    }
  }, []);

  const render = useCallback(
    (content: string, msg?: ChatMessage) => {
      const terms = (msg?.preservedTerms && msg.preservedTerms.length ? msg.preservedTerms : FALLBACK_TERMS)
        .filter((t) => typeof t === 'string' && t.trim().length)
        .map((t) => t.trim());

      if (!terms.length) return content;

      const canonicalByLower: Record<string, string> = {};
      for (const t of terms) canonicalByLower[t.toLowerCase()] = t;

      const re = new RegExp(`(${[...terms].sort((a, b) => b.length - a.length).map(escapeRegExp).join('|')})`, 'gi');
      const parts = content.split(re);
      if (parts.length === 1) return content;

      return parts.map((p, idx) => {
        const canonical = canonicalByLower[p.toLowerCase()];
        if (!canonical) return <span key={idx}>{p}</span>;

        const cached = cacheRef.current[canonical.toLowerCase()];
        const title = cached?.definition || 'Loading definition…';

        return (
          <span
            key={idx}
            onMouseEnter={() => void fetchDefinition(canonical)}
            title={title}
            className="underline decoration-dotted underline-offset-4 text-legal-gold/90"
          >
            {p}
          </span>
        );
      });
    },
    [FALLBACK_TERMS, fetchDefinition]
  );

  return render;
}

function DraftingStudio() {
  const editorRef = useRef<HTMLTextAreaElement | null>(null);
  const dictateInputRef = useRef<HTMLInputElement | null>(null);

  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);

  const [court, setCourt] = useState<CourtValue>('high_court');
  const [rules, setRules] = useState<FormattingRules | null>(null);
  const [isLoadingRules, setIsLoadingRules] = useState(false);

  const [documentType, setDocumentType] = useState<string>('writ_petition');
  const [paperType, setPaperType] = useState<'A4' | 'Legal'>('A4');
  const [caseNumber, setCaseNumber] = useState<string>('');
  const [petitioner, setPetitioner] = useState<string>('Petitioner');
  const [respondent, setRespondent] = useState<string>('Respondent');

  const [content, setContent] = useState<string>('');
  const [previewHtml, setPreviewHtml] = useState<string>('');
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null);

  const [slashOpen, setSlashOpen] = useState(false);
  const [slashQuery, setSlashQuery] = useState('');
  const [criticOpen, setCriticOpen] = useState(false);
  const [criticOutput, setCriticOutput] = useState<string>('');
  const [isDictating, setIsDictating] = useState(false);

  const [citationStatusByLine, setCitationStatusByLine] = useState<Record<number, ShepardizeResult>>({});

  const selectedTemplate = templates.find((t) => t.id === documentType);

  // Load saved draft (best-effort)
  useEffect(() => {
    try {
      const raw = localStorage.getItem('jr_drafting_state_v1');
      if (!raw) return;
      const parsed = JSON.parse(raw) as Record<string, unknown>;
      if (typeof parsed !== 'object' || parsed === null) return;

      if (typeof parsed.court === 'string') setCourt(parsed.court as CourtValue);
      if (typeof parsed.documentType === 'string') setDocumentType(parsed.documentType);
      if (typeof parsed.paperType === 'string') setPaperType(parsed.paperType as 'A4' | 'Legal');
      if (typeof parsed.caseNumber === 'string') setCaseNumber(parsed.caseNumber);
      if (typeof parsed.petitioner === 'string') setPetitioner(parsed.petitioner);
      if (typeof parsed.respondent === 'string') setRespondent(parsed.respondent);
      if (typeof parsed.content === 'string') setContent(parsed.content);

      const ts = typeof parsed.lastSavedAt === 'number' ? parsed.lastSavedAt : null;
      setLastSavedAt(ts);
      setSaveState(ts ? 'saved' : 'idle');
    } catch {
      // ignore
    }
    // Only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-save draft state (debounced)
  useEffect(() => {
    setSaveState('saving');
    const t = window.setTimeout(() => {
      try {
        const ts = Date.now();
        localStorage.setItem(
          'jr_drafting_state_v1',
          JSON.stringify({
            court,
            documentType,
            paperType,
            caseNumber,
            petitioner,
            respondent,
            content,
            lastSavedAt: ts,
          })
        );
        setLastSavedAt(ts);
        setSaveState('saved');
      } catch {
        setSaveState('idle');
      }
    }, 650);

    return () => window.clearTimeout(t);
  }, [caseNumber, content, court, documentType, paperType, petitioner, respondent]);

  const makeRequestBody = useCallback(
    () => ({
      content: content || ' ',
      document_type: documentType,
      court,
      case_number: caseNumber || '—',
      petitioner: petitioner || 'Petitioner',
      respondent: respondent || 'Respondent',
    }),
    [caseNumber, content, court, documentType, petitioner, respondent]
  );

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setIsLoadingTemplates(true);
      try {
        const res = await fetch('/api/v1/format/templates');
        if (!res.ok) throw new Error('Failed to load templates');
        const data = (await res.json()) as { templates: DocumentTemplate[] };
        if (cancelled) return;
        setTemplates(data.templates ?? []);
        if (data.templates?.length && !data.templates.some((t) => t.id === documentType)) {
          setDocumentType(data.templates[0].id);
        }
      } catch {
        if (!cancelled) setTemplates([]);
      } finally {
        if (!cancelled) setIsLoadingTemplates(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setIsLoadingRules(true);
      setError(null);
      try {
        const res = await fetch(`/api/v1/format/rules/${court}`);
        if (!res.ok) throw new Error('Failed to load court rules');
        const data = (await res.json()) as FormattingRules;
        if (!cancelled) setRules(data);
      } catch {
        if (!cancelled) setRules(null);
      } finally {
        if (!cancelled) setIsLoadingRules(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [court]);

  // Live preview (debounced)
  useEffect(() => {
    let cancelled = false;
    const t = window.setTimeout(async () => {
      setError(null);
      try {
        const res = await fetch('/api/v1/format/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(makeRequestBody()),
        });
        if (!res.ok) throw new Error('Preview failed');
        const html = await res.text();
        if (!cancelled) setPreviewHtml(html);
      } catch {
        if (!cancelled) setPreviewHtml('');
      }
    }, 450);

    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [makeRequestBody]);

  // Citation validity (debounced)
  useEffect(() => {
    const lines = content.split('\n');

    // Basic citation detector: tries to catch common Indian citation shapes.
    const citationRegex = /\b\(?(\d{4})\)?\s*\d+\s*SCC\s*\d+\b|\bAIR\s*\d{4}\s*SC\s*\d+\b|\b\d{4}\s*\(?\d+\)?\s*SCR\s*\d+\b/gi;

    const found: Array<{ lineIndex: number; citation: string }> = [];
    lines.forEach((line, idx) => {
      const m = line.match(citationRegex);
      if (m && m.length) found.push({ lineIndex: idx, citation: m[0] });
    });

    if (found.length === 0) {
      setCitationStatusByLine({});
      return;
    }

    let cancelled = false;
    const t = window.setTimeout(async () => {
      const updates: Record<number, ShepardizeResult> = {};
      await Promise.all(
        found.map(async (f) => {
          try {
            const safe = encodeURIComponent(f.citation);
            const res = await fetch(`/api/v1/research/shepardize/${safe}`);
            if (!res.ok) throw new Error('bad');
            const data = (await res.json()) as { status?: string; status_emoji?: string; message?: string };
            const status = (data.status as ShepardizeStatus) || 'unknown';
            updates[f.lineIndex] = { status, status_emoji: data.status_emoji, message: data.message };
          } catch {
            updates[f.lineIndex] = { status: 'unknown', status_emoji: '⚪', message: 'Unknown status' };
          }
        })
      );

      if (!cancelled) setCitationStatusByLine(updates);
    }, 500);

    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [content]);

  const statusDot = (status: ShepardizeStatus) => {
    if (status === 'overruled') return 'bg-rose-500';
    if (status === 'distinguished') return 'bg-amber-400';
    if (status === 'good_law') return 'bg-emerald-400';
    return 'bg-slate-500';
  };

  const slashItems = [
    { id: 'jurisdiction', label: 'Jurisdiction', insert: 'JURISDICTION\n\nThat this Hon\'ble Court has jurisdiction to entertain the present petition because…\n' },
    { id: 'facts', label: 'Facts', insert: 'FACTS\n\n1. That…\n2. That…\n' },
    { id: 'grounds', label: 'Grounds', insert: 'GROUNDS\n\nA. Because…\nB. Because…\n' },
    { id: 'prayer', label: 'Prayer Clause', insert: 'PRAYER\n\nIt is, therefore, most respectfully prayed that this Hon\'ble Court may be pleased to…\n' },
    { id: 'verification', label: 'Verification', insert: 'VERIFICATION\n\nVerified at ______ on this ___ day of ______ that the contents of the above are true and correct…\n' },
  ];

  const filteredSlash = slashItems.filter((i) => i.label.toLowerCase().includes(slashQuery.toLowerCase()));

  const insertAtCursor = (text: string) => {
    const el = editorRef.current;
    if (!el) {
      setContent((prev) => prev + text);
      return;
    }
    const start = el.selectionStart ?? content.length;
    const end = el.selectionEnd ?? content.length;
    const before = content.slice(0, start);
    const after = content.slice(end);
    const next = before + text + after;
    setContent(next);
    window.requestAnimationFrame(() => {
      el.focus();
      const pos = start + text.length;
      el.setSelectionRange(pos, pos);
    });
  };

  const handleDictateClick = () => {
    dictateInputRef.current?.click();
  };

  const handleDictateFileSelected = async (file: File | null) => {
    if (!file) return;
    setError(null);
    setIsDictating(true);
    try {
      const form = new FormData();
      form.append('file', file);

      const res = await fetch('/api/v1/audio/transcribe', {
        method: 'POST',
        body: form,
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || 'Transcription failed');
      }

      const data = (await res.json()) as { text?: string };
      const text = (data.text || '').trim();
      if (!text) throw new Error('No speech detected');

      insertAtCursor(`${text}\n`);
    } catch {
      setError('Could not transcribe audio.');
    } finally {
      setIsDictating(false);
      if (dictateInputRef.current) dictateInputRef.current.value = '';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Productivity shortcuts
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (e.shiftKey) {
        void handleReviewDraft();
      } else {
        void handleFormatOnce();
      }
      return;
    }

    if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
      // Open the slash menu after the character is actually inserted.
      window.setTimeout(() => {
        setSlashOpen(true);
        setSlashQuery('');
      }, 0);
      return;
    }

    if (slashOpen) {
      if (e.key === 'Escape') {
        setSlashOpen(false);
        setSlashQuery('');
        return;
      }
      if (e.key === 'Backspace') {
        // Let textarea update content; slashQuery is derived lightly by user typing.
        return;
      }
      if (e.key.length === 1 && !e.metaKey && !e.ctrlKey && !e.altKey) {
        // Keep a minimal query to filter list.
        setSlashQuery((q) => (q + e.key).slice(0, 24));
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        const first = filteredSlash[0];
        if (first) {
          insertAtCursor(first.insert);
        }
        setSlashOpen(false);
        setSlashQuery('');
      }
    }
  };

  const lines = useMemo(() => content.split('\n'), [content]);
  const wordCount = useMemo(() => {
    const t = content.trim();
    if (!t) return 0;
    return t.split(/\s+/g).filter(Boolean).length;
  }, [content]);
  const charCount = content.length;
  const lineCount = lines.length;
  const citationLines = Object.values(citationStatusByLine);
  const citeGood = citationLines.filter((c) => c.status === 'good_law').length;
  const citeWarn = citationLines.filter((c) => c.status === 'distinguished').length;
  const citeBad = citationLines.filter((c) => c.status === 'overruled').length;

  const handleFormatOnce = async () => {
    setError(null);
    setIsWorking(true);
    try {
      const res = await fetch('/api/v1/format/document', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(makeRequestBody()),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || 'Formatting failed');
      }
      const data = (await res.json()) as { formatted_text?: string };
      if (data.formatted_text) {
        setContent(data.formatted_text);
      }
    } catch {
      setError('Could not format the document.');
    } finally {
      setIsWorking(false);
    }
  };

  const handleOpenPreview = async () => {
    setError(null);
    setIsWorking(true);
    try {
      const res = await fetch('/api/v1/format/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(makeRequestBody()),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || 'Preview failed');
      }
      const html = await res.text();
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch {
      setError('Could not open preview.');
    } finally {
      setIsWorking(false);
    }
  };

  const handleDownloadDoc = async () => {
    try {
      const res = await fetch('/api/v1/format/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(makeRequestBody()),
      });
      if (!res.ok) throw new Error('failed');
      const html = await res.text();
      const blob = new Blob([html], { type: 'application/msword' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${documentType}-${court}.doc`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch {
      setError('Could not download document.');
    }
  };

  const handleReviewDraft = async () => {
    setError(null);
    setIsWorking(true);
    setCriticOpen(true);
    setCriticOutput('');
    try {
      const res = await fetch('/api/v1/research/devils-advocate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_summary: `${caseNumber || 'Case'}: ${petitioner} v. ${respondent}`,
          arguments: content || ' ',
          citations: [],
        }),
      });
      if (!res.ok) throw new Error('failed');
      const data = (await res.json()) as DevilsAdvocateResponse;

      const attackText = (data.attack_points || [])
        .slice(0, 12)
        .map((p, i) => {
          const lines = [
            `Attack ${i + 1}: ${p.title || 'Untitled'}`,
            p.weakness ? `- Weakness: ${p.weakness}` : null,
            p.counter_citation ? `- Counter-citation: ${p.counter_citation}` : null,
            p.suggested_attack ? `- Suggested attack: ${p.suggested_attack}` : null,
          ].filter(Boolean);
          return lines.join('\n');
        })
        .join('\n\n');

      const recs = (data.preparation_recommendations || []).map((r) => `- ${r}`).join('\n');
      const header = Number.isFinite(data.vulnerability_score)
        ? `Vulnerability score: ${data.vulnerability_score.toFixed(1)}/10`
        : 'Vulnerability score: N/A';

      setCriticOutput([header, attackText, recs ? `Preparation recommendations:\n${recs}` : null].filter(Boolean).join('\n\n') || 'No issues found.');
    } catch {
      setCriticOutput('Critic Agent is unavailable (missing LLM config).');
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <div className="flex-1 relative overflow-auto lg:overflow-hidden">
      <div className="absolute inset-0 container-bg z-0" />
      <div className="relative z-10 flex flex-col lg:flex-row min-h-full">
        {/* Left: Workspace */}
        <div className="w-full lg:w-1/2 min-w-0 lg:min-w-[520px] glass-panel border-b lg:border-b-0 lg:border-r border-white/10 flex flex-col">
          <div className="p-4 border-b border-white/10 bg-gradient-to-r from-slate-800/40 to-slate-900/40">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white font-serif">Drafting Studio</h3>
                  <span className="text-[10px] text-slate-400 font-mono border border-white/10 rounded-full px-2 py-1">{paperType}</span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
                  <span>Type “/” to insert clauses.</span>
                  <span className="text-slate-500">Ctrl+Enter: Format</span>
                  <span className="text-slate-500">Ctrl+Shift+Enter: Review</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setSlashOpen(true);
                    setSlashQuery('');
                    window.requestAnimationFrame(() => editorRef.current?.focus());
                  }}
                  className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 text-xs font-bold tracking-wider transition-colors"
                  aria-label="Insert clause"
                  title="Insert clause"
                >
                  INSERT
                </button>
                <input
                  ref={dictateInputRef}
                  type="file"
                  accept="audio/*,video/webm,video/mp4"
                  aria-label="Dictation audio file"
                  title="Dictation audio file"
                  className="hidden"
                  onChange={(e) => handleDictateFileSelected(e.target.files?.[0] ?? null)}
                />
                <button
                  onClick={handleDictateClick}
                  disabled={isWorking || isDictating}
                  className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 text-xs font-bold tracking-wider disabled:opacity-50 transition-colors"
                >
                  {isDictating ? 'DICTATING…' : 'DICTATE'}
                </button>
                <button
                  onClick={handleReviewDraft}
                  disabled={isWorking || !content.trim()}
                  className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 text-xs font-bold tracking-wider disabled:opacity-50 transition-colors"
                >
                  REVIEW DRAFT
                </button>
                <button
                  onClick={handleFormatOnce}
                  disabled={isWorking || !content.trim()}
                  className="px-3 py-2 rounded-lg bg-legal-gold text-legal-bg text-xs font-bold tracking-wider shadow-glow hover:bg-yellow-400 transition-colors disabled:opacity-50"
                >
                  {isWorking ? 'WORKING…' : 'FORMAT'}
                </button>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono">
                <span className="px-2 py-1 rounded-full border border-white/10 text-slate-400 bg-white/5">{wordCount} words</span>
                <span className="px-2 py-1 rounded-full border border-white/10 text-slate-400 bg-white/5">{charCount} chars</span>
                <span className="px-2 py-1 rounded-full border border-white/10 text-slate-400 bg-white/5">{lineCount} lines</span>
                <span className="px-2 py-1 rounded-full border border-emerald-500/30 text-emerald-200 bg-emerald-500/10">{citeGood} good</span>
                <span className="px-2 py-1 rounded-full border border-amber-500/30 text-amber-200 bg-amber-500/10">{citeWarn} caution</span>
                <span className="px-2 py-1 rounded-full border border-rose-500/30 text-rose-200 bg-rose-500/10">{citeBad} bad</span>
              </div>

              <div className="text-[10px] text-slate-500 font-mono">
                {saveState === 'saving' && 'Saving…'}
                {saveState === 'saved' && lastSavedAt ? `Saved ${new Date(lastSavedAt).toLocaleTimeString()}` : null}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-4">
              <div>
                <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Format</div>
                <div className="mt-1 grid grid-cols-2 gap-2">
                  <select
                    value={court}
                    onChange={(e) => setCourt(e.target.value as CourtValue)}
                    aria-label="Court"
                    className="w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  >
                    <option value="supreme_court">Supreme Court</option>
                    <option value="high_court">High Court</option>
                    <option value="district_court">District Court</option>
                    <option value="tribunal">Tribunal</option>
                    <option value="other">Other</option>
                  </select>
                  <select
                    value={documentType}
                    onChange={(e) => setDocumentType(e.target.value)}
                    aria-label="Document template"
                    className="w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  >
                    {isLoadingTemplates && <option>Loading…</option>}
                    {!isLoadingTemplates && templates.length === 0 && <option value="writ_petition">Writ Petition</option>}
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>
                {selectedTemplate?.description && (
                  <div className="mt-2 text-[11px] text-slate-500 leading-relaxed">{selectedTemplate.description}</div>
                )}
              </div>

              <div>
                <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Case Details</div>
                <div className="mt-1 grid grid-cols-2 gap-2">
                  <input
                    value={caseNumber}
                    onChange={(e) => setCaseNumber(e.target.value)}
                    aria-label="Case number"
                    placeholder="Case No."
                    className="w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  />
                  <select
                    value={paperType}
                    onChange={(e) => setPaperType(e.target.value as 'A4' | 'Legal')}
                    aria-label="Paper type"
                    className="w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  >
                    <option value="A4">A4</option>
                    <option value="Legal">Legal</option>
                  </select>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <input
                    value={petitioner}
                    onChange={(e) => setPetitioner(e.target.value)}
                    placeholder="Petitioner"
                    className="w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  />
                  <input
                    value={respondent}
                    onChange={(e) => setRespondent(e.target.value)}
                    placeholder="Respondent"
                    className="w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="mt-3 bg-rose-950/40 border border-rose-900/50 rounded-lg p-3 text-xs text-rose-200">
                {error}
              </div>
            )}
          </div>

          <div className="flex-1 relative">
            <div className="absolute inset-0 overflow-auto">
              <div className="min-h-full flex">
                {/* Gutter (scrolls with editor) */}
                <div className="w-14 flex-shrink-0 bg-black/20 border-r border-white/10 text-[10px] text-slate-500 font-mono pt-4">
                  {lines.map((_, idx) => {
                    const hit = citationStatusByLine[idx];
                    return (
                      <div key={idx} className="h-5 flex items-center justify-between px-2">
                        <span>{idx + 1}</span>
                        {hit ? (
                          <span
                            className={`w-2 h-2 rounded-full ${statusDot(hit.status)}`}
                            title={hit.message || hit.status}
                            aria-label={hit.message || hit.status}
                          ></span>
                        ) : (
                          <span className="w-2 h-2" aria-hidden="true"></span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Editor */}
                <div className="relative flex-1">
                  <textarea
                    ref={editorRef}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    onKeyDown={handleKeyDown}
                    spellCheck={false}
                    aria-label="Draft editor"
                    placeholder="Start drafting here…\n\nTip: type /prayer or /verification"
                    className="block w-full min-h-[420px] lg:min-h-[calc(100vh-210px)] px-4 py-4 bg-transparent text-slate-200 outline-none resize-none font-mono text-xs leading-5"
                  />

                  {/* Slash menu */}
                  {slashOpen && (
                    <div className="absolute left-2 top-4 z-40 w-72 glass-panel border border-white/10 rounded-xl shadow-2xl overflow-hidden">
                      <div className="px-3 py-2 border-b border-white/10 text-[10px] text-slate-500 font-mono">
                        /{slashQuery || '…'}
                      </div>
                      <div className="max-h-64 overflow-auto">
                        {filteredSlash.map((item) => (
                          <button
                            key={item.id}
                            onClick={() => {
                              insertAtCursor(item.insert);
                              setSlashOpen(false);
                              setSlashQuery('');
                            }}
                            aria-label={`Insert ${item.label}`}
                            title={`Insert ${item.label}`}
                            className="w-full text-left px-3 py-2 text-xs text-slate-200 hover:bg-white/5 flex items-center justify-between"
                          >
                            <span>{item.label}</span>
                            <ChevronRight size={14} className="text-slate-500" />
                          </button>
                        ))}
                        {filteredSlash.length === 0 && (
                          <div className="px-3 py-3 text-xs text-slate-500">No matching clauses.</div>
                        )}
                      </div>
                      <div className="px-3 py-2 border-t border-white/10 flex justify-end">
                        <button
                          onClick={() => {
                            setSlashOpen(false);
                            setSlashQuery('');
                          }}
                          aria-label="Close slash menu"
                          title="Close"
                          className="text-xs text-slate-400 hover:text-slate-200"
                        >
                          Close
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Live preview + agentic sidebar */}
        <div className="w-full lg:flex-1 flex flex-col lg:flex-row bg-black/20 backdrop-blur-xl">
          <div className="flex-1 p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h4 className="text-sm font-bold text-white">Live Preview</h4>
                <div className="text-xs text-slate-500">WYSIWYG court layout (updates as you type)</div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleOpenPreview}
                  disabled={isWorking}
                  className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 text-xs font-bold tracking-wider disabled:opacity-50 transition-colors"
                >
                  OPEN
                </button>
                <button
                  onClick={handleDownloadDoc}
                  disabled={isWorking}
                  className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 text-xs font-bold tracking-wider disabled:opacity-50 transition-colors"
                >
                  DOWNLOAD
                </button>
              </div>
            </div>

            {!previewHtml && (
              <div className="mb-3 text-[11px] text-slate-500">
                Preview will appear here when the formatting service is available.
              </div>
            )}

            <div className="rounded-xl overflow-hidden border border-white/10 bg-black/20 shadow-2xl">
              {previewHtml ? (
                <iframe title="preview" className="w-full h-[420px] lg:h-[calc(100vh-170px)]" sandbox="allow-same-origin" srcDoc={previewHtml} />
              ) : (
                <div className="h-[420px] lg:h-[calc(100vh-170px)] flex items-center justify-center text-slate-500 text-sm">
                  Preview unavailable.
                </div>
              )}
            </div>

          </div>

          <div className="w-full lg:w-[360px] border-t lg:border-t-0 lg:border-l border-white/10 glass-panel flex flex-col">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2 text-legal-gold">
                <ShieldAlert size={16} />
                <span className="text-xs font-bold tracking-wider uppercase">Agentic Sidebar</span>
              </div>
              <button
                onClick={() => setCriticOpen((v) => !v)}
                className="text-slate-400 hover:text-slate-200"
                title="Toggle"
                aria-label="Toggle agentic sidebar"
              >
                {criticOpen ? <X size={16} /> : <ChevronRight size={16} />}
              </button>
            </div>

            {criticOpen ? (
              <div className="flex-1 overflow-y-auto p-4">
                <button
                  onClick={handleReviewDraft}
                  disabled={isWorking || !content.trim()}
                  className="w-full px-4 py-2 rounded-lg bg-legal-gold/10 border border-legal-gold/30 text-legal-gold text-xs font-bold tracking-wider hover:bg-legal-gold/20 disabled:opacity-50 transition-colors"
                >
                  REVIEW DRAFT
                </button>

                <div className="mt-4 bg-black/20 border border-white/10 rounded-xl p-3">
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 font-bold tracking-wider uppercase mb-2">
                    <AlertTriangle size={12} className="text-legal-gold" />
                    <span>Critic Notes</span>
                  </div>
                  <pre className="whitespace-pre-wrap text-xs text-slate-200 leading-relaxed">
                    {criticOutput || 'Run Review Draft to get opposition points.'}
                  </pre>
                </div>

                <div className="mt-4 border-t border-white/10 pt-4">
                  <div className="flex items-center gap-2 text-[10px] text-slate-500 font-bold tracking-wider uppercase mb-2">
                    <Gavel size={12} />
                    <span>Court Rules</span>
                    {isLoadingRules && <span className="text-slate-600 font-normal">Loading…</span>}
                  </div>
                  {!rules && !isLoadingRules && <div className="text-xs text-slate-500">Rules unavailable.</div>}
                  {rules && (
                    <div className="text-xs text-slate-400 space-y-1">
                      <div className="flex justify-between"><span>Font</span><span className="text-slate-300">{rules.font_family} {rules.font_size}</span></div>
                      <div className="flex justify-between"><span>Line spacing</span><span className="text-slate-300">{rules.line_spacing}</span></div>
                      <div className="flex justify-between"><span>Margins</span><span className="text-slate-300">T{rules.margins.top} B{rules.margins.bottom} L{rules.margins.left} R{rules.margins.right}</span></div>
                      <div className="flex justify-between"><span>Indent</span><span className="text-slate-300">{rules.paragraph_indent}</span></div>
                      <div className="flex justify-between"><span>Page numbering</span><span className="text-slate-300">{rules.page_numbering}</span></div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-4 text-xs text-slate-500">Open to run “Review Draft” and see court rules.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

type JudgeAnalyticsPattern = {
  pattern: string;
  signal: 'low' | 'medium' | 'high';
  evidence: string[];
  caveats: string[];
};

type JudgeAnalyticsResponse = {
  judge_name: string;
  total_cases_analyzed: number;
  patterns: JudgeAnalyticsPattern[];
  recommendations: string[];
};

function StrategyAnalytics(props: { activeCase?: CaseData | null }) {
  const [mode, setMode] = useState<AnalyticsMode>('judge');

  const [judgeName, setJudgeName] = useState('');
  const [court, setCourt] = useState<CourtValue>('high_court');
  const [caseType, setCaseType] = useState('');
  const [excerpts, setExcerpts] = useState('');
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JudgeAnalyticsResponse | null>(null);

  const [caseSummary, setCaseSummary] = useState('');
  const [argumentsText, setArgumentsText] = useState('');
  const [citationsRaw, setCitationsRaw] = useState('');
  const [devilWorking, setDevilWorking] = useState(false);
  const [devilError, setDevilError] = useState<string | null>(null);
  const [devilResult, setDevilResult] = useState<DevilsAdvocateResponse | null>(null);

  useEffect(() => {
    if (caseSummary.trim()) return;
    if (props.activeCase?.title) {
      setCaseSummary(props.activeCase.title);
    }
  }, [props.activeCase?.title, caseSummary]);

  const splitExcerpts = (raw: string) => {
    const parts = raw
      .split(/\n---\n/g)
      .map((p) => p.trim())
      .filter(Boolean);
    return parts.length ? parts : raw.trim() ? [raw.trim()] : [];
  };

  const runAnalysis = async () => {
    setError(null);
    setResult(null);
    const judgments = splitExcerpts(excerpts);
    if (!judgeName.trim()) {
      setError('Enter a judge name.');
      return;
    }
    if (judgments.length === 0) {
      setError('Paste at least one judgment excerpt.');
      return;
    }

    setIsWorking(true);
    try {
      const res = await fetch('/api/v1/judges/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          judge_name: judgeName,
          court,
          case_type: caseType || null,
          judgments,
        }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `API error: ${res.status}`);
      }

      const data = (await res.json()) as JudgeAnalyticsResponse;
      setResult(data);
    } catch {
      setError('Judge analytics is unavailable (missing LLM config or backend not running).');
    } finally {
      setIsWorking(false);
    }
  };

  const splitCitations = (raw: string) =>
    raw
      .split(/\n+/g)
      .map((s) => s.trim())
      .filter(Boolean);

  const runDevilsAdvocate = async () => {
    setDevilError(null);
    setDevilResult(null);

    if (!caseSummary.trim()) {
      setDevilError('Enter a case summary.');
      return;
    }
    if (!argumentsText.trim()) {
      setDevilError('Enter your arguments to stress-test.');
      return;
    }

    setDevilWorking(true);
    try {
      const res = await fetch('/api/v1/research/devils-advocate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_summary: caseSummary,
          arguments: argumentsText,
          citations: splitCitations(citationsRaw),
        }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `API error: ${res.status}`);
      }

      const data = (await res.json()) as DevilsAdvocateResponse;
      setDevilResult(data);
    } catch {
      setDevilError("Devil's Advocate is unavailable (missing LLM config or backend not running).");
    } finally {
      setDevilWorking(false);
    }
  };

  const signalColor = (s: 'low' | 'medium' | 'high') => {
    if (s === 'high') return 'text-rose-300 border-rose-500/30 bg-rose-500/10';
    if (s === 'medium') return 'text-amber-300 border-amber-500/30 bg-amber-500/10';
    return 'text-emerald-300 border-emerald-500/30 bg-emerald-500/10';
  };

  return (
    <div className="flex-1 relative overflow-auto lg:overflow-hidden">
      <div className="absolute inset-0 container-bg z-0" />
      <div className="relative z-10 flex flex-col lg:flex-row min-h-full">
        <div className="w-full lg:w-1/2 min-w-0 lg:min-w-[520px] glass-panel border-b lg:border-b-0 lg:border-r border-white/10 flex flex-col">
          <div className="p-4 border-b border-white/10 bg-gradient-to-r from-slate-800/40 to-slate-900/40">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white font-serif">
                    Analytics / {mode === 'judge' ? 'Judge' : "Devil's Advocate"}
                  </h3>
                  {props.activeCase?.title && (
                    <span className="text-[10px] text-slate-400 font-mono border border-white/10 rounded-full px-2 py-1">
                      {props.activeCase.title}
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  {mode === 'judge'
                    ? 'Paste judgment excerpts (separate multiple with a line containing “---”).'
                    : 'Simulate opposing counsel and stress-test your arguments.'}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="flex items-center bg-black/20 border border-white/10 rounded-full p-1">
                  <button
                    type="button"
                    onClick={() => {
                      setMode('judge');
                      setError(null);
                      setDevilError(null);
                    }}
                    className={`px-3 py-1.5 rounded-full text-[11px] font-bold tracking-wider transition-colors ${
                      mode === 'judge'
                        ? 'bg-legal-gold/20 border border-legal-gold/30 text-legal-gold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    aria-label="Judge analytics"
                    title="Judge"
                  >
                    JUDGE
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('devils');
                      setError(null);
                      setDevilError(null);
                    }}
                    className={`px-3 py-1.5 rounded-full text-[11px] font-bold tracking-wider transition-colors ${
                      mode === 'devils'
                        ? 'bg-legal-gold/20 border border-legal-gold/30 text-legal-gold'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    aria-label="Devil's Advocate"
                    title="Devil's Advocate"
                  >
                    DEVIL'S
                  </button>
                </div>

                {mode === 'judge' ? (
                  <button
                    onClick={() => void runAnalysis()}
                    disabled={isWorking}
                    className="px-3 py-2 rounded-lg bg-legal-gold text-legal-bg text-xs font-bold tracking-wider shadow-glow hover:bg-yellow-400 transition-colors disabled:opacity-50"
                  >
                    {isWorking ? 'ANALYZING…' : 'ANALYZE'}
                  </button>
                ) : (
                  <button
                    onClick={() => void runDevilsAdvocate()}
                    disabled={devilWorking}
                    className="px-3 py-2 rounded-lg bg-legal-gold text-legal-bg text-xs font-bold tracking-wider shadow-glow hover:bg-yellow-400 transition-colors disabled:opacity-50"
                  >
                    {devilWorking ? 'SIMULATING…' : 'SIMULATE'}
                  </button>
                )}
              </div>
            </div>

            {mode === 'judge' ? (
              <>
                <div className="grid grid-cols-2 gap-3 mt-4">
                  <div>
                    <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Judge</div>
                    <input
                      value={judgeName}
                      onChange={(e) => setJudgeName(e.target.value)}
                      placeholder="Hon’ble Justice …"
                      className="mt-1 w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                    />
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Court</div>
                    <select
                      value={court}
                      onChange={(e) => setCourt(e.target.value as CourtValue)}
                      aria-label="Court"
                      className="mt-1 w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                    >
                      <option value="supreme_court">Supreme Court</option>
                      <option value="high_court">High Court</option>
                      <option value="district_court">District Court</option>
                      <option value="tribunal">Tribunal</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                </div>

                <div className="mt-3">
                  <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Case Type (optional)</div>
                  <input
                    value={caseType}
                    onChange={(e) => setCaseType(e.target.value)}
                    placeholder="Bail / Writ / IP / Service / …"
                    className="mt-1 w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  />
                </div>

                {error && <div className="mt-3 bg-rose-950/40 border border-rose-900/50 rounded-lg p-3 text-xs text-rose-200">{error}</div>}
              </>
            ) : (
              <>
                <div className="mt-4">
                  <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Case Summary</div>
                  <input
                    value={caseSummary}
                    onChange={(e) => setCaseSummary(e.target.value)}
                    placeholder="e.g., Bail application in State v. …"
                    className="mt-1 w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  />
                </div>

                <div className="mt-3">
                  <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Your Arguments</div>
                  <textarea
                    value={argumentsText}
                    onChange={(e) => setArgumentsText(e.target.value)}
                    spellCheck={false}
                    placeholder="Paste your draft arguments / key points here…"
                    className="mt-1 w-full h-[140px] resize-none glass-input rounded-xl px-4 py-3 text-xs text-slate-200 leading-relaxed outline-none"
                    aria-label="Arguments"
                  />
                </div>

                <div className="mt-3">
                  <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Citations (optional)</div>
                  <textarea
                    value={citationsRaw}
                    onChange={(e) => setCitationsRaw(e.target.value)}
                    spellCheck={false}
                    placeholder="One citation per line (optional)"
                    className="mt-1 w-full h-[90px] resize-none glass-input rounded-xl px-4 py-3 text-xs text-slate-200 leading-relaxed outline-none"
                    aria-label="Citations"
                  />
                </div>

                {devilError && <div className="mt-3 bg-rose-950/40 border border-rose-900/50 rounded-lg p-3 text-xs text-rose-200">{devilError}</div>}
              </>
            )}
          </div>

          <div className="flex-1 p-4">
            {mode === 'judge' ? (
              <>
                <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase mb-2">Judgment Excerpts</div>
                <textarea
                  value={excerpts}
                  onChange={(e) => setExcerpts(e.target.value)}
                  spellCheck={false}
                  placeholder="Paste excerpts here.\n\nTip: Separate multiple excerpts with:\n---"
                  className="w-full h-[320px] lg:h-[calc(100vh-310px)] resize-none glass-input rounded-xl px-4 py-3 text-xs text-slate-200 leading-relaxed outline-none"
                />
              </>
            ) : (
              <div className="text-xs text-slate-500 leading-relaxed">
                Tip: Keep the case summary short. Paste the arguments exactly as you plan to submit them.
              </div>
            )}
          </div>
        </div>

        <div className="w-full lg:flex-1 bg-black/20 backdrop-blur-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h4 className="text-sm font-bold text-white">Findings</h4>
              <div className="text-xs text-slate-500">
                {mode === 'judge'
                  ? 'Patterns + recommendations based only on provided excerpts'
                  : 'Opposing counsel simulation + what to prepare'}
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {mode === 'judge' ? (
              <>
                {!result && <div className="text-sm text-slate-500">Run Analyze to see results.</div>}

                {result && (
                  <>
                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="text-xs text-slate-400">Judge</div>
                      <div className="text-sm text-slate-200 font-bold mt-1">{result.judge_name}</div>
                      <div className="text-xs text-slate-500 mt-1">Cases analyzed: {result.total_cases_analyzed}</div>
                    </div>

                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase mb-2">Patterns</div>
                      {result.patterns?.length ? (
                        <div className="space-y-3">
                          {result.patterns.map((p, idx) => (
                            <div key={idx} className="border border-white/10 rounded-lg p-3 bg-white/5">
                              <div className="flex items-center justify-between gap-2">
                                <div className="text-xs text-slate-200 font-semibold">{p.pattern}</div>
                                <span className={`text-[10px] px-2 py-1 rounded-full border ${signalColor(p.signal)}`}>{p.signal.toUpperCase()}</span>
                              </div>
                              {!!p.evidence?.length && (
                                <div className="mt-2 text-xs text-slate-400 space-y-1">
                                  {p.evidence.slice(0, 4).map((e, i) => (
                                    <div key={i}>- {e}</div>
                                  ))}
                                </div>
                              )}
                              {!!p.caveats?.length && <div className="mt-2 text-[11px] text-slate-500">Limitations: {p.caveats[0]}</div>}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-slate-500">No patterns returned.</div>
                      )}
                    </div>

                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase mb-2">Recommendations</div>
                      {result.recommendations?.length ? (
                        <div className="text-xs text-slate-200 space-y-1">
                          {result.recommendations.map((r, idx) => (
                            <div key={idx}>- {r}</div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-slate-500">No recommendations returned.</div>
                      )}
                    </div>
                  </>
                )}
              </>
            ) : (
              <>
                {!devilResult && <div className="text-sm text-slate-500">Run Simulate to see attack points.</div>}

                {devilResult && (
                  <>
                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="text-xs text-slate-400">Vulnerability</div>
                      <div className="text-sm text-slate-200 font-bold mt-1">
                        {Number.isFinite(devilResult.vulnerability_score) ? `${devilResult.vulnerability_score.toFixed(1)}/10` : 'N/A'}
                      </div>
                      <div className="text-xs text-slate-500 mt-1">Higher means more angles for the opposition.</div>
                    </div>

                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase mb-2">Attack Points</div>
                      {devilResult.attack_points?.length ? (
                        <div className="space-y-3">
                          {devilResult.attack_points.slice(0, 12).map((p, idx) => (
                            <div key={idx} className="border border-white/10 rounded-lg p-3 bg-white/5">
                              <div className="text-xs text-slate-200 font-semibold">
                                {p.title || `Attack Point ${idx + 1}`}
                              </div>
                              {p.weakness && <div className="mt-2 text-xs text-slate-400">Weakness: <span className="text-slate-300">{p.weakness}</span></div>}
                              {p.counter_citation && <div className="mt-1 text-xs text-slate-400">Counter-citation: <span className="text-slate-300">{p.counter_citation}</span></div>}
                              {p.suggested_attack && <div className="mt-1 text-xs text-slate-400">Suggested attack: <span className="text-slate-300">{p.suggested_attack}</span></div>}
                              {!p.weakness && !p.counter_citation && !p.suggested_attack && p.raw && (
                                <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-300 leading-relaxed">{p.raw}</pre>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-slate-500">No attack points returned.</div>
                      )}
                    </div>

                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase mb-2">Preparation</div>
                      {devilResult.preparation_recommendations?.length ? (
                        <div className="text-xs text-slate-200 space-y-1">
                          {devilResult.preparation_recommendations.map((r, idx) => (
                            <div key={idx}>- {r}</div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-xs text-slate-500">No recommendations returned.</div>
                      )}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DetectiveWall(props: { onBack: () => void; activeCase?: CaseData | null }) {
  const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard');
  const [isToolsOpen, setIsToolsOpen] = useState(false);
  const [activeTool, setActiveTool] = useState<ToolId>(null);
  const [isRemoveMode, setIsRemoveMode] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [scale, setScale] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const dragPreviewRef = useRef<HTMLDivElement | null>(null);
  const transformLayerRef = useRef<HTMLDivElement | null>(null);

  const [toolbarPos, setToolbarPos] = useState<{ x: number; y: number }>(() => {
    try {
      const raw = localStorage.getItem('junior:canvasToolbarPos');
      if (!raw) return { x: 160, y: 24 };
      const parsed = JSON.parse(raw) as unknown;
      if (
        typeof parsed === 'object' &&
        parsed !== null &&
        'x' in parsed &&
        'y' in parsed &&
        typeof (parsed as { x: unknown }).x === 'number' &&
        typeof (parsed as { y: unknown }).y === 'number'
      ) {
        const x = (parsed as { x: number }).x;
        const y = (parsed as { y: number }).y;
        if (Number.isFinite(x) && Number.isFinite(y)) return { x, y };
      }
    } catch {
      // ignore
    }
    return { x: 160, y: 24 };
  });
  const toolbarPosRef = useRef(toolbarPos);
  const toolbarRef = useRef<HTMLDivElement | null>(null);
  const [isDraggingToolbar, setIsDraggingToolbar] = useState(false);
  const toolbarDragRef = useRef({ startClientX: 0, startClientY: 0, startX: 0, startY: 0 });
  const didDragToolbarRef = useRef(false);

  useEffect(() => {
    toolbarPosRef.current = toolbarPos;
    const el = toolbarRef.current;
    if (!el) return;
    el.style.left = `${toolbarPos.x}px`;
    el.style.top = `${toolbarPos.y}px`;
  }, [toolbarPos]);

  useEffect(() => {
    if (!isDraggingToolbar) return;

    const handleMove = (e: MouseEvent) => {
      const dx = e.clientX - toolbarDragRef.current.startClientX;
      const dy = e.clientY - toolbarDragRef.current.startClientY;
      if (!didDragToolbarRef.current && Math.abs(dx) + Math.abs(dy) > 3) {
        didDragToolbarRef.current = true;
      }
      setToolbarPos({ x: toolbarDragRef.current.startX + dx, y: toolbarDragRef.current.startY + dy });
    };

    const handleUp = () => {
      setIsDraggingToolbar(false);
      if (didDragToolbarRef.current) {
        try {
          localStorage.setItem('junior:canvasToolbarPos', JSON.stringify(toolbarPosRef.current));
        } catch {
          // ignore
        }
      }
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [isDraggingToolbar]);

  const [draggedResearchItem, setDraggedResearchItem] = useState<null | {
    item: ResearchItem;
    offset: { x: number; y: number };
  }>(null);
  const [dragPos, setDragPos] = useState({ x: 0, y: 0 });
  const [dragStartPos, setDragStartPos] = useState({ x: 0, y: 0 });

  const handleResearchDragStart = (e: React.MouseEvent<HTMLElement>, item: ResearchItem) => {
    e.preventDefault();
    e.stopPropagation();
    const rect = e.currentTarget.getBoundingClientRect();
    setDraggedResearchItem({ item, offset: { x: e.clientX - rect.left, y: e.clientY - rect.top } });
    setDragPos({ x: e.clientX, y: e.clientY });
    setDragStartPos({ x: e.clientX, y: e.clientY });
  };

  const [nodes, setNodes] = useState<NodeData[]>(() => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    const cx = w / 2;
    const cy = h / 2;
    const cardWidth = 320;
    const halfCard = cardWidth / 2;

    return [
      { id: 1, title: 'FIR No. 402/2023', type: 'Evidence', date: '12 Oct 2023', status: 'Verified', x: cx - halfCard, y: cy - 300, rotation: 0, pinColor: 'red', attachments: [] },
      { id: 2, title: 'Witness Statement (A)', type: 'Statement', date: '14 Oct 2023', status: 'Contested', x: cx - halfCard - 350, y: cy, rotation: -1, pinColor: 'blue', attachments: [] },
      { id: 3, title: 'CCTV Log (Exhibit B)', type: 'Evidence', date: '12 Oct 2023', status: 'Verified', x: cx - halfCard + 350, y: cy, rotation: 1, pinColor: 'green', attachments: [] },
      { id: 4, title: 'Alibi Defense Strategy', type: 'Strategy', date: 'Pending', status: 'Pending', x: cx - halfCard, y: cy + 300, rotation: 0, pinColor: 'yellow', attachments: [] },
    ];
  });

  // Start with no connections - they should only appear after "Analyze Wall"
  const [connections, setConnections] = useState<Connection[]>([]);

  // Clear any old cached connections on mount
  useEffect(() => {
    // This ensures we always start fresh with no connections
    setConnections([]);
  }, []);

  const caseId = props.activeCase?.id ? String(props.activeCase.id) : 'default';
  const caseTitle = props.activeCase?.title ?? 'Current Matter';
  const chatStorageKey = useMemo(() => `junior:chat:${caseId}`, [caseId]);
  const loadStoredMessages = useCallback(
    (key: string): ChatMessage[] | null => {
      try {
        const raw = localStorage.getItem(key);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed as ChatMessage[];
      } catch {
        // ignore malformed storage
      }
      return null;
    },
    []
  );

  const [wallIsAnalyzing, setWallIsAnalyzing] = useState(false);
  const [wallNodeSeverity, setWallNodeSeverity] = useState<Record<string, WallInsightSeverity | undefined>>({});
  const [wallAnalyzeStatus, setWallAnalyzeStatus] = useState<'idle' | 'ok' | 'llm_off' | 'backend_off'>('idle');

  const handleAnalyzeWall = async (overrides?: { nodes?: NodeData[]; connections?: Connection[]; silent?: boolean }) => {
    if (wallIsAnalyzing) return;
    setWallIsAnalyzing(true);

    const currentNodes = overrides?.nodes ?? nodes;
    const currentConnections = overrides?.connections ?? connections;

    const payload = {
      case_context: props.activeCase ? `${props.activeCase.title} (${props.activeCase.type})` : undefined,
      nodes: currentNodes.map((n) => ({
        id: String(n.id),
        title: n.title,
        type: n.type,
        status: n.status,
        date: n.date,
        content: undefined,
      })),
      edges: currentConnections.map((c) => ({ source: String(c.from), target: String(c.to), label: c.label })),
    };

    try {
      const res = await fetch('/api/v1/wall/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        if (res.status === 503) {
          setWallAnalyzeStatus('llm_off');
          if (!overrides?.silent) {
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: 'Detective Wall analysis is unavailable because the LLM is not configured. Set GROQ_API_KEY in your .env (see .env.example) and restart the backend.',
              },
            ]);
          }
          return;
        }
        setWallAnalyzeStatus('backend_off');
        throw new Error(`API error: ${res.status}`);
      }

      const data = (await res.json()) as WallAnalyzeResponse;
      setWallAnalyzeStatus('ok');

      // Build node severity map (keep highest severity per node)
      const rank: Record<WallInsightSeverity, number> = { low: 1, medium: 2, high: 3 };
      const nextSeverity: Record<string, WallInsightSeverity | undefined> = {};
      for (const insight of Array.isArray(data.insights) ? data.insights : []) {
        const sev = insight?.severity;
        if (sev !== 'low' && sev !== 'medium' && sev !== 'high') continue;
        const ids = Array.isArray(insight.node_ids) ? insight.node_ids : [];
        for (const id of ids) {
          const key = String(id);
          const prev = nextSeverity[key];
          if (!prev || rank[sev] > rank[prev]) nextSeverity[key] = sev;
        }
      }
      setWallNodeSeverity(nextSeverity);

      // Merge suggested links into connections (only if both endpoints exist on canvas)
      const nodeIds = new Set(currentNodes.map((n) => String(n.id)));
      const existing = new Set(currentConnections.map((c) => `${c.from}->${c.to}:${c.label}:${c.type}`));
      const toAdd: Connection[] = [];
      for (const link of Array.isArray(data.suggested_links) ? data.suggested_links : []) {
        const source = String(link?.source ?? '');
        const target = String(link?.target ?? '');
        const label = typeof link?.label === 'string' ? link.label : 'Suggested';
        const reason = typeof link?.reason === 'string' ? link.reason : undefined;
        const confidence = typeof link?.confidence === 'number' ? link.confidence : undefined;
        if (!nodeIds.has(source) || !nodeIds.has(target)) continue;
        const from = Number(source);
        const to = Number(target);
        if (!Number.isFinite(from) || !Number.isFinite(to)) continue;
        const key = `${from}->${to}:${label}:suggested`;
        if (existing.has(key)) continue;
        toAdd.push({ from, to, label, type: 'suggested', reason, confidence });
      }
      if (toAdd.length) {
        setConnections((prev) => [...prev, ...toAdd]);
      }

      // Post summary + next actions to chat (uses existing UX)
      const nextActions = Array.isArray(data.next_actions) ? data.next_actions : [];
      const content = [
        data.summary ? `Detective Wall Summary:\n${data.summary}` : 'Detective Wall Summary: (no summary returned)',
        nextActions.length ? `\nNext actions:\n${nextActions.map((a) => `- ${a}`).join('\n')}` : '',
      ]
        .filter(Boolean)
        .join('\n');

      if (!overrides?.silent) {
        setMessages((prev) => [...prev, { role: 'assistant', content }]);
      }
    } catch {
      setWallAnalyzeStatus('backend_off');
      if (!overrides?.silent) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: "Detective Wall analysis couldn't reach the backend. Make sure the FastAPI server is running, then try again.",
          },
        ]);
      }
    } finally {
      setWallIsAnalyzing(false);
    }
  };

  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  const handleUploadClick = () => {
    uploadInputRef.current?.click();
  };

  const handleUploadFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const now = Date.now();
    const w = window.innerWidth;
    const h = window.innerHeight;
    const cx = w / 2;
    const cy = h / 2;

    const created: NodeData[] = Array.from(files).map((f, idx) => ({
      id: now + idx,
      title: f.name,
      type: 'Evidence',
      date: new Date().toLocaleDateString(),
      status: 'Pending',
      x: cx - 160 + (idx % 3) * 36,
      y: cy - 50 + Math.floor(idx / 3) * 36,
      rotation: Math.random() * 6 - 3,
      pinColor: 'yellow',
      source: 'Upload',
      attachments: [{ name: f.name, kind: 'document', sizeBytes: f.size }],
    }));

    let nextNodes: NodeData[] = [];
    setNodes((prev) => {
      nextNodes = [...prev, ...created];
      return nextNodes;
    });
  };

  const defaultWelcome = useMemo<ChatMessage[]>(
    () => [
      {
        role: 'assistant',
        content: `Welcome to ${caseTitle}. I can read your wall, spot conflicts, and draft next steps. If you add evidence, I'll cross-check timelines and witnesses.`,
      },
    ],
    [caseTitle]
  );

  const [messages, setMessages] = useState<ChatMessage[]>(() => loadStoredMessages(chatStorageKey) ?? defaultWelcome);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [suggestActions, setSuggestActions] = useState(true);
  const [chatLanguage, setChatLanguage] = useState<ChatLanguage>('en');
  const [chatOutputScript, setChatOutputScript] = useState<OutputScript>('native');
  const renderLegalTerms = useLegalTermRenderer();

  useEffect(() => {
    setMessages(loadStoredMessages(chatStorageKey) ?? defaultWelcome);
    setChatSessionId(null);
  }, [chatStorageKey, defaultWelcome, loadStoredMessages]);

  useEffect(() => {
    try {
      localStorage.setItem(chatStorageKey, JSON.stringify(messages.slice(-50)));
    } catch {
      // ignore storage errors
    }
  }, [messages, chatStorageKey]);

  useEffect(() => {
    if (!draggedResearchItem) return;

    const handleMouseMove = (e: MouseEvent) => {
      setDragPos({ x: e.clientX, y: e.clientY });
    };

    const handleMouseUp = (e: MouseEvent) => {
      const dist = Math.sqrt(Math.pow(e.clientX - dragStartPos.x, 2) + Math.pow(e.clientY - dragStartPos.y, 2));
      if (dist > 50 && canvasRef.current) {
        const canvasRect = canvasRef.current.getBoundingClientRect();
        const x = (e.clientX - canvasRect.left - pan.x) / scale;
        const y = (e.clientY - canvasRect.top - pan.y) / scale;
        const newNode: NodeData = {
          id: Date.now(),
          title: draggedResearchItem.item.title,
          type: draggedResearchItem.item.type === 'Precedent' ? 'Precedent' : 'Evidence',
          date: new Date().toLocaleDateString(),
          status: 'Verified',
          x: x - 160,
          y: y - 80,
          rotation: Math.random() * 6 - 3,
          pinColor: 'blue',
          source: draggedResearchItem.item.source,
          attachments: [{ name: draggedResearchItem.item.title, kind: 'document', url: draggedResearchItem.item.url }],
        };

        let nextNodes: NodeData[] = [];
        setNodes((prev) => {
          nextNodes = [...prev, newNode];
          return nextNodes;
        });
      }
      setDraggedResearchItem(null);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [draggedResearchItem, pan, scale, dragStartPos]);

  useEffect(() => {
    const el = dragPreviewRef.current;
    if (!el || !draggedResearchItem) return;
    el.style.left = `${dragPos.x}px`;
    el.style.top = `${dragPos.y}px`;
  }, [dragPos.x, dragPos.y, draggedResearchItem]);

  useEffect(() => {
    const el = transformLayerRef.current;
    if (!el) return;
    el.style.transform = `translate(${pan.x}px, ${pan.y}px) scale(${scale})`;
  }, [pan.x, pan.y, scale]);

  useEffect(() => {
    setIsToolsOpen(false);
    setActiveTool(null);
    setIsRemoveMode(false);
  }, [activeTab]);

  const handleNodeDrag = useCallback((id: number, newPos: { x: number; y: number }) => {
    setNodes((prev) => prev.map((node) => (node.id === id ? { ...node, x: newPos.x, y: newPos.y } : node)));
  }, []);

  const handleNodeDelete = useCallback((id: number) => {
    setNodes((prev) => prev.filter((node) => node.id !== id));
    setSelectedNode((prev) => {
      if (prev === id) {
        setIsDetailsOpen(false);
        return null;
      }
      return prev;
    });
  }, []);

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (isRemoveMode) return;

    const target = e.target as HTMLElement | null;
    if (target === canvasRef.current || target?.classList.contains('container-bg') || target?.classList.contains('transform-layer')) {
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      setSelectedNode(null);
      setIsDetailsOpen(false);
    }
  };

  useEffect(() => {
    if (!isPanning) return;
    const handleMouseMove = (e: MouseEvent) => {
      setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
    };
    const handleMouseUp = () => {
      setIsPanning(false);
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isPanning, panStart]);

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale((prev) => Math.min(2, Math.max(0.3, prev + delta)));
  };

  const handleSendMessage = async (message: string) => {
    setMessages((prev) => [...prev, { role: 'user', content: message }]);
    setIsLoading(true);
    
    // Add a placeholder for assistant message that we'll stream into
    const assistantMsgIndex = messages.length + 1;
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);
    
    try {
      const payload: Record<string, unknown> = {
        message,
        language: chatLanguage,
        input_language: chatLanguage === 'en' ? null : chatLanguage,
        output_script: chatLanguage === 'en' ? null : chatOutputScript,
      };
      if (chatSessionId) payload.session_id = chatSessionId;

      // Use streaming endpoint for ChatGPT-like experience
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (!reader) {
        throw new Error('No response body');
      }

      let fullResponse = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'session' && data.session_id) {
                setChatSessionId(data.session_id);
              } else if (data.type === 'chunk' && data.content) {
                fullResponse += data.content;
                // Update the assistant message with streaming content
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[assistantMsgIndex] = {
                    role: 'assistant',
                    content: fullResponse,
                    preservedTerms: newMessages[assistantMsgIndex]?.preservedTerms,
                  };
                  return newMessages;
                });
              } else if (data.type === 'meta' && Array.isArray(data.preserved_terms)) {
                const preserved = data.preserved_terms.filter((t: unknown) => typeof t === 'string') as string[];
                setMessages((prev) => {
                  const newMessages = [...prev];
                  const existing = newMessages[assistantMsgIndex];
                  newMessages[assistantMsgIndex] = {
                    ...(existing ?? { role: 'assistant', content: fullResponse }),
                    preservedTerms: preserved,
                  };
                  return newMessages;
                });
              } else if (data.type === 'error') {
                throw new Error(data.error || 'Unknown error');
              }
            } catch (e) {
              // Ignore JSON parse errors for incomplete chunks
              if (e instanceof Error && !e.message.includes('Unexpected')) {
                throw e;
              }
            }
          }
        }
      }
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setMessages((prev) => {
        const newMessages = [...prev];
        newMessages[assistantMsgIndex] = {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${errorMessage}\n\nPlease try again.`
        };
        return newMessages;
      });
    }
    setIsLoading(false);
  };

  const getNodePosition = (id: number) => {
    const node = nodes.find((n) => n.id === id);
    return node ? { x: node.x, y: node.y } : { x: 0, y: 0 };
  };

  if (activeTab === 'strategy') {
    return (
      <div className="flex min-h-screen w-full text-legal-text font-sans overflow-hidden relative bg-legal-bg">
        <RadialMenu activeTab={activeTab} setActiveTab={setActiveTab} onBack={props.onBack} />
        <StrategyAnalytics activeCase={props.activeCase} />
      </div>
    );
  }

  if (activeTab === 'drafting') {
    return (
      <div className="flex min-h-screen w-full text-legal-text font-sans overflow-hidden relative bg-legal-bg">
        <RadialMenu activeTab={activeTab} setActiveTab={setActiveTab} onBack={props.onBack} />
        <DraftingStudio />
      </div>
    );
  }

  return (
    <div className={`flex min-h-screen w-full text-legal-text font-sans overflow-hidden relative bg-legal-bg ${isRemoveMode ? 'cursor-crosshair' : ''}`}>
      <div className="absolute inset-0 container-bg z-0"></div>
      
      <RadialMenu activeTab={activeTab} setActiveTab={setActiveTab} onBack={props.onBack} />

      <div className="flex-1 relative flex flex-col h-screen overflow-hidden">

        <ResearchPanel isOpen={isToolsOpen && activeTool === 'research'} onClose={() => setActiveTool(null)} onDragStart={handleResearchDragStart} />
        <VaultPanel isOpen={isToolsOpen && activeTool === 'vault'} onClose={() => setActiveTool(null)} onDragStart={handleResearchDragStart} />

        {draggedResearchItem && (
          <div
            ref={dragPreviewRef}
            className="fixed z-[100] pointer-events-none w-64 bg-legal-surface/90 backdrop-blur-xl border border-legal-gold/50 rounded-xl p-3 shadow-2xl transform -translate-x-1/2 -translate-y-1/2"
          >
            <h4 className="text-xs font-bold text-legal-text mb-1">{draggedResearchItem.item.title}</h4>
            <div className="flex items-center gap-1 text-[10px] text-legal-gold font-mono">
              <Plus size={10} />
              <span>ADD TO CANVAS</span>
            </div>
          </div>
        )}

        {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex */}
        <div
          ref={canvasRef}
          className={`flex-1 relative overflow-hidden select-none ${isRemoveMode ? 'cursor-crosshair' : isPanning ? 'cursor-grabbing' : 'cursor-grab'}`}
          onMouseDown={handleCanvasMouseDown}
          onWheel={handleWheel}
          role="application"
          aria-label="Detective wall canvas"
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              setIsRemoveMode(false);
            }
          }}
        >
          <div ref={toolbarRef} className="absolute z-30">
            {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
            <div
              className={`flex items-center justify-between glass-panel rounded-full px-6 py-3 shadow-glow max-w-md transition-all duration-300 hover:shadow-xl border border-white/10 ${
                isDraggingToolbar ? 'cursor-grabbing' : 'cursor-grab'
              }`}
              onMouseDown={(e) => {
                if (e.button !== 0) return;
                const target = e.target as HTMLElement | null;
                if (target?.closest('button')) return;

                e.preventDefault();
                didDragToolbarRef.current = false;
                toolbarDragRef.current = {
                  startClientX: e.clientX,
                  startClientY: e.clientY,
                  startX: toolbarPosRef.current.x,
                  startY: toolbarPosRef.current.y,
                };
                setIsDraggingToolbar(true);
              }}
            >
              <button
                className="text-rose-400 hover:text-rose-300 mx-2 transition-transform duration-200 ease-in-out hover:scale-110 focus:outline-none focus:ring-2 focus:ring-rose-500 rounded-full"
                title="Upload"
                aria-label="Upload"
                onClick={handleUploadClick}
              >
                <Upload size={20} />
              </button>

              <input
                ref={uploadInputRef}
                type="file"
                className="hidden"
                multiple
                aria-label="Upload files"
                onChange={(e) => {
                  handleUploadFiles(e.currentTarget.files);
                  e.currentTarget.value = '';
                }}
              />
              <button
                className="text-slate-400 hover:text-white mx-2 transition-all duration-200 ease-in-out hover:rotate-12 focus:outline-none focus:ring-2 focus:ring-slate-400 rounded-full"
                onClick={() => setScale((s) => Math.max(0.3, s - 0.2))}
                title="Zoom Out"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 12H4"></path>
                </svg>
              </button>
              <button
                className="text-slate-400 hover:text-white mx-2 transition-all duration-200 ease-in-out hover:bg-white/5 hover:shadow-md rounded-full p-1 focus:outline-none focus:ring-2 focus:ring-slate-400"
                onClick={() => setScale((s) => Math.min(2, s + 0.2))}
                title="Zoom In"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                </svg>
              </button>
              <button
                className="text-slate-400 hover:text-white mx-2 transition-transform duration-200 ease-in-out hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-slate-400 rounded-full"
                onClick={() => {
                  setPan({ x: 0, y: 0 });
                  setScale(1);
                }}
                title="Reset View"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"
                  ></path>
                </svg>
              </button>
              <button
                onClick={() => void handleAnalyzeWall()}
                className={`mx-2 transition-all duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-slate-400 rounded-full ${
                  wallIsAnalyzing ? 'text-legal-gold opacity-80 cursor-wait' : 'text-slate-400 hover:text-legal-gold hover:scale-110'
                }`}
                title="Analyze Wall"
                aria-label="Analyze Wall"
              >
                <Sparkles size={22} />
              </button>
              <button
                onClick={() => setIsToolsOpen(!isToolsOpen)}
                className={`mx-2 transition-all duration-200 ease-in-out hover:rotate-180 focus:outline-none focus:ring-2 focus:ring-slate-400 rounded-full ${
                  isToolsOpen ? 'text-legal-gold' : 'text-slate-400 hover:text-white'
                }`}
                title="Tools"
                aria-label="Tools"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                  ></path>
                </svg>
              </button>
            </div>
            <ToolsDock
              isOpen={isToolsOpen}
              activeTool={activeTool}
              setActiveTool={setActiveTool}
              onToggleRemove={() => {
                setIsRemoveMode(!isRemoveMode);
                setActiveTool('remove');
              }}
              isRemoveMode={isRemoveMode}
            />
          </div>

          <div className="absolute bottom-6 left-6 z-30 glass-panel border border-white/10 rounded-lg px-4 py-2 shadow-xl">
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <span>
                <strong className="text-slate-300">{nodes.length}</strong> Documents
              </span>
              <span className="w-px h-4 bg-white/10"></span>
              <span className="text-rose-400">
                <strong>{connections.filter((c) => c.type === 'conflict').length}</strong> Conflicts
              </span>
              <span className="w-px h-4 bg-white/10"></span>
              <span className="text-legal-gold">
                <strong>{connections.filter((c) => c.type === 'suggested').length}</strong> Suggested
              </span>
            </div>
            {wallAnalyzeStatus === 'llm_off' && (
              <div className="mt-1 text-[11px] text-legal-gold">
                Link suggestions are off (set <span className="font-mono">GROQ_API_KEY</span> and restart backend).
              </div>
            )}
            {wallAnalyzeStatus === 'backend_off' && (
              <div className="mt-1 text-[11px] text-rose-300">Wall analysis backend is unreachable.</div>
            )}
          </div>

          <div
            ref={transformLayerRef}
            className={`transform-layer absolute inset-0 origin-center ${
              isPanning ? 'transition-none' : 'transition-transform duration-75'
            }`}
          >
            {connections.map((conn, idx) => (
              <ConnectionLine
                key={idx}
                start={getNodePosition(conn.from)}
                end={getNodePosition(conn.to)}
                label={conn.label}
                type={conn.type}
                reason={conn.reason}
              />
            ))}
            {nodes.map((node) => (
              <DocumentNode
                key={node.id}
                {...node}
                scale={scale}
                onDrag={handleNodeDrag}
                onDelete={handleNodeDelete}
                isSelected={selectedNode === node.id}
                onSelect={(id) => {
                  setSelectedNode(id);
                  if (id !== null) {
                    setIsChatOpen(false);
                    setIsDetailsOpen(true);
                  }
                }}
                isRemoveMode={isRemoveMode}
                insightSeverity={wallNodeSeverity[String(node.id)]}
              />
            ))}
          </div>
        </div>

        {!isChatOpen && (
          <button
            type="button"
            className="absolute bottom-8 right-8 z-30"
            onClick={() => {
              setIsDetailsOpen(false);
              setIsChatOpen(true);
            }}
            aria-label="Open chat"
          >
            <div className="ai-orb">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <div className="absolute inset-0 flex items-center justify-center z-10">
                <MessageSquare size={28} className="text-white drop-shadow-md" />
              </div>
            </div>
          </button>
        )}

        <ChatPanel
          isOpen={isChatOpen}
          toggleChat={() => {
            setIsDetailsOpen(false);
            setIsChatOpen(!isChatOpen);
          }}
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          suggestActions={suggestActions}
          onToggleSuggestActions={() => setSuggestActions((v) => !v)}
          caseTitle={caseTitle}
          language={chatLanguage}
          outputScript={chatOutputScript}
          onChangeLanguage={(lang) => setChatLanguage(lang)}
          onChangeOutputScript={(s) => setChatOutputScript(s)}
          renderMessageContent={renderLegalTerms}
        />

        {selectedNode !== null && (
          <NodeDetailsPanel
            isOpen={isDetailsOpen}
            onClose={() => setIsDetailsOpen(false)}
            node={nodes.find((n) => n.id === selectedNode) ?? nodes[0]}
            connections={connections}
            nodes={nodes}
          />
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState<View>('landing');
  const [activeCase, setActiveCase] = useState<CaseData | null>(() => {
    const saved = localStorage.getItem('jr_activeCase');
    return saved ? (JSON.parse(saved) as CaseData) : null;
  });

  useEffect(() => {
    if (activeCase) localStorage.setItem('jr_activeCase', JSON.stringify(activeCase));
    else localStorage.removeItem('jr_activeCase');
  }, [activeCase]);

  const handleEnter = () => setView('selection');

  const handleSelectCase = (caseData: CaseData) => {
    setActiveCase(caseData);
    setView('wall');
  };

  const handleNewCase = () => {
    setActiveCase({
      id: Date.now(),
      title: 'New Case',
      type: 'General',
      date: new Date().toLocaleDateString(),
      status: 'Active',
    });
    setView('wall');
  };

  const handleBack = () => setView('selection');

  return (
    <>
      {view === 'landing' && <LandingPage onEnter={handleEnter} />}
      {view === 'selection' && <CaseSelection onSelectCase={handleSelectCase} onNewCase={handleNewCase} />}
      {view === 'wall' && <DetectiveWall onBack={handleBack} activeCase={activeCase} />}
    </>
  );
}
