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
import { AuthPage } from './views/AuthPage';
import {
  AlertTriangle,
  ChevronRight,
  ExternalLink,
  Gavel,
  Loader2,
  MessageSquare,
  Eye,
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

type ChatLanguage = 'en' | 'hi' | 'mr' | 'hi-latn';
type OutputScript = 'native' | 'roman';

type DraftQualityIssue = {
  code: string;
  severity: 'low' | 'medium' | 'high' | string;
  message: string;
  recommendation: string;
};

type DraftQualityResponse = {
  score: number;
  confidence: string;
  issues: DraftQualityIssue[];
  checklist: Record<string, boolean>;
  ai_disclaimer?: string;
};

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
  const [qualityCheck, setQualityCheck] = useState<DraftQualityResponse | null>(null);
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
    // Document Structure
    { id: 'jurisdiction', label: 'Jurisdiction', category: 'Structure', description: 'Add jurisdiction clause', insert: 'JURISDICTION\n\nThat this Hon\'ble Court has jurisdiction to entertain the present petition because…\n' },
    { id: 'facts', label: 'Facts', category: 'Structure', description: 'Statement of facts', insert: 'FACTS\n\n1. That…\n2. That…\n' },
    { id: 'grounds', label: 'Grounds', category: 'Structure', description: 'Legal grounds for petition', insert: 'GROUNDS\n\nA. Because…\nB. Because…\n' },
    { id: 'prayer', label: 'Prayer Clause', category: 'Structure', description: 'Prayer for relief', insert: 'PRAYER\n\nIt is, therefore, most respectfully prayed that this Hon\'ble Court may be pleased to…\n' },
    { id: 'verification', label: 'Verification', category: 'Legal', description: 'Verification statement', insert: 'VERIFICATION\n\nVerified at ______ on this ___ day of ______ that the contents of the above are true and correct…\n' },
    // Additional useful clauses
    { id: 'arguments', label: 'Arguments', category: 'Structure', description: 'Main legal arguments', insert: 'ARGUMENTS\n\nA. ARGUMENT 1\n\n1. That…\n2. That…\n\nB. ARGUMENT 2\n\n1. That…\n2. That…\n' },
    { id: 'reliefs', label: 'Reliefs Sought', category: 'Legal', description: 'List of reliefs', insert: 'RELIEFS SOUGHT\n\n(a) …\n(b) …\n(c) Any other relief this Hon\'ble Court deems fit.\n' },
    { id: 'affidavit', label: 'Affidavit', category: 'Legal', description: 'Affidavit format', insert: 'AFFIDAVIT\n\nI, ______, S/o ______, R/o ______, do hereby solemnly affirm and state as follows:\n\n1. That…\n2. That…\n' },
    { id: 'synopsis', label: 'Synopsis', category: 'Structure', description: 'Case synopsis', insert: 'SYNOPSIS\n\nBrief overview of the case:\n- Nature of dispute\n- Key facts\n- Legal issues\n- Relief sought\n' },
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

  const handleQualityCheck = async () => {
    setError(null);
    setIsWorking(true);
    try {
      const res = await fetch('/api/v1/format/quality-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(makeRequestBody()),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || 'Quality check failed');
      }
      const data = (await res.json()) as DraftQualityResponse;
      setQualityCheck(data);
    } catch {
      setError('Could not run draft quality check.');
      setQualityCheck(null);
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
                  onClick={handleQualityCheck}
                  disabled={isWorking || !content.trim()}
                  className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 text-xs font-bold tracking-wider disabled:opacity-50 transition-colors"
                >
                  QUALITY CHECK
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

            <div className="mt-3 flex items-center justify-between gap-3 flex-wrap">
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-white/10 text-slate-300 bg-white/5 backdrop-blur-sm">
                  <span className="text-[9px] font-mono">{wordCount}</span>
                  <span className="text-[9px] text-slate-500">words</span>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-white/10 text-slate-300 bg-white/5 backdrop-blur-sm">
                  <span className="text-[9px] font-mono">{charCount}</span>
                  <span className="text-[9px] text-slate-500">chars</span>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-white/10 text-slate-300 bg-white/5 backdrop-blur-sm">
                  <span className="text-[9px] font-mono">{lineCount}</span>
                  <span className="text-[9px] text-slate-500">lines</span>
                </div>
                <div className="w-px h-4 bg-white/10"></div>
                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-emerald-500/30 text-emerald-200 bg-emerald-500/10 backdrop-blur-sm">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></div>
                  <span className="text-[9px] font-mono font-bold">{citeGood}</span>
                  <span className="text-[9px]">good</span>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-amber-500/30 text-amber-200 bg-amber-500/10 backdrop-blur-sm">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-400"></div>
                  <span className="text-[9px] font-mono font-bold">{citeWarn}</span>
                  <span className="text-[9px]">caution</span>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-rose-500/30 text-rose-200 bg-rose-500/10 backdrop-blur-sm">
                  <div className="w-1.5 h-1.5 rounded-full bg-rose-400"></div>
                  <span className="text-[9px] font-mono font-bold">{citeBad}</span>
                  <span className="text-[9px]">bad</span>
                </div>
              </div>

              <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
                {saveState === 'saving' && (
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></div>
                    <span>Saving…</span>
                  </div>
                )}
                {saveState === 'saved' && lastSavedAt && (
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
                    <span>Saved {new Date(lastSavedAt).toLocaleTimeString()}</span>
                  </div>
                )}
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

            {qualityCheck && (
              <div className="mt-3 bg-black/30 border border-white/10 rounded-lg p-3 text-xs text-slate-200">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold">Draft Quality Score: {qualityCheck.score}/100</div>
                  <div className="text-[10px] text-slate-400 uppercase tracking-wide">Confidence: {qualityCheck.confidence}</div>
                </div>
                {qualityCheck.ai_disclaimer && (
                  <div className="mt-1 text-[10px] text-slate-400">{qualityCheck.ai_disclaimer}</div>
                )}
                {qualityCheck.issues?.length ? (
                  <div className="mt-2 space-y-2 max-h-28 overflow-auto findings-scroll pr-1">
                    {qualityCheck.issues.slice(0, 6).map((issue, i) => (
                      <div key={`${issue.code}-${i}`} className="bg-white/5 border border-white/10 rounded-md p-2">
                        <div className="text-[11px] font-medium text-slate-100">
                          {issue.message}
                          <span className="ml-2 text-[10px] uppercase text-slate-400">{issue.severity}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{issue.recommendation}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-2 text-[11px] text-emerald-300">No major structural issues detected.</div>
                )}
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
                    <div className="absolute left-2 top-4 z-40 w-80 glass-panel border border-white/10 rounded-xl shadow-2xl overflow-hidden">
                      <div className="px-3 py-2 border-b border-white/10 flex items-center justify-between bg-gradient-to-r from-legal-gold/5 to-legal-gold/0">
                        <div className="flex items-center gap-2">
                          <Sparkles size={12} className="text-legal-gold" />
                          <span className="text-[10px] text-slate-400 font-mono">/{slashQuery || '…'}</span>
                        </div>
                        <span className="text-[9px] text-slate-500 tracking-wider uppercase">Quick Insert</span>
                      </div>
                      <div className="max-h-80 overflow-auto">
                        {(() => {
                          const categories = Array.from(new Set(filteredSlash.map(i => i.category || 'Other')));
                          return categories.map(category => {
                            const items = filteredSlash.filter(i => (i.category || 'Other') === category);
                            if (items.length === 0) return null;
                            return (
                              <div key={category}>
                                <div className="px-3 py-1.5 text-[9px] text-slate-500 font-bold tracking-wider uppercase bg-black/20">
                                  {category}
                                </div>
                                {items.map((item) => (
                                  <button
                                    key={item.id}
                                    onClick={() => {
                                      insertAtCursor(item.insert);
                                      setSlashOpen(false);
                                      setSlashQuery('');
                                    }}
                                    aria-label={`Insert ${item.label}`}
                                    title={item.description || item.label}
                                    className="w-full text-left px-3 py-2 text-xs text-slate-200 hover:bg-white/5 transition-colors flex items-center justify-between group border-b border-white/5 last:border-0"
                                  >
                                    <div className="flex-1 min-w-0">
                                      <div className="font-medium">{item.label}</div>
                                      {item.description && (
                                        <div className="text-[10px] text-slate-500 mt-0.5 truncate">{item.description}</div>
                                      )}
                                    </div>
                                    <ChevronRight size={14} className="text-slate-600 group-hover:text-legal-gold transition-colors flex-shrink-0" />
                                  </button>
                                ))}
                              </div>
                            );
                          });
                        })()}
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
            <div className="flex items-center justify-between mb-3 pb-3 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="p-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    Live Preview
                    {previewHtml && <span className="text-[9px] text-emerald-400 font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">LIVE</span>}
                  </h4>
                  <div className="text-[10px] text-slate-500 mt-0.5">WYSIWYG court layout • Auto-updates</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleOpenPreview}
                  disabled={isWorking || !previewHtml}
                  title="Open in new tab"
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-200 text-[10px] font-bold tracking-wider disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  OPEN
                </button>
                <button
                  onClick={handleDownloadDoc}
                  disabled={isWorking || !previewHtml}
                  title="Download as .doc file"
                  className="px-3 py-1.5 rounded-lg bg-legal-gold/10 hover:bg-legal-gold/20 border border-legal-gold/30 text-legal-gold text-[10px] font-bold tracking-wider disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  DOWNLOAD
                </button>
              </div>
            </div>

            {!previewHtml && content.trim() && (
              <div className="mb-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/10 flex items-start gap-2">
                <div className="mt-0.5">
                  <svg className="w-4 h-4 text-blue-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="flex-1 text-[11px] text-slate-400">
                  <div className="font-medium text-blue-300 mb-1">Generating preview...</div>
                  <div>Your document is being formatted according to {court.replace('_', ' ')} rules.</div>
                </div>
              </div>
            )}

            {!previewHtml && !content.trim() && (
              <div className="mb-3 p-4 rounded-lg bg-white/5 border border-white/10 text-center">
                <svg className="w-10 h-10 text-slate-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div className="text-xs text-slate-500">Start drafting to see live preview</div>
              </div>
            )}

            <div className="rounded-xl overflow-hidden border border-white/10 shadow-2xl bg-gradient-to-br from-white/5 to-white/[0.02]">
              {previewHtml ? (
                <iframe 
                  title="Document Preview" 
                  className="w-full h-[420px] lg:h-[calc(100vh-200px)] bg-white" 
                  sandbox="allow-same-origin" 
                  srcDoc={previewHtml} 
                />
              ) : (
                <div className="h-[420px] lg:h-[calc(100vh-200px)] flex flex-col items-center justify-center text-slate-500">
                  <svg className="w-16 h-16 text-slate-700 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <div className="text-sm font-medium text-slate-600 mb-1">No Preview Available</div>
                  <div className="text-xs text-slate-500">Start typing to see formatted output</div>
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
  source_provenance?: Array<{
    title: string;
    citation: string;
    year?: number | null;
    court?: string;
    case_type?: string;
    legal_status?: string;
    source_url?: string;
    origin?: string;
    summary?: string;
    is_landmark?: boolean;
  }>;
};

type CaseTimelineItem = {
  id: string;
  date: string;
  event_type: string;
  title: string;
  description?: string;
  documents?: string[];
};

type CaseDetailsResponse = {
  id: string;
  case_number: string;
  title: string;
  court: string;
  status: string;
  filing_date: string;
  timeline: CaseTimelineItem[];
  subject_matter: string[];
  acts_sections: string[];
};

type ListedCaseDocument = {
  id: string;
  title: string;
  date?: string;
  summary?: string;
};

type CaseDocumentsResponse = {
  documents?: ListedCaseDocument[];
};

type SourcePreview = {
  title: string;
  content: string;
  full_text_length: number;
  error?: string | null;
  summary_ai?: string;
  key_points?: string[];
  quotes?: string[];
};

type SourceSearchItem = {
  id: string;
  title: string;
  url?: string;
};

function StrategyAnalytics(props: {
  activeCase?: CaseData | null;
  onAddCitationToWall?: (payload: { title: string; content: string; url?: string; citation: string }) => void;
}) {
  const [mode, setMode] = useState<AnalyticsMode>('judge');

  const [judgeName, setJudgeName] = useState('');
  const [court, setCourt] = useState<CourtValue>('high_court');
  const [caseType, setCaseType] = useState('');
  const [timePeriod, setTimePeriod] = useState('');
  const [casesCount, setCasesCount] = useState('');
  const [caseDetails, setCaseDetails] = useState('');
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JudgeAnalyticsResponse | null>(null);

  const [caseSummary, setCaseSummary] = useState('');
  const [argumentsText, setArgumentsText] = useState('');
  const [citationsRaw, setCitationsRaw] = useState('');
  const [devilWorking, setDevilWorking] = useState(false);
  const [devilError, setDevilError] = useState<string | null>(null);
  const [devilResult, setDevilResult] = useState<DevilsAdvocateResponse | null>(null);
  const [isAutoFillingDevil, setIsAutoFillingDevil] = useState(false);
  const [devilSaveStatus, setDevilSaveStatus] = useState<string | null>(null);
  const [devilUsedFallback, setDevilUsedFallback] = useState(false);
  const [responseDraft, setResponseDraft] = useState<string | null>(null);
  const [selectedCitationPreview, setSelectedCitationPreview] = useState<null | {
    citation: string;
    title: string;
    url: string;
  }>(null);
  const [citationPreviewState, setCitationPreviewState] = useState<
    | { status: 'idle' }
    | { status: 'loading'; url: string }
    | { status: 'ok'; url: string; data: SourcePreview }
    | { status: 'error'; url: string; message: string }
  >({ status: 'idle' });
  const citationPreviewCacheRef = useRef<Map<string, { kind: 'ok'; data: SourcePreview } | { kind: 'error'; message: string }>>(
    new Map()
  );

  useEffect(() => {
    if (caseSummary.trim()) return;
    if (props.activeCase?.title) {
      setCaseSummary(props.activeCase.title);
    }
  }, [props.activeCase?.title, caseSummary]);

  const splitCitations = (raw: string) =>
    raw
      .split(/\n+/g)
      .map((s) => s.trim())
      .filter(Boolean);

  const buildFallbackDevilsAdvocate = (): DevilsAdvocateResponse => {
    const text = argumentsText.toLowerCase();
    const points: DevilsAdvocateResponse['attack_points'] = [];

    const hasEvidenceSignal = /(evidence|document|annexure|exhibit|record|proof)/.test(text);
    const hasReliefSignal = /(relief|prayer|seeking|requested)/.test(text);
    const hasJurisdictionSignal = /(jurisdiction|maintainab|territorial|pecuniary)/.test(text);
    const hasTimelineSignal = /(date|timeline|on\s+\d|chronology|sequence)/.test(text);

    if (!hasEvidenceSignal) {
      points.push({
        title: 'Evidentiary foundation may be challenged',
        weakness: 'Argument does not explicitly anchor each key claim to supporting documents or admissible evidence.',
        suggested_attack: 'Opposing counsel may argue that assertions are speculative and unsupported on record.',
      });
    }
    if (!hasReliefSignal) {
      points.push({
        title: 'Relief framing appears under-specified',
        weakness: 'Requested relief is not clearly scoped with legal basis and practical enforceability.',
        suggested_attack: 'Opposing counsel may submit that the prayer is vague or beyond jurisdictional competence.',
      });
    }
    if (!hasJurisdictionSignal) {
      points.push({
        title: 'Jurisdiction and maintainability vulnerability',
        weakness: 'No direct maintainability/jurisdiction position is articulated.',
        suggested_attack: 'Opposing counsel may seek early dismissal on maintainability or forum objections.',
      });
    }
    if (!hasTimelineSignal) {
      points.push({
        title: 'Chronology can be attacked for ambiguity',
        weakness: 'Argument lacks crisp date-wise sequence linking facts to legal consequences.',
        suggested_attack: 'Opposing counsel may exploit timeline gaps to cast doubt on causation and credibility.',
      });
    }

    if (points.length === 0) {
      points.push({
        title: 'Counter-precedent exposure check',
        weakness: 'Even strong submissions can be weakened if opposing side produces a fact-distinguishable higher-court precedent.',
        suggested_attack: 'Opposing counsel may concede facts but defeat your legal inference through nuanced precedent distinction.',
      });
    }

    const score = Math.min(8.5, 2.5 + points.length * 1.3);
    return {
      attack_points: points,
      vulnerability_score: Number(score.toFixed(1)),
      preparation_recommendations: [
        'Map every major assertion to one supporting document/exhibit in your written submissions.',
        'Add a dedicated maintainability/jurisdiction paragraph with authority and fallback position.',
        'Prepare short oral rebuttals for each identified attack point and keep one alternate precedent ready.',
      ],
    };
  };

  const formatDevilsResultForNote = (data: DevilsAdvocateResponse, fallbackUsed: boolean) => {
    const lines: string[] = [];
    lines.push(`Vulnerability Score: ${Number.isFinite(data.vulnerability_score) ? data.vulnerability_score.toFixed(1) : 'N/A'}/10`);
    lines.push(`Engine: ${fallbackUsed ? 'Fallback Checklist' : 'LLM Devil\'s Advocate'}`);
    lines.push('');
    lines.push('Attack Points:');
    if (data.attack_points?.length) {
      data.attack_points.forEach((p, idx) => {
        lines.push(`${idx + 1}. ${p.title || `Attack Point ${idx + 1}`}`);
        if (p.weakness) lines.push(`   - Weakness: ${p.weakness}`);
        if (p.counter_citation) lines.push(`   - Counter-citation: ${p.counter_citation}`);
        if (p.suggested_attack) lines.push(`   - Suggested attack: ${p.suggested_attack}`);
      });
    } else {
      lines.push('1. None');
    }
    lines.push('');
    lines.push('Preparation Recommendations:');
    if (data.preparation_recommendations?.length) {
      data.preparation_recommendations.forEach((r, idx) => lines.push(`${idx + 1}. ${r}`));
    } else {
      lines.push('1. None');
    }
    return lines.join('\n');
  };

  const persistDevilsResult = async (data: DevilsAdvocateResponse, fallbackUsed: boolean) => {
    if (!props.activeCase?.id) {
      setDevilSaveStatus('Result generated (no active case selected, so not saved).');
      return;
    }

    const note = formatDevilsResultForNote(data, fallbackUsed);
    try {
      const res = await fetch(`/api/v1/cases/${props.activeCase.id}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: "Devil's Advocate",
          tag: fallbackUsed ? 'devils_advocate_fallback' : 'devils_advocate',
          note,
        }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `Failed to save (${res.status})`);
      }
      setDevilSaveStatus('Saved to case notes.');
    } catch {
      setDevilSaveStatus('Generated successfully, but could not save to case notes.');
    }
  };

  const autoFillDevilsAdvocate = async () => {
    if (!props.activeCase?.id || !props.activeCase.caseNumber) return;

    setIsAutoFillingDevil(true);
    try {
      const [caseRes, docsRes] = await Promise.all([
        fetch(`/api/v1/cases/${props.activeCase.id}`),
        fetch(`/api/v1/documents/?case_number=${encodeURIComponent(props.activeCase.caseNumber)}&limit=20`),
      ]);

      if (!caseRes.ok || !docsRes.ok) {
        throw new Error('Autofill data unavailable');
      }

      const caseData = (await caseRes.json()) as CaseDetailsResponse;
      const docsData = (await docsRes.json()) as CaseDocumentsResponse;
      const timeline = Array.isArray(caseData.timeline) ? caseData.timeline : [];
      const documents = Array.isArray(docsData.documents) ? docsData.documents : [];

      const summary = `${caseData.title} (${caseData.case_number}) before ${caseData.court.replace(/_/g, ' ')}; current status: ${caseData.status}.`;
      setCaseSummary(summary);

      const argumentLines: string[] = [];
      if (timeline.length) {
        argumentLines.push('Case chronology and key events:');
        timeline.slice(0, 8).forEach((event, idx) => {
          argumentLines.push(
            `${idx + 1}. ${event.date}: ${event.title}${event.description ? ` - ${event.description}` : ''}`
          );
        });
        argumentLines.push('');
      }

      if (documents.length) {
        argumentLines.push('Key record-backed points from available documents:');
        documents.slice(0, 8).forEach((doc, idx) => {
          argumentLines.push(
            `${idx + 1}. ${doc.title}${doc.summary ? ` - ${doc.summary}` : ''}`
          );
        });
        argumentLines.push('');
      }

      if (Array.isArray(caseData.acts_sections) && caseData.acts_sections.length) {
        argumentLines.push(`Applicable provisions: ${caseData.acts_sections.slice(0, 6).join(', ')}`);
      }

      if (Array.isArray(caseData.subject_matter) && caseData.subject_matter.length) {
        argumentLines.push(`Subject focus: ${caseData.subject_matter.slice(0, 6).join(', ')}`);
      }

      setArgumentsText(argumentLines.join('\n').trim());

      const citationLines = documents
        .slice(0, 10)
        .map((doc) => `${doc.title}${doc.date ? ` (${doc.date})` : ''}`)
        .filter(Boolean);
      setCitationsRaw(citationLines.join('\n'));
    } catch {
      // Keep manual input path if autofill cannot load
    } finally {
      setIsAutoFillingDevil(false);
    }
  };

  useEffect(() => {
    if (mode !== 'devils') return;
    if (!props.activeCase?.id || !props.activeCase.caseNumber) return;
    if (caseSummary.trim() || argumentsText.trim() || citationsRaw.trim()) return;
    void autoFillDevilsAdvocate();
  }, [mode, props.activeCase?.id, props.activeCase?.caseNumber]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        if (mode === 'judge' && !isWorking) {
          void runAnalysis();
        } else if (mode === 'devils' && !devilWorking) {
          void runDevilsAdvocate();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mode, isWorking, devilWorking, judgeName, caseDetails, caseSummary, argumentsText]);

  const runAnalysis = async () => {
    setError(null);
    setResult(null);
    
    if (!judgeName.trim()) {
      setError('Enter a judge name.');
      return;
    }
    if (!caseType.trim()) {
      setError('Enter a case type (e.g., "Bail Applications", "IPC 376 Sexual Offenses").');
      return;
    }
    if (!caseDetails.trim()) {
      setError('Describe your case/application briefly.');
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
          case_type: caseType,
          judgments: [], // Empty array signals backend to auto-fetch
          case_details: caseDetails,
          time_period: timePeriod || null,
          cases_count: casesCount ? parseInt(casesCount) : 15,
        }),
      });

      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `API error: ${res.status}`);
      }

      const data = (await res.json()) as JudgeAnalyticsResponse;
      setResult(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Judge analytics is unavailable: ${message}`);
    } finally {
      setIsWorking(false);
    }
  };

  const runDevilsAdvocate = async () => {
    setDevilError(null);
    setDevilResult(null);
    setDevilUsedFallback(false);
    setDevilSaveStatus(null);

    if (!caseSummary.trim()) {
      setDevilError('Enter a case summary.');
      return;
    }
    if (!argumentsText.trim()) {
      setDevilError('Enter your arguments to stress-test.');
      return;
    }

    setDevilWorking(true);
    let allowFallback = false;
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
        allowFallback = res.status >= 500 || res.status === 503;
        throw new Error(detail || `API error: ${res.status}`);
      }

      const data = (await res.json()) as DevilsAdvocateResponse;
      setDevilResult(data);
      await persistDevilsResult(data, false);
    } catch (err) {
      // Strict fallback: only when backend/LLM is unavailable, not for normal validation issues.
      if (allowFallback || err instanceof TypeError || err instanceof SyntaxError) {
        const fallback = buildFallbackDevilsAdvocate();
        setDevilUsedFallback(true);
        setDevilResult(fallback);
        setDevilError("Live Devil's Advocate is unavailable, showing strict fallback checklist.");
        await persistDevilsResult(fallback, true);
      } else {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setDevilError(`Devil's Advocate failed: ${message}`);
      }
    } finally {
      setDevilWorking(false);
    }
  };

  const signalColor = (s: 'low' | 'medium' | 'high') => {
    if (s === 'high') return 'text-rose-200 border-rose-400/40 bg-rose-500/20 shadow-sm shadow-rose-500/20';
    if (s === 'medium') return 'text-amber-200 border-amber-400/40 bg-amber-500/20 shadow-sm shadow-amber-500/20';
    return 'text-emerald-200 border-emerald-400/40 bg-emerald-500/20 shadow-sm shadow-emerald-500/20';
  };

  const signalIcon = (s: 'low' | 'medium' | 'high') => {
    if (s === 'high') return '⚠️';
    if (s === 'medium') return '⚡';
    return '✓';
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      alert('Copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const buildResponseDraft = (attack: DevilsAdvocateResponse['attack_points'][number], index: number) => {
    return [
      `RESPONSE DRAFT - Attack ${index + 1}`,
      '',
      `Issue: ${attack.title || `Attack Point ${index + 1}`}`,
      '',
      `Opponent's likely attack: ${attack.suggested_attack || attack.weakness || 'To be articulated based on pleadings.'}`,
      '',
      'Proposed rebuttal:',
      '1. Facts on record:',
      '2. Applicable legal position:',
      '3. Distinguish adverse authority:',
      `4. Our supporting citation: ${attack.counter_citation || 'Insert controlling precedent'}`,
      '5. Relief and prayer alignment:',
    ].join('\n');
  };

  const extractFirstUrl = (input: string) => {
    const m = input.match(/https?:\/\/[^\s)\]]+/i);
    return m ? m[0] : null;
  };

  const resolveCitationUrl = async (citation: string): Promise<{ title: string; url: string } | null> => {
    const direct = extractFirstUrl(citation);
    if (direct) return { title: citation.slice(0, 120), url: direct };

    const res = await fetch('/api/v1/research/sources/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: citation, limit: 5 }),
    });
    if (!res.ok) return null;
    const data = await res.json() as { results?: SourceSearchItem[] };
    const first = (Array.isArray(data.results) ? data.results : []).find((r) => !!r.url);
    if (!first?.url) return null;
    return { title: first.title || citation.slice(0, 120), url: first.url };
  };

  const handleCounterCitationPreview = async (citation: string, attackTitle: string) => {
    const clean = citation.trim();
    if (!clean) {
      setDevilError('No counter-citation text available to preview.');
      return;
    }

    try {
      const resolved = await resolveCitationUrl(clean);
      if (!resolved?.url) {
        setDevilError('Could not resolve a previewable source URL for this citation.');
        return;
      }

      setSelectedCitationPreview({
        citation: clean,
        title: attackTitle || resolved.title,
        url: resolved.url,
      });

      const cached = citationPreviewCacheRef.current.get(resolved.url);
      if (cached?.kind === 'ok') {
        setCitationPreviewState({ status: 'ok', url: resolved.url, data: cached.data });
        return;
      }
      if (cached?.kind === 'error') {
        setCitationPreviewState({ status: 'error', url: resolved.url, message: cached.message });
        return;
      }

      setCitationPreviewState({ status: 'loading', url: resolved.url });
      const previewRes = await fetch('/api/v1/research/sources/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: resolved.url }),
      });
      if (!previewRes.ok) {
        const detail = await previewRes.text();
        throw new Error(detail || `Preview error: ${previewRes.status}`);
      }
      const preview = await previewRes.json() as SourcePreview;
      if (preview.error) {
        citationPreviewCacheRef.current.set(resolved.url, { kind: 'error', message: preview.error });
        setCitationPreviewState({ status: 'error', url: resolved.url, message: preview.error });
        return;
      }

      citationPreviewCacheRef.current.set(resolved.url, { kind: 'ok', data: preview });
      setCitationPreviewState({ status: 'ok', url: resolved.url, data: preview });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to preview citation source.';
      const url = selectedCitationPreview?.url || '';
      if (url) {
        citationPreviewCacheRef.current.set(url, { kind: 'error', message });
      }
      setCitationPreviewState({ status: 'error', url, message });
    }
  };

  const addCitationPreviewToWall = () => {
    if (!selectedCitationPreview) return;
    if (citationPreviewState.status !== 'ok' || citationPreviewState.url !== selectedCitationPreview.url) return;
    if (!props.onAddCitationToWall) {
      setDevilError('Add to wall is unavailable in this view.');
      return;
    }

    const preview = citationPreviewState.data;
    props.onAddCitationToWall({
      title: preview.title || selectedCitationPreview.title,
      content: preview.summary_ai || preview.content || selectedCitationPreview.citation,
      url: selectedCitationPreview.url,
      citation: selectedCitationPreview.citation,
    });
    setDevilSaveStatus('Citation added to wall as a precedent node.');
    setSelectedCitationPreview(null);
    setCitationPreviewState({ status: 'idle' });
  };

  const exportResults = () => {
    if (mode === 'judge' && result) {
      const text = `JUDGE ANALYTICS REPORT
======================

Judge: ${result.judge_name}
Cases Analyzed: ${result.total_cases_analyzed}

SOURCES USED:
${result.source_provenance?.length
  ? result.source_provenance.map((s, i) => `${i + 1}. ${s.title} | ${s.citation}${s.year ? ` (${s.year})` : ''}${s.origin ? ` | ${s.origin}` : ''}`).join('\n')
  : 'None'}

PATTERNS:
${result.patterns.map((p, i) => `
${i + 1}. ${p.pattern} [${p.signal.toUpperCase()}]
Evidence:
${p.evidence.map(e => `  - ${e}`).join('\n')}
${p.caveats.length ? `Limitations: ${p.caveats.join(', ')}` : ''}
`).join('\n')}

RECOMMENDATIONS:
${result.recommendations.map((r, i) => `${i + 1}. ${r}`).join('\n')}
`;
      copyToClipboard(text);
    } else if (mode === 'devils' && devilResult) {
      const text = `DEVIL'S ADVOCATE ANALYSIS
=========================

Vulnerability Score: ${devilResult.vulnerability_score}/10

ATTACK POINTS:
${devilResult.attack_points?.map((p, i) => `
${i + 1}. ${p.title || `Attack Point ${i + 1}`}
${p.weakness ? `Weakness: ${p.weakness}` : ''}
${p.counter_citation ? `Counter-citation: ${p.counter_citation}` : ''}
${p.suggested_attack ? `Suggested attack: ${p.suggested_attack}` : ''}
`).join('\n') || 'None'}

PREPARATION RECOMMENDATIONS:
${devilResult.preparation_recommendations?.map((r, i) => `${i + 1}. ${r}`).join('\n') || 'None'}
`;
      copyToClipboard(text);
    }
  };

  const clearForm = () => {
    if (mode === 'judge') {
      setJudgeName('');
      setCourt('high_court');
      setCaseType('');
      setTimePeriod('');
      setCasesCount('');
      setCaseDetails('');
      setResult(null);
      setError(null);
    } else {
      setCaseSummary('');
      setArgumentsText('');
      setCitationsRaw('');
      setDevilResult(null);
      setDevilError(null);
      setDevilSaveStatus(null);
      setDevilUsedFallback(false);
    }
  };

  return (
    <div className="flex-1 h-full min-h-0 relative overflow-hidden">
      <div className="absolute inset-0 container-bg z-0" />
      <div className="relative z-10 flex h-full min-h-0 flex-col lg:flex-row">
        <div className="w-full lg:w-1/2 min-w-0 lg:min-w-[520px] min-h-0 glass-panel border-b lg:border-b-0 lg:border-r border-white/10 flex flex-col">
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

                <div className="flex items-center gap-2">
                  {((mode === 'judge' && result) || (mode === 'devils' && devilResult)) && (
                    <>
                      <button
                        onClick={exportResults}
                        className="px-2 py-2 rounded-lg bg-slate-700/50 text-slate-300 text-xs hover:bg-slate-700 transition-colors"
                        title="Copy to clipboard"
                      >
                        📋
                      </button>
                      <button
                        onClick={clearForm}
                        className="px-2 py-2 rounded-lg bg-slate-700/50 text-slate-300 text-xs hover:bg-slate-700 transition-colors"
                        title="Clear form"
                      >
                        🗑️
                      </button>
                    </>
                  )}

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
            </div>

            {/* Keyboard Shortcut Hint */}
            <div className="px-4 py-2 bg-black/10 border-t border-white/5">
              <div className="text-[10px] text-slate-500 flex items-center gap-2">
                <span>💡 Tip:</span>
                <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-[9px]">Ctrl</kbd>
                <span>+</span>
                <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-[9px]">Enter</kbd>
                <span>to {mode === 'judge' ? 'Analyze' : 'Simulate'}</span>
              </div>
            </div>

            {mode === 'judge' ? (
              <>
                <div className="grid grid-cols-2 gap-3 mt-4 px-4">
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

                <div className="mt-3 px-4">
                  <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Case Type (optional)</div>
                  <input
                    value={caseType}
                    onChange={(e) => setCaseType(e.target.value)}
                    placeholder="Bail / Writ / IP / Service / …"
                    title="Optional: Specify case type for better analysis"
                    className="mt-1 w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 mt-3 px-4">
                  <div>
                    <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Time Period (optional)</div>
                    <input
                      value={timePeriod}
                      onChange={(e) => setTimePeriod(e.target.value)}
                      placeholder="2022-2024"
                      title="Optional: Time period of judgments"
                      className="mt-1 w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                    />
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Cases to Analyze</div>
                    <input
                      value={casesCount}
                      onChange={(e) => setCasesCount(e.target.value)}
                      placeholder="15"
                      type="number"
                      min="1"
                      max="100"
                      title="Number of cases (1-100)"
                      className="mt-1 w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                    />
                  </div>
                </div>

                {error && (
                  <div className="mt-3 mx-4 bg-rose-950/40 border border-rose-900/50 rounded-lg p-3">
                    <div className="text-xs text-rose-200 mb-2">{error}</div>
                    <button
                      onClick={() => {
                        setError(null);
                        void runAnalysis();
                      }}
                      className="text-[10px] px-2 py-1 bg-rose-900/40 hover:bg-rose-900/60 border border-rose-800 rounded text-rose-200 transition-colors"
                    >
                      Try Again
                    </button>
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="mt-4 px-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Case Summary</div>
                    <button
                      type="button"
                      onClick={() => void autoFillDevilsAdvocate()}
                      disabled={isAutoFillingDevil || !props.activeCase?.id || !props.activeCase?.caseNumber}
                      className="text-[10px] px-2 py-1 rounded-md border border-white/15 bg-white/5 text-slate-300 hover:bg-white/10 disabled:opacity-50"
                    >
                      {isAutoFillingDevil ? 'AUTO-FILLING…' : 'AUTO-FILL'}
                    </button>
                  </div>
                  <input
                    value={caseSummary}
                    onChange={(e) => setCaseSummary(e.target.value)}
                    placeholder="e.g., Bail application in State v. …"
                    title="Brief summary of your case"
                    className="mt-1 w-full glass-input rounded-lg px-3 py-2 text-xs text-slate-200 focus:border-legal-gold/50 outline-none"
                  />
                </div>

                <div className="mt-3 px-4">
                  <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Your Arguments</div>
                  <textarea
                    value={argumentsText}
                    onChange={(e) => setArgumentsText(e.target.value)}
                    spellCheck={false}
                    placeholder="Paste your draft arguments / key points here…"
                    title="Your main arguments to stress-test"
                    className="mt-1 w-full h-[140px] resize-none glass-input rounded-xl px-4 py-3 text-xs text-slate-200 leading-relaxed outline-none focus:border-legal-gold/50"
                    aria-label="Arguments"
                  />
                </div>

                <div className="mt-3 px-4">
                  <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Citations (optional)</div>
                  <textarea
                    value={citationsRaw}
                    onChange={(e) => setCitationsRaw(e.target.value)}
                    spellCheck={false}
                    placeholder="One citation per line (optional)"
                    title="Supporting citations (optional)"
                    className="mt-1 w-full h-[90px] resize-none glass-input rounded-xl px-4 py-3 text-xs text-slate-200 leading-relaxed outline-none focus:border-legal-gold/50"
                    aria-label="Citations"
                  />
                </div>

                {devilError && (
                  <div className="mt-3 mx-4 bg-rose-950/40 border border-rose-900/50 rounded-lg p-3">
                    <div className="text-xs text-rose-200 mb-2">{devilError}</div>
                    <button
                      onClick={() => {
                        setDevilError(null);
                        void runDevilsAdvocate();
                      }}
                      className="text-[10px] px-2 py-1 bg-rose-900/40 hover:bg-rose-900/60 border border-rose-800 rounded text-rose-200 transition-colors"
                    >
                      Try Again
                    </button>
                  </div>
                )}

                {devilSaveStatus && (
                  <div className="mt-3 mx-4 bg-emerald-950/25 border border-emerald-900/40 rounded-lg p-3">
                    <div className="text-xs text-emerald-200">{devilSaveStatus}</div>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="flex-1 p-4">
            {mode === 'judge' ? (
              <>
                <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase mb-2">Case/Application Details</div>
                <textarea
                  value={caseDetails}
                  onChange={(e) => setCaseDetails(e.target.value)}
                  spellCheck={false}
                  placeholder={"Briefly describe your case or application. Example:\n\nMy client is applying for bail in a murder case (IPC 302). He is a 42-year-old businessman with no criminal record, has been in custody for 3 months. He is a family man with two children, owns property in Delhi, and is ready to surrender passport and comply with all conditions.\n\nI want to understand how this judge typically approaches bail applications in serious offense cases and what factors he weighs most heavily.\n\nThe AI will automatically fetch this judge's past judgments and analyze patterns relevant to your case."}
                  className="w-full h-[280px] lg:h-[calc(100vh-400px)] resize-none glass-input rounded-xl px-4 py-3 text-xs text-slate-200 leading-relaxed outline-none"
                />
                <div className="mt-2 text-[10px] text-slate-500 leading-relaxed">
                  💡 <strong>AI will auto-fetch judgments:</strong> Just describe your case above. The system will automatically search for {judgeName || "the judge"}'s past judgments on {caseType || "this case type"} {timePeriod && `from ${timePeriod}`} and analyze patterns.
                </div>
              </>
            ) : (
              <div className="text-xs text-slate-500 leading-relaxed space-y-3">
                <p><strong className="text-slate-400">💡 Tips for better results:</strong></p>
                <ul className="space-y-1 pl-4">
                  <li>• Keep case summary brief (1-2 sentences)</li>
                  <li>• Paste arguments exactly as you plan to submit</li>
                  <li>• Include key facts, not just legal theory</li>
                  <li>• Add citations if you're relying on specific precedents</li>
                </ul>
                <p className="mt-3 text-slate-600">The AI will simulate opposing counsel and identify weaknesses in your arguments.</p>
              </div>
            )}
          </div>
        </div>

        <div className="w-full lg:flex-1 min-h-0 bg-black/20 backdrop-blur-xl p-5 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between mb-3 shrink-0">
            <div>
              <h4 className="text-sm font-bold text-white">Findings</h4>
              <div className="text-xs text-slate-500">
                {mode === 'judge'
                  ? 'AI-analyzed patterns from judge\'s actual past judgments'
                  : 'Opposing counsel simulation + what to prepare'}
              </div>
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-scroll space-y-3 pr-2 findings-scroll">
            {mode === 'judge' ? (
              <>
                {isWorking && (
                  <div className="space-y-3 animate-pulse">
                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="h-4 bg-slate-700/50 rounded w-1/3 mb-2"></div>
                      <div className="h-5 bg-slate-700/50 rounded w-1/2 mb-1"></div>
                      <div className="h-3 bg-slate-700/50 rounded w-1/4"></div>
                    </div>
                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="h-3 bg-slate-700/50 rounded w-1/4 mb-3"></div>
                      <div className="space-y-2">
                        <div className="h-16 bg-slate-700/50 rounded"></div>
                        <div className="h-16 bg-slate-700/50 rounded"></div>
                      </div>
                    </div>
                  </div>
                )}

                {!isWorking && !result && (
                  <div className="bg-black/10 border border-white/5 rounded-xl p-8 text-center">
                    <div className="text-5xl mb-4">⚖️</div>
                    <div className="text-sm text-slate-300 font-semibold mb-2">AI-Powered Judge Analysis</div>
                    <div className="text-xs text-slate-400 mb-4">Automatically fetch & analyze judicial patterns</div>
                    <div className="text-xs text-slate-500 space-y-2 text-left max-w-md mx-auto">
                      <p className="mb-2"><strong className="text-slate-400">How it works:</strong></p>
                      <div className="space-y-2">
                        <div className="flex gap-2">
                          <span className="text-legal-gold font-bold">1.</span>
                          <span>Enter judge name and court</span>
                        </div>
                        <div className="flex gap-2">
                          <span className="text-legal-gold font-bold">2.</span>
                          <span>Specify case type (required - e.g., "Bail Applications")</span>
                        </div>
                        <div className="flex gap-2">
                          <span className="text-legal-gold font-bold">3.</span>
                          <span>Add time period and case count (optional)</span>
                        </div>
                        <div className="flex gap-2">
                          <span className="text-legal-gold font-bold">4.</span>
                          <span>Describe your case/application situation</span>
                        </div>
                        <div className="flex gap-2">
                          <span className="text-legal-gold font-bold">5.</span>
                          <span>Click ANALYZE - AI will auto-fetch judgments</span>
                        </div>
                      </div>
                    </div>
                    <div className="mt-6 text-[10px] text-slate-600">
                      🤖 AI fetches judgments automatically - no manual pasting needed!
                    </div>
                  </div>
                )}

                {!isWorking && result && (
                  <>
                    {/* Quick Summary */}
                    <div className="bg-gradient-to-br from-legal-gold/10 to-amber-900/10 border border-legal-gold/20 rounded-xl p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="text-xs text-amber-300/80 font-semibold tracking-wider uppercase">Analysis Complete</div>
                          <div className="text-sm text-slate-200 font-bold mt-1">{result.judge_name}</div>
                          <div className="flex items-center gap-3 mt-2 text-xs">
                            <span className="text-slate-400">📊 {result.total_cases_analyzed} cases</span>
                            <span className="text-slate-400">🎯 {result.patterns?.length || 0} patterns</span>
                            <span className="text-slate-400">💡 {result.recommendations?.length || 0} tips</span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          {result.patterns?.filter(p => p.signal === 'high').length > 0 && (
                            <span className="text-xs px-2 py-1 rounded-full bg-rose-500/20 border border-rose-400/40 text-rose-200">
                              ⚠️ {result.patterns.filter(p => p.signal === 'high').length} high
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {result.source_provenance?.length ? (
                      <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                        <div className="flex items-center justify-between gap-3 mb-3">
                          <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Sources Used</div>
                          <div className="text-[10px] text-slate-500">{result.source_provenance.length} records</div>
                        </div>
                        <div className="space-y-2 max-h-72 overflow-y-auto pr-1 findings-scroll">
                          {result.source_provenance.slice(0, 12).map((source, idx) => (
                            <div key={idx} className="border border-white/10 rounded-lg p-3 bg-white/5">
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0">
                                  <div className="text-xs text-slate-200 font-semibold truncate">{source.title}</div>
                                  <div className="text-[11px] text-slate-400 mt-1 truncate">
                                    {source.citation}{source.year ? ` • ${source.year}` : ''}{source.court ? ` • ${source.court}` : ''}
                                  </div>
                                </div>
                                <span className="text-[10px] px-2 py-1 rounded-full border border-white/10 bg-black/20 text-slate-300 capitalize">
                                  {source.origin || 'corpus'}
                                </span>
                              </div>
                              {source.summary && (
                                <div className="mt-2 text-[11px] text-slate-400 leading-relaxed">
                                  {source.summary}
                                </div>
                              )}
                              {source.source_url && (
                                <a
                                  href={source.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="mt-2 inline-flex items-center gap-1 text-[10px] text-legal-gold hover:text-amber-300"
                                >
                                  <ExternalLink size={10} />
                                  Open source
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase mb-3">Patterns</div>
                      {result.patterns?.length ? (
                        <div className="space-y-3">
                          {result.patterns.map((p, idx) => (
                            <div key={idx} className="border border-white/10 rounded-lg p-3 bg-white/5 hover:bg-white/[0.07] transition-all duration-200 group">
                              <div className="flex items-start justify-between gap-2 mb-2">
                                <div className="flex-1">
                                  <div className="text-xs text-slate-200 font-semibold leading-snug">{p.pattern}</div>
                                </div>
                                <span className={`text-[10px] px-2 py-1 rounded-full border font-semibold flex items-center gap-1 shrink-0 ${signalColor(p.signal)}`}>
                                  <span>{signalIcon(p.signal)}</span>
                                  <span>{p.signal.toUpperCase()}</span>
                                </span>
                              </div>
                              {!!p.evidence?.length && (
                                <div className="mt-3 space-y-1.5">
                                  <div className="text-[10px] text-slate-500 font-semibold tracking-wider uppercase">Evidence:</div>
                                  <div className="text-xs text-slate-300 space-y-1.5 pl-3 border-l-2 border-slate-700">
                                    {p.evidence.slice(0, 5).map((e, i) => (
                                      <div key={i} className="leading-relaxed">• {e}</div>
                                    ))}
                                    {p.evidence.length > 5 && (
                                      <div className="text-[11px] text-slate-500 italic">+ {p.evidence.length - 5} more evidence points</div>
                                    )}
                                  </div>
                                </div>
                              )}
                              {!!p.caveats?.length && (
                                <div className="mt-3 bg-amber-950/20 border border-amber-900/30 rounded p-2">
                                  <div className="text-[10px] text-amber-400/80 font-semibold mb-1">⚠️ Limitations:</div>
                                  <div className="text-[11px] text-amber-300/70 leading-relaxed">{p.caveats[0]}</div>
                                </div>
                              )}
                              {/* Quick Actions */}
                              <div className="mt-3 pt-3 border-t border-white/5 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button
                                  onClick={() => copyToClipboard(`Pattern: ${p.pattern}\n\nEvidence:\n${p.evidence?.join('\n') || 'None'}`)}
                                  className="text-[10px] px-2 py-1 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 rounded text-slate-300 transition-colors"
                                  title="Copy this pattern"
                                >
                                  📋 Copy
                                </button>
                                <button
                                  onClick={() =>
                                    copyToClipboard(
                                      `Analyze this judicial pattern:\n\nPattern: ${p.pattern}\n\nEvidence:\n${p.evidence?.join('\n') || 'None'}\n\nQuestion: How should I adapt my strategy for this judge?`
                                    )
                                  }
                                  className="text-[10px] px-2 py-1 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 rounded text-slate-300 transition-colors"
                                  title="Ask AI about this pattern"
                                >
                                  🤖 Ask AI
                                </button>
                              </div>
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
                {devilWorking && (
                  <div className="space-y-3 animate-pulse">
                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="h-4 bg-slate-700/50 rounded w-1/3 mb-2"></div>
                      <div className="h-6 bg-slate-700/50 rounded w-1/4"></div>
                    </div>
                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="h-3 bg-slate-700/50 rounded w-1/4 mb-3"></div>
                      <div className="space-y-2">
                        <div className="h-20 bg-slate-700/50 rounded"></div>
                        <div className="h-20 bg-slate-700/50 rounded"></div>
                      </div>
                    </div>
                  </div>
                )}

                {!devilWorking && !devilResult && (
                  <div className="bg-black/10 border border-white/5 rounded-xl p-8 text-center">
                    <div className="text-5xl mb-4">⚔️</div>
                    <div className="text-sm text-slate-300 font-semibold mb-2">Stress-Test Your Arguments</div>
                    <div className="text-xs text-slate-400 mb-4">Simulate opposition counsel and discover weaknesses before they do</div>
                    <div className="text-xs text-slate-500 space-y-1 text-left max-w-md mx-auto">
                      <p className="mb-2"><strong className="text-slate-400">What you'll get:</strong></p>
                      <ul className="space-y-1 pl-4">
                        <li>• Vulnerability score (0-10)</li>
                        <li>• Specific attack points opposition may use</li>
                        <li>• Counter-arguments and citations</li>
                        <li>• Preparation recommendations</li>
                      </ul>
                    </div>
                    <div className="mt-6 text-[10px] text-slate-600">
                      Enter case summary & arguments above, then click SIMULATE
                    </div>
                  </div>
                )}
                {!devilWorking && devilResult && (
                  <>
                    {devilUsedFallback && (
                      <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl p-3 text-xs text-amber-200">
                        Running on fallback mode because live Devil's Advocate was unavailable.
                      </div>
                    )}

                    {responseDraft && (
                      <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Response Workbench</div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => void copyToClipboard(responseDraft)}
                              className="text-[10px] px-2 py-1 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 rounded text-slate-300 transition-colors"
                            >
                              Copy
                            </button>
                            <button
                              onClick={() => {
                                setArgumentsText((prev) => (prev.trim() ? `${prev}\n\n${responseDraft}` : responseDraft));
                                setDevilSaveStatus('Response draft added to Your Arguments.');
                              }}
                              className="text-[10px] px-2 py-1 bg-legal-gold/20 hover:bg-legal-gold/30 border border-legal-gold/30 rounded text-legal-gold transition-colors"
                            >
                              Use In Arguments
                            </button>
                          </div>
                        </div>
                        <textarea
                          value={responseDraft}
                          onChange={(e) => setResponseDraft(e.target.value)}
                          title="Response workbench draft"
                          aria-label="Response workbench draft"
                          placeholder="Generated response draft"
                          className="w-full h-36 resize-y glass-input rounded-lg px-3 py-2 text-xs text-slate-200 leading-relaxed outline-none"
                        />
                      </div>
                    )}

                    {/* Quick Summary */}
                    <div className="bg-gradient-to-br from-rose-500/10 to-red-900/10 border border-rose-400/20 rounded-xl p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="text-xs text-rose-300/80 font-semibold tracking-wider uppercase mb-1">Stress Test Complete</div>
                          <div className="flex items-center gap-4 mt-3">
                            <div>
                              <div className="text-2xl font-bold">
                                {Number.isFinite(devilResult.vulnerability_score) ? (
                                  <span className={devilResult.vulnerability_score > 7 ? 'text-rose-300' : devilResult.vulnerability_score > 4 ? 'text-amber-300' : 'text-emerald-300'}>
                                    {devilResult.vulnerability_score.toFixed(1)}<span className="text-lg text-slate-400">/10</span>
                                  </span>
                                ) : (
                                  <span className="text-slate-400">N/A</span>
                                )}
                              </div>
                              <div className="text-[10px] text-slate-400 mt-1">Vulnerability Score</div>
                            </div>
                            {/* Visual Gauge */}
                            {Number.isFinite(devilResult.vulnerability_score) && (
                              <div className="flex-1 max-w-[200px]">
                                <div className="h-2 bg-black/30 rounded-full overflow-hidden border border-white/10">
                                  <progress
                                    className={`vulnerability-progress ${
                                      devilResult.vulnerability_score > 7
                                        ? 'vulnerability-progress-high'
                                        : devilResult.vulnerability_score > 4
                                          ? 'vulnerability-progress-medium'
                                          : 'vulnerability-progress-low'
                                    }`}
                                    max={10}
                                    value={devilResult.vulnerability_score}
                                  />
                                </div>
                                <div className="flex justify-between text-[9px] text-slate-500 mt-1">
                                  <span>Low</span>
                                  <span>Medium</span>
                                  <span>High</span>
                                </div>
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-3 mt-3 text-xs">
                            <span className="text-slate-400">⚔️ {devilResult.attack_points?.length || 0} attacks</span>
                            <span className="text-slate-400">🛡️ {devilResult.preparation_recommendations?.length || 0} defenses</span>
                          </div>
                        </div>
                        <div className="text-xs text-slate-400 max-w-[200px] bg-black/20 rounded-lg p-3 border border-white/5">
                          <div className="font-semibold text-slate-300 mb-1">💡 What this means:</div>
                          {devilResult.vulnerability_score > 7 ? (
                            <p>High vulnerability. Opposition has strong attack angles. Strengthen your arguments urgently.</p>
                          ) : devilResult.vulnerability_score > 4 ? (
                            <p>Moderate vulnerability. Some weak points exist. Address them before submission.</p>
                          ) : (
                            <p>Low vulnerability. Arguments are solid. Minor improvements suggested below.</p>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Attack Points</div>
                        {devilResult.attack_points?.length > 0 && (
                          <div className="text-[10px] text-slate-400">
                            {devilResult.attack_points.length} vulnerabilities found
                          </div>
                        )}
                      </div>
                      {devilResult.attack_points?.length ? (
                        <div className="space-y-3">
                          {devilResult.attack_points.slice(0, 12).map((p, idx) => {
                            // Determine severity based on content
                            const hasCitation = !!p.counter_citation;
                            const hasAttack = !!p.suggested_attack;
                            const severity = hasCitation && hasAttack ? 'high' : hasAttack || hasCitation ? 'medium' : 'low';
                            const severityColor = 
                              severity === 'high' ? 'border-rose-500/40 bg-rose-950/20' :
                              severity === 'medium' ? 'border-amber-500/40 bg-amber-950/20' :
                              'border-slate-600/40 bg-slate-900/20';
                            const severityBadge =
                              severity === 'high' ? 'bg-rose-500/20 text-rose-300 border-rose-400/40' :
                              severity === 'medium' ? 'bg-amber-500/20 text-amber-300 border-amber-400/40' :
                              'bg-slate-700/20 text-slate-400 border-slate-600/40';
                            
                            return (
                              <div key={idx} className={`border rounded-lg p-3 transition-all duration-200 group ${severityColor}`}>
                                <div className="flex items-start justify-between gap-2 mb-2">
                                  <div className="text-xs text-slate-200 font-semibold leading-snug">
                                    {idx + 1}. {p.title || `Attack Point ${idx + 1}`}
                                  </div>
                                  <span className={`text-[9px] px-2 py-0.5 rounded-full border font-bold tracking-wider shrink-0 ${severityBadge}`}>
                                    {severity === 'high' ? '⚠️ CRITICAL' : severity === 'medium' ? '⚡ MODERATE' : 'ℹ️ MINOR'}
                                  </span>
                                </div>
                                
                                {p.weakness && (
                                  <div className="mt-2 bg-black/20 rounded-lg p-2 border border-white/5">
                                    <div className="text-[10px] text-slate-500 font-semibold mb-1">🔴 Weakness Identified:</div>
                                    <div className="text-xs text-slate-300 leading-relaxed">{p.weakness}</div>
                                  </div>
                                )}
                                
                                {p.suggested_attack && (
                                  <div className="mt-2 bg-black/20 rounded-lg p-2 border border-white/5">
                                    <div className="text-[10px] text-slate-500 font-semibold mb-1">⚔️ Opposition's Likely Argument:</div>
                                    <div className="text-xs text-slate-300 leading-relaxed">{p.suggested_attack}</div>
                                  </div>
                                )}
                                
                                {p.counter_citation && (
                                  <div className="mt-2 bg-black/20 rounded-lg p-2 border border-white/5">
                                    <div className="flex items-center justify-between gap-2 mb-1">
                                      <div className="text-[10px] text-slate-500 font-semibold">📖 Counter-Citation:</div>
                                      <button
                                        type="button"
                                        onClick={() => void handleCounterCitationPreview(p.counter_citation || '', p.title || `Attack Point ${idx + 1}`)}
                                        className="text-[10px] px-2 py-1 rounded-md border border-white/10 bg-black/20 text-slate-300 hover:text-legal-gold hover:border-legal-gold/30 transition-all inline-flex items-center gap-1"
                                      >
                                        <Eye size={10} />
                                        Preview
                                      </button>
                                    </div>
                                    <button
                                      type="button"
                                      onClick={() => void handleCounterCitationPreview(p.counter_citation || '', p.title || `Attack Point ${idx + 1}`)}
                                      className="text-left w-full text-xs text-blue-300 leading-relaxed font-mono hover:text-blue-200 transition-colors"
                                      title="Preview citation source"
                                    >
                                      {p.counter_citation}
                                    </button>
                                  </div>
                                )}
                                
                                {!p.weakness && !p.counter_citation && !p.suggested_attack && p.raw && (
                                  <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-300 leading-relaxed">{p.raw}</pre>
                                )}
                                
                                {/* Quick Actions */}
                                <div className="mt-3 pt-3 border-t border-white/5 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button
                                    onClick={() => copyToClipboard(`${p.title || 'Attack Point'}\n\nWeakness: ${p.weakness || 'N/A'}\nSuggested Attack: ${p.suggested_attack || 'N/A'}\nCounter-Citation: ${p.counter_citation || 'N/A'}`)}
                                    className="text-[10px] px-2 py-1 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 rounded text-slate-300 transition-colors"
                                    title="Copy this attack point"
                                  >
                                    📋 Copy
                                  </button>
                                  <button
                                    onClick={() => {
                                      const draft = buildResponseDraft(p, idx);
                                      setResponseDraft(draft);
                                      setDevilSaveStatus('Response draft generated in workbench.');
                                    }}
                                    className="text-[10px] px-2 py-1 bg-slate-800/50 hover:bg-slate-700 border border-slate-700 rounded text-slate-300 transition-colors"
                                    title="Draft a response"
                                  >
                                    ✍️ Respond
                                  </button>
                                </div>
                              </div>
                            );
                          })}
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

      {selectedCitationPreview && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-[1px] z-[70] flex items-center justify-center p-4">
          <div className="w-full max-w-3xl max-h-[85vh] bg-slate-950 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            <div className="p-4 border-b border-white/10 flex items-start justify-between gap-3 bg-white/5">
              <div className="min-w-0">
                <h4 className="text-sm font-semibold text-slate-100 truncate">{selectedCitationPreview.title}</h4>
                <p className="text-[11px] text-legal-gold/70 truncate mt-1">
                  {selectedCitationPreview.url.replace(/^https?:\/\//, '')}
                </p>
              </div>
              <button
                onClick={() => {
                  setSelectedCitationPreview(null);
                  setCitationPreviewState({ status: 'idle' });
                }}
                className="text-slate-400 hover:text-white transition-colors"
                title="Close Preview"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4">
              {citationPreviewState.status === 'loading' && selectedCitationPreview.url === citationPreviewState.url && (
                <div className="py-12 flex flex-col items-center gap-2 text-slate-400">
                  <Loader2 size={20} className="animate-spin" />
                  <p className="text-sm">Fetching preview and extracting key content...</p>
                </div>
              )}

              {citationPreviewState.status === 'error' && selectedCitationPreview.url === citationPreviewState.url && (
                <div className="p-4 rounded-lg border border-red-500/20 bg-red-500/10 text-red-200 text-sm">
                  {citationPreviewState.message}
                </div>
              )}

              {citationPreviewState.status === 'ok' && selectedCitationPreview.url === citationPreviewState.url && (
                <>
                  {citationPreviewState.data.summary_ai && (
                    <div className="p-4 rounded-lg border border-legal-gold/20 bg-legal-gold/10">
                      <h5 className="text-xs font-bold text-legal-gold mb-2 uppercase tracking-wide">AI Summary</h5>
                      <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{citationPreviewState.data.summary_ai}</p>
                    </div>
                  )}

                  {citationPreviewState.data.key_points && citationPreviewState.data.key_points.length > 0 && (
                    <div className="p-4 rounded-lg border border-white/10 bg-white/5">
                      <h5 className="text-xs font-bold text-slate-300 mb-2 uppercase tracking-wide">Key Points</h5>
                      <ul className="list-disc list-inside space-y-1 text-sm text-slate-300">
                        {citationPreviewState.data.key_points.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="p-4 rounded-lg border border-white/10 bg-slate-900/70">
                    <h5 className="text-xs font-bold text-slate-300 mb-2 uppercase tracking-wide">Extracted Content</h5>
                    <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                      {citationPreviewState.data.content || 'No preview text extracted.'}
                    </p>
                  </div>
                </>
              )}
            </div>

            <div className="p-4 border-t border-white/10 bg-white/5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={addCitationPreviewToWall}
                disabled={citationPreviewState.status !== 'ok' || citationPreviewState.url !== selectedCitationPreview.url}
                className="text-xs px-3 py-1.5 rounded-md border border-legal-gold/30 bg-legal-gold/10 text-legal-gold hover:bg-legal-gold/20 transition-all inline-flex items-center gap-1 disabled:opacity-50"
              >
                <Plus size={12} />
                Add To Wall
              </button>
              <a
                href={selectedCitationPreview.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs px-3 py-1.5 rounded-md border border-white/10 bg-black/20 text-slate-300 hover:text-legal-gold hover:border-legal-gold/30 transition-all inline-flex items-center gap-1"
              >
                <ExternalLink size={12} />
                Open Original
              </a>
            </div>
          </div>
        </div>
      )}
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

  const [nodes, setNodes] = useState<NodeData[]>([]);

  // Start with no connections - they should only appear after "Analyze Wall"
  const [connections, setConnections] = useState<Connection[]>([]);

  // Clear any old cached connections on mount
  useEffect(() => {
    // This ensures we always start fresh with no connections
    setConnections([]);
  }, []);

  const caseId = props.activeCase?.id ? String(props.activeCase.id) : 'default';
  const caseTitle = props.activeCase?.title ?? 'Current Matter';
  const caseNumber = props.activeCase?.caseNumber ?? '';

  const handleAddCitationToWall = useCallback((payload: { title: string; content: string; url?: string; citation: string }) => {
    setNodes((prev) => {
      const nextId = prev.length ? Math.max(...prev.map((n) => n.id)) + 1 : 1;
      const baseX = window.innerWidth / 2 - 160;
      const baseY = window.innerHeight / 2 - 120;
      const spread = (nextId % 5) * 34;

      const next: NodeData = {
        id: nextId,
        title: payload.title || 'Counter Citation',
        type: 'Precedent',
        date: new Date().toLocaleDateString('en-IN'),
        status: 'Verified',
        x: baseX + spread,
        y: baseY + spread,
        rotation: (nextId % 6) - 3,
        pinColor: 'blue',
        source: 'Counter Citation',
        caseNumber,
        content: payload.content || payload.citation,
        attachments: [
          {
            name: payload.citation,
            kind: 'document',
            url: payload.url,
          },
        ],
      };

      return [...prev, next];
    });
  }, [caseNumber]);
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

  useEffect(() => {
    if (!props.activeCase?.id || !caseNumber) {
      setNodes([]);
      setConnections([]);
      return;
    }

    let cancelled = false;

    const hydrateWall = async () => {
      try {
        const [caseRes, docsRes] = await Promise.all([
          fetch(`/api/v1/cases/${props.activeCase?.id}`),
          fetch(`/api/v1/documents/?case_number=${encodeURIComponent(caseNumber)}&limit=50`),
        ]);

        if (!caseRes.ok) throw new Error(`Failed to load case (${caseRes.status})`);
        if (!docsRes.ok) throw new Error(`Failed to load documents (${docsRes.status})`);

        const caseData = await caseRes.json() as {
          title?: string;
          filing_date?: string;
          timeline?: Array<{ id: string; date: string; event_type: string; title: string; description?: string; documents?: string[] }>;
          notes?: string | null;
        };
        const docsData = await docsRes.json() as { documents?: Array<{ id: string; title: string; date?: string; summary?: string; url?: string | null }> };

        const documents = Array.isArray(docsData.documents) ? docsData.documents : [];
        const timeline = Array.isArray(caseData.timeline) ? caseData.timeline : [];

        const centerX = window.innerWidth / 2 - 160;
        const topY = 120;
        const mappedNodes: NodeData[] = [];

        timeline.forEach((event, idx) => {
          const docId = Array.isArray(event.documents) ? event.documents[0] : undefined;
          const match = documents.find((doc) => doc.id === docId);
          const eventType = String(event.event_type || '').toLowerCase();
          const nodeType: NodeData['type'] =
            eventType === 'judgment' ? 'Precedent' : eventType === 'hearing' ? 'Statement' : 'Evidence';

          mappedNodes.push({
            id: idx + 1,
            title: event.title || match?.title || `Case Event ${idx + 1}`,
            type: nodeType,
            date: event.date ? new Date(event.date).toLocaleDateString('en-IN') : props.activeCase?.date || '',
            status: nodeType === 'Precedent' ? 'Verified' : 'Pending',
            x: centerX + ((idx % 2 === 0 ? -1 : 1) * 260),
            y: topY + idx * 170,
            rotation: idx % 2 === 0 ? -2 : 2,
            pinColor: nodeType === 'Precedent' ? 'blue' : nodeType === 'Statement' ? 'yellow' : 'green',
            source: 'Case Timeline',
            caseNumber,
            documentId: docId,
            content: match?.summary || event.description || '',
            attachments: match
              ? [{ name: match.title, kind: 'document', url: match.url || undefined }]
              : [],
          });
        });

        documents.forEach((doc, docIdx) => {
          if (mappedNodes.some((node) => node.documentId === doc.id)) return;
          mappedNodes.push({
            id: timeline.length + docIdx + 1,
            title: doc.title,
            type: 'Evidence',
            date: doc.date ? new Date(doc.date).toLocaleDateString('en-IN') : props.activeCase?.date || '',
            status: 'Verified',
            x: centerX + ((docIdx % 3) - 1) * 290,
            y: topY + timeline.length * 170 + 140 + Math.floor(docIdx / 3) * 170,
            rotation: (docIdx % 3) - 1,
            pinColor: 'red',
            source: 'Case Document',
            caseNumber,
            documentId: doc.id,
            content: doc.summary || '',
            attachments: [{ name: doc.title, kind: 'document', url: doc.url || undefined }],
          });
        });

        if (caseData.notes) {
          mappedNodes.push({
            id: mappedNodes.length + 1,
            title: 'Case Strategy Notes',
            type: 'Strategy',
            date: props.activeCase?.date || '',
            status: 'Pending',
            x: centerX,
            y: topY + Math.max(mappedNodes.length, 1) * 170,
            rotation: 0,
            pinColor: 'yellow',
            source: 'Case Notes',
            caseNumber,
            content: caseData.notes,
            attachments: [],
          });
        }

        if (!cancelled) {
          setNodes(mappedNodes);
          setConnections([]);
        }
      } catch {
        if (!cancelled) {
          setNodes([]);
          setConnections([]);
        }
      }
    };

    void hydrateWall();
    return () => {
      cancelled = true;
    };
  }, [caseNumber, props.activeCase?.date, props.activeCase?.id]);

  const handleUploadClick = () => {
    uploadInputRef.current?.click();
  };

  const handleUploadFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;

    void (async () => {
      const centerX = window.innerWidth / 2 - 160;
      const baseY = 180 + nodes.length * 40;
      const created: NodeData[] = [];

      for (const [idx, file] of Array.from(files).entries()) {
        const form = new FormData();
        form.append('file', file);
        form.append('title', file.name.replace(/\.pdf$/i, ''));
        if (caseNumber) form.append('case_number', caseNumber);

        try {
          await fetch('/api/v1/documents/upload', { method: 'POST', body: form });
        } catch {
          // keep local node even if upload fails visibly in backend logs
        }

        created.push({
          id: Date.now() + idx,
          title: file.name,
          type: 'Evidence',
          date: new Date().toLocaleDateString('en-IN'),
          status: 'Pending',
          x: centerX + (idx % 3) * 40,
          y: baseY + Math.floor(idx / 3) * 40,
          rotation: Math.random() * 6 - 3,
          pinColor: 'yellow',
          source: 'Upload',
          caseNumber,
          content: 'Uploaded document pending extraction.',
          attachments: [{ name: file.name, kind: 'document', sizeBytes: file.size }],
        });
      }

      setNodes((prev) => [...prev, ...created]);
    })();
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
      <div className="flex h-screen min-h-screen w-full text-legal-text font-sans overflow-hidden relative bg-legal-bg">
        <RadialMenu activeTab={activeTab} setActiveTab={setActiveTab} onBack={props.onBack} />
        <StrategyAnalytics activeCase={props.activeCase} onAddCitationToWall={handleAddCitationToWall} />
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
  const [authChecked, setAuthChecked] = useState(false);
  const [authToken, setAuthToken] = useState<string | null>(() => localStorage.getItem('jr_authToken'));
  const [authUser, setAuthUser] = useState<{ id: string; email: string; name?: string; role?: string } | null>(() => {
    const raw = localStorage.getItem('jr_authUser');
    return raw ? (JSON.parse(raw) as { id: string; email: string; name?: string; role?: string }) : null;
  });
  const [view, setView] = useState<View>('landing');
  const [activeCase, setActiveCase] = useState<CaseData | null>(() => {
    const saved = localStorage.getItem('jr_activeCase');
    return saved ? (JSON.parse(saved) as CaseData) : null;
  });

  useEffect(() => {
    const verifyAuth = async () => {
      if (!authToken) {
        setAuthChecked(true);
        setView('auth');
        return;
      }

      try {
        const res = await fetch('/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${authToken}` },
        });
        if (!res.ok) throw new Error('invalid token');
        const user = await res.json();
        const normalized = {
          id: String(user.id),
          email: String(user.email),
          name: user.name ? String(user.name) : undefined,
          role: user.role ? String(user.role) : undefined,
        };
        setAuthUser(normalized);
        localStorage.setItem('jr_authUser', JSON.stringify(normalized));
      } catch {
        localStorage.removeItem('jr_authToken');
        localStorage.removeItem('jr_authUser');
        setAuthToken(null);
        setAuthUser(null);
        setView('auth');
      } finally {
        setAuthChecked(true);
      }
    };

    void verifyAuth();
  }, [authToken]);

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
      id: String(Date.now()),
      title: 'New Case',
      type: 'General',
      date: new Date().toLocaleDateString(),
      status: 'Active',
    });
    setView('wall');
  };

  const handleBack = () => setView('selection');

  const handleAuthenticated = (token: string, user: { id: string; email: string; name?: string; role?: string }) => {
    localStorage.setItem('jr_authToken', token);
    localStorage.setItem('jr_authUser', JSON.stringify(user));
    setAuthToken(token);
    setAuthUser(user);
    setView('landing');
  };

  const handleSignOut = () => {
    localStorage.removeItem('jr_authToken');
    localStorage.removeItem('jr_authUser');
    localStorage.removeItem('jr_activeCase');
    setAuthToken(null);
    setAuthUser(null);
    setActiveCase(null);
    setView('auth');
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen w-full bg-legal-bg text-legal-text flex items-center justify-center">
        <div className="text-sm text-slate-400">Checking authentication...</div>
      </div>
    );
  }

  if (!authToken || !authUser || view === 'auth') {
    return <AuthPage onAuthenticated={handleAuthenticated} />;
  }

  return (
    <>
      <button
        type="button"
        onClick={handleSignOut}
        className="fixed top-4 right-4 z-[200] rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 text-xs text-slate-300 hover:text-white"
      >
        Sign Out
      </button>
      {view === 'landing' && <LandingPage onEnter={handleEnter} />}
      {view === 'selection' && <CaseSelection onSelectCase={handleSelectCase} onNewCase={handleNewCase} />}
      {view === 'wall' && <DetectiveWall onBack={handleBack} activeCase={activeCase} />}
    </>
  );
}
