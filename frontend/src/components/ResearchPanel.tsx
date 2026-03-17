import React, { useEffect, useMemo, useRef, useState } from 'react';
import './ResearchPanel.css';
import {
  AlertTriangle,
  BookOpen,
  Search,
  ShieldAlert,
  X,
  Clock,
  Bookmark,
  ExternalLink,
  Eye,
  Loader2,
  Trash2
} from 'lucide-react';

export type ResearchItem = {
  id: string;
  title: string;
  type: string;
  summary?: string;
  source?: string;
  url?: string;
  publisher?: string;
  authority?: 'official' | 'study' | 'web' | string;
  tags?: string[];
  size?: string;
  date?: string;
  score?: number;
};

type Category = 'all' | 'case-law' | 'acts' | 'official' | 'study';

type SourcePreview = {
  title: string;
  content: string;
  full_text_length: number;
  error?: string | null;
  summary_ai?: string;
  key_points?: string[];
  quotes?: string[];
};

type GroupKey = 'case-law' | 'acts' | 'official' | 'study' | 'web';

const GROUP_META: Record<GroupKey, { label: string; hint: string }> = {
  'case-law': { label: 'Case Law & Judgments', hint: 'Precedents from courts and legal reporters' },
  acts: { label: 'Acts, Codes & Statutes', hint: 'Bare acts, sections, codes, and statutory law' },
  official: { label: 'Official Government Sources', hint: 'Government and court portals' },
  study: { label: 'Commentary & Study Material', hint: 'Articles, explainers, and legal commentary' },
  web: { label: 'General Web Results', hint: 'Additional internet sources' },
};

function classifyGroup(item: ResearchItem): GroupKey {
  const t = (item.type || '').toLowerCase();
  const a = (item.authority || '').toLowerCase();
  if (t === 'precedent') return 'case-law';
  if (t === 'act' || t === 'constitution' || t === 'law') return 'acts';
  if (a === 'official' || t === 'official') return 'official';
  if (a === 'study' || t === 'study') return 'study';
  return 'web';
}

function sanitizeTitle(title: string): string {
  if (!title) return 'Untitled';
  // Remove common junk patterns
  let cleaned = title
    .replace(/^(robbery|.*? v\.\s+\w+)/i, (match) => match) // keep case names
    .replace(/\bdoctypes?\s*[:=]\s*\w+/gi, '') // remove doctypes:xxx
    .replace(/\bfiletype\s*[:=]\s*\w+/gi, '') // remove filetype:xxx
    .replace(/site:\S+/gi, '') // remove site: operators
    .replace(/\s{2,}/g, ' ') // collapse multiple spaces
    .trim();
  // Remove trailing technical junk
  cleaned = cleaned.replace(/\s*\(.*?(pdf|docx?|zip|archive).*?\)\s*$/i, '').trim();
  // If too short after cleaning, return original
  return cleaned && cleaned.length > 5 ? cleaned : title;
}

export function ResearchPanel(props: {
  isOpen: boolean;
  onClose: () => void;
  onDragStart: (e: React.MouseEvent<HTMLElement>, item: ResearchItem) => void;
}) {
  // Core State
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<'all' | 'case-law' | 'acts' | 'official' | 'study'>('all');
  const [items, setItems] = useState<ResearchItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [searchTimeMs, setSearchTimeMs] = useState(0);

  // UI State
  const [bookmarks, setBookmarks] = useState<Set<string>>(new Set());
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [citationChecks, setCitationChecks] = useState<Record<string, { status: string; emoji: string; message: string }>>({});
  const [checkingCitation, setCheckingCitation] = useState<string | null>(null);
  const [selectedPreviewItem, setSelectedPreviewItem] = useState<ResearchItem | null>(null);
  const [previewState, setPreviewState] = useState<
    | { status: 'idle' }
    | { status: 'loading'; url: string }
    | { status: 'ok'; url: string; data: SourcePreview }
    | { status: 'error'; url: string; message: string }
  >({ status: 'idle' });
  const previewCacheRef = useRef<Map<string, { kind: 'ok'; data: SourcePreview } | { kind: 'error'; message: string }>>(
    new Map()
  );

  // Pagination State
  const [displayLimit, setDisplayLimit] = useState(50);
  const [, setHasMore] = useState(false);

  // Load saved data from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem('jr_research_bookmarks');
      if (saved) setBookmarks(new Set(JSON.parse(saved)));
      
      const history = localStorage.getItem('jr_research_history');
      if (history) setSearchHistory(JSON.parse(history).slice(0, 10));
    } catch (e) {
      console.error('Failed to load research data:', e);
    }
  }, []);

  // Save bookmarks
  useEffect(() => {
    localStorage.setItem('jr_research_bookmarks', JSON.stringify([...bookmarks]));
  }, [bookmarks]);

  // Main search effect
  useEffect(() => {
    if (!props.isOpen) return;

    let cancelled = false;
    const controller = new AbortController();

    const performSearch = async () => {
      setIsLoading(true);
      setLoadError(null);
      setDisplayLimit(50); // Reset pagination on new search
      
      try {
        const res = await fetch('/api/v1/research/sources/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: query.trim() || '',
            category: category === 'all' ? null : 
                     category === 'case-law' ? 'Precedent' :
                     category === 'acts' ? 'Act' :
                     category === 'official' ? 'Official' :
                     category === 'study' ? 'Study' : null,
            authority: category === 'official' ? 'official' : 
                      category === 'study' ? 'study' : null,
            limit: 200,  // Request more results from backend
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const detail = await res.text();
          throw new Error(detail || `API error: ${res.status}`);
        }

        const data = await res.json();
        
        if (!cancelled) {
          // Handle response - could be {results: [...]} or just [...]
          const results = data.results || (Array.isArray(data) ? data : []);
          console.log('Search results:', results);
          setItems(results);
          setTotalCount(data.total_count ?? results.length);
          setSearchTimeMs(data.search_time_ms ?? 0);
          
          // Reset display limit and check if more results available
          setDisplayLimit(50);
          setHasMore(results.length > 50);
          
          // Add to search history if query is meaningful
          if (query.trim() && query.length > 2) {
            setSearchHistory(prev => {
              const updated = [query, ...prev.filter(h => h !== query)].slice(0, 10);
              localStorage.setItem('jr_research_history', JSON.stringify(updated));
              return updated;
            });
          }
        }
      } catch (e) {
        if (!cancelled && !(e instanceof DOMException && e.name === 'AbortError')) {
          console.error('Search error:', e);
          setLoadError('Unable to load sources. Please check backend connection.');
          setItems([]);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    // Debounce: 500ms
    const timer = window.setTimeout(() => void performSearch(), 500);
    
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [props.isOpen, query, category]);

  // Citation check
  const handleCheckAuthority = async (e: React.MouseEvent, item: ResearchItem) => {
    e.stopPropagation();
    e.preventDefault();
    
    const query = item.title;
    setCheckingCitation(item.id);
    
    try {
      const safe = encodeURIComponent(query);
      const res = await fetch(`/api/v1/research/shepardize/${safe}`);
      const data = await res.json();
      
      setCitationChecks(prev => ({
        ...prev,
        [item.id]: {
          status: data.status || 'unknown',
          emoji: data.status_emoji || '⚪',
          message: data.message || 'Status check completed'
        }
      }));
    } catch (e) {
      setCitationChecks(prev => ({
        ...prev,
        [item.id]: {
          status: 'error',
          emoji: '⚠️',
          message: 'Unable to verify citation status'
        }
      }));
    } finally {
      setCheckingCitation(null);
    }
  };

  // Bookmark toggle
  const toggleBookmark = (itemId: string) => {
    setBookmarks(prev => {
      const updated = new Set(prev);
      if (updated.has(itemId)) {
        updated.delete(itemId);
      } else {
        updated.add(itemId);
      }
      return updated;
    });
  };

  // Remove from search history
  const removeFromHistory = (e: React.MouseEvent, historyItem: string) => {
    e.stopPropagation();
    setSearchHistory(prev => prev.filter(h => h !== historyItem));
    localStorage.setItem('jr_research_history', JSON.stringify(searchHistory.filter(h => h !== historyItem)));
  };

  const visibleItems = useMemo(() => items.slice(0, displayLimit), [items, displayLimit]);

  const groupedResults = useMemo(() => {
    const groups: Record<GroupKey, ResearchItem[]> = {
      'case-law': [],
      acts: [],
      official: [],
      study: [],
      web: [],
    };

    for (const item of visibleItems) {
      groups[classifyGroup(item)].push(item);
    }

    const ordered: Array<{ key: GroupKey; items: ResearchItem[] }> = [
      { key: 'case-law', items: groups['case-law'] },
      { key: 'acts', items: groups.acts },
      { key: 'official', items: groups.official },
      { key: 'study', items: groups.study },
      { key: 'web', items: groups.web },
    ];

    return ordered.filter((g) => g.items.length > 0);
  }, [visibleItems]);

  const handlePreview = async (e: React.MouseEvent, item: ResearchItem) => {
    e.stopPropagation();
    if (!item.url) return;

    setSelectedPreviewItem(item);

    const cached = previewCacheRef.current.get(item.url);
    if (cached?.kind === 'ok') {
      setPreviewState({ status: 'ok', url: item.url, data: cached.data });
      return;
    }
    if (cached?.kind === 'error') {
      setPreviewState({ status: 'error', url: item.url, message: cached.message });
      return;
    }

    setPreviewState({ status: 'loading', url: item.url });
    try {
      const res = await fetch('/api/v1/research/sources/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: item.url }),
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `Preview error: ${res.status}`);
      }
      const data = (await res.json()) as SourcePreview;
      if (data?.error) {
        previewCacheRef.current.set(item.url, { kind: 'error', message: data.error });
        setPreviewState({ status: 'error', url: item.url, message: data.error });
        return;
      }

      previewCacheRef.current.set(item.url, { kind: 'ok', data });
      setPreviewState({ status: 'ok', url: item.url, data });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Preview failed';
      previewCacheRef.current.set(item.url, { kind: 'error', message });
      setPreviewState({ status: 'error', url: item.url, message });
    }
  };

  if (!props.isOpen) return null;

  return (
    <div className="fixed top-20 bottom-4 left-4 right-4 sm:left-28 sm:right-auto sm:top-8 sm:bottom-8 sm:w-96 z-40 flex flex-col overflow-hidden glass-panel rounded-2xl border border-white/10 shadow-2xl animate-fade-in-left">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10 bg-legal-surface/60">
        <div className="flex items-center gap-2">
          <BookOpen className="text-legal-gold" size={18} />
          <h3 className="text-sm font-bold text-legal-text font-serif">Research Library</h3>
        </div>
        <button
          onClick={props.onClose}
          className="text-slate-400 hover:text-legal-text transition-colors"
          title="Close Research Panel"
        >
          <X size={18} />
        </button>
      </div>

      {/* Search Controls */}
      <div className="p-5 space-y-3 border-b border-white/10 bg-legal-surface/40">
        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
          <input
            type="text"
            placeholder="Search legal resources..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setShowHistory(true)}
            onBlur={() => setTimeout(() => setShowHistory(false), 200)}
            className="w-full pl-9 pr-8 py-2 bg-black/30 border border-white/10 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:border-legal-gold/50 focus:ring-1 focus:ring-legal-gold/20 outline-none transition-all"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
              title="Clear search"
            >
              <X size={14} />
            </button>
          )}
          
          {/* Search History Dropdown */}
          {showHistory && searchHistory.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-legal-surface border border-white/10 rounded-lg shadow-xl z-50 overflow-hidden">
              <div className="px-3 py-2 text-[10px] text-slate-500 border-b border-white/10">Recent Searches</div>
              {searchHistory.map((h, idx) => (
                <div key={idx} className="flex items-center gap-2 px-3 py-2 hover:bg-white/5 transition-colors group">
                  <button
                    onClick={() => setQuery(h)}
                    className="flex-1 text-left text-xs text-slate-300 flex items-center gap-2"
                  >
                    <Clock size={12} className="text-slate-500 flex-shrink-0" />
                    <span className="truncate">{h}</span>
                  </button>
                  <button
                    onClick={(e) => removeFromHistory(e, h)}
                    className="p-1 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                    title="Remove from history"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Category Pills */}
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          {[
            { id: 'all', label: 'All Sources' },
            { id: 'case-law', label: 'Case Law' },
            { id: 'acts', label: 'Acts & Rules' },
            { id: 'official', label: 'Official Sources' },
            { id: 'study', label: 'Study Material' }
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setCategory(cat.id as Category)}
              className={`px-3 py-1 rounded-full text-[10px] font-medium whitespace-nowrap transition-all ${
                category === cat.id
                  ? 'bg-legal-gold/20 text-legal-gold border border-legal-gold/30 shadow-lg shadow-legal-gold/10'
                  : 'bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Result Count */}
        {!isLoading && items.length > 0 && (
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-slate-500">
              {displayLimit < items.length ? (
                <>
                  Showing <span className="text-legal-gold font-semibold">{displayLimit}</span> of <span className="text-legal-gold font-semibold">{totalCount}</span> result{totalCount === 1 ? '' : 's'}
                </>
              ) : (
                <>
                  Found <span className="text-legal-gold font-semibold">{totalCount}</span> result{totalCount === 1 ? '' : 's'}
                  {searchTimeMs > 0 && <span className="text-slate-600 ml-1">({(searchTimeMs / 1000).toFixed(2)}s)</span>}
                </>
              )}
            </span>
            {query && (
              <span className="text-slate-600">for "{query}"</span>
            )}
          </div>
        )}
      </div>

      {/* Results Area */}
      <div className="flex-1 overflow-y-auto p-5">
        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="w-12 h-12 border-4 border-legal-gold/20 border-t-legal-gold rounded-full animate-spin" />
                <div className="absolute inset-0 w-12 h-12 border-4 border-transparent border-b-legal-gold/40 rounded-full animate-spin reverse-spin" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-legal-text mb-1">
                  {query ? 'Searching the Internet...' : 'Loading Sources...'}
                </p>
                <p className="text-[11px] text-slate-500">
                  {query ? `Finding results for "${query}"` : 'Scanning legal databases...'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {loadError && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 px-4">
            <AlertTriangle className="text-red-400 mb-3" size={32} />
            <p className="text-xs text-red-300 text-center mb-2">Search Error</p>
            <p className="text-[11px] text-slate-400 text-center">{loadError}</p>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !loadError && items.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 px-6">
            <div className="w-16 h-16 rounded-full bg-legal-gold/10 border border-legal-gold/20 flex items-center justify-center mb-4">
              <Search className="text-legal-gold" size={28} />
            </div>
            <p className="text-sm font-medium text-slate-300 text-center mb-2">
              {query ? 'No Results Found' : 'Search the Internet'}
            </p>
            <p className="text-[11px] text-slate-500 text-center leading-relaxed max-w-xs">
              {query 
                ? `No results found for "${query}". Try different keywords or broader terms.`
                : 'Type anything to search the web — cases, laws, legal topics, definitions, news and more.'}
            </p>
            {!query && (
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {['IPC Section 302', 'how to file FIR', 'bail conditions India', 'Article 21 RTL', 'consumer complaint process'].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setQuery(suggestion)}
                    className="px-3 py-1.5 text-[10px] bg-white/5 border border-white/10 rounded-full text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 hover:bg-white/10 transition-all"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Results Grid */}
        {!isLoading && items.length > 0 && (
          <div className="space-y-5">
            {groupedResults.map((group) => (
              <section key={group.key} className="space-y-3">
                <div className="px-1">
                  <h4 className="text-[11px] uppercase tracking-wider text-legal-gold font-semibold">
                    {GROUP_META[group.key].label}
                  </h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    {GROUP_META[group.key].hint} · {group.items.length} result{group.items.length === 1 ? '' : 's'}
                  </p>
                </div>

                <div className="space-y-3">
                  {group.items.map((item) => {
              const citCheck = citationChecks[item.id];
              const isBookmarked = bookmarks.has(item.id);

              return (
                <div
                  key={item.id}
                  className="w-full text-left bg-gradient-to-br from-legal-surface/40 to-legal-surface/20 border border-white/5 rounded-xl p-4 hover:border-legal-gold/30 hover:from-legal-surface/60 hover:to-legal-surface/40 hover:shadow-lg hover:shadow-legal-gold/5 transition-all duration-200 group relative"
                >
                  {/* Bookmark Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleBookmark(item.id);
                    }}
                    className="absolute top-3 right-3 text-slate-600 hover:text-legal-gold transition-colors z-10"
                    title={isBookmarked ? "Remove Bookmark" : "Add Bookmark"}
                  >
                    {isBookmarked ? (
                      <Bookmark size={14} fill="currentColor" className="text-legal-gold" />
                    ) : (
                      <BookOpen size={14} />
                    )}
                  </button>

                  {/* Badges */}
                  <div className="flex justify-between items-start mb-3 pr-6">
                    <div className="flex items-center gap-2 flex-wrap">
                      {/* Type Badge */}
                      <span
                        className={`text-[10px] px-2 py-1 rounded-md font-medium border ${
                          item.type === 'Act'
                            ? 'text-green-400 border-green-400/30 bg-green-400/10'
                            : item.type === 'Precedent'
                            ? 'text-blue-400 border-blue-400/30 bg-blue-400/10'
                            : item.type === 'Study'
                            ? 'text-purple-400 border-purple-400/30 bg-purple-400/10'
                            : item.type === 'Web'
                            ? 'text-orange-400 border-orange-400/30 bg-orange-400/10'
                            : 'text-yellow-400 border-yellow-400/30 bg-yellow-400/10'
                        }`}
                      >
                        {item.type === 'Precedent' ? 'Case Law' : 
                         item.type === 'Act' ? 'Act' : 
                         item.type === 'Study' ? 'Study' :
                         item.type === 'Web' ? 'Web' :
                         item.type || 'Resource'}
                      </span>

                      {/* Authority Badge */}
                      {item.authority === 'official' && (
                        <span
                          className="text-[10px] px-2 py-1 rounded-md font-medium border text-emerald-300 border-emerald-500/30 bg-emerald-500/10 flex items-center gap-1"
                          title="Official Government Source"
                        >
                          <span className="text-[11px]">🏛️</span>
                          OFFICIAL
                        </span>
                      )}
                      {item.authority === 'web' && item.tags?.includes('live_search') && (
                        <span
                          className="text-[10px] px-2 py-1 rounded-md font-medium border text-orange-300 border-orange-500/30 bg-orange-500/10 flex items-center gap-1"
                          title="Live Internet Result"
                        >
                          <span className="text-[11px]">🌐</span>
                          WEB
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Content - Draggable */}
                  <div
                    className="cursor-grab active:cursor-grabbing mb-3"
                    onMouseDown={(e) => props.onDragStart(e, item)}
                  >
                    <h4 className="text-sm font-bold text-legal-text mb-1 font-serif leading-tight pr-4 group-hover:text-legal-gold transition-colors">
                      {sanitizeTitle(item.title) || 'Untitled Resource'}
                    </h4>
                    {/* URL shown below title, like Google */}
                    {item.url && (
                      <p className="text-[10px] text-legal-gold/50 mb-2 truncate">
                        {item.url.replace(/^https?:\/\//, '')}
                      </p>
                    )}
                    {item.summary && (
                      <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                        {item.summary}
                      </p>
                    )}
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between gap-2 text-[10px] text-slate-500 pt-3 border-t border-white/5">
                    {/* Source */}
                    <div className="flex items-center gap-1.5 min-w-0">
                      <ShieldAlert size={11} className="flex-shrink-0" />
                      <span className="truncate font-medium">{item.source || item.publisher || 'Legal Source'}</span>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {/* Preview */}
                      {item.url && (
                        <button
                          type="button"
                          onClick={(e) => handlePreview(e, item)}
                          className="text-[10px] px-2 py-1 rounded-md border border-white/10 bg-black/20 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 hover:bg-black/30 transition-all flex items-center gap-1 font-medium"
                        >
                          <Eye size={10} />
                          PREVIEW
                        </button>
                      )}

                      {/* Citation Check */}
                      {citCheck ? (
                        <div
                          className="text-[10px] px-2 py-1 rounded-md border border-white/10 bg-black/30 font-medium"
                          title={citCheck.message}
                        >
                          {citCheck.emoji} {citCheck.status.toUpperCase()}
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={(e) => handleCheckAuthority(e, item)}
                          disabled={checkingCitation === item.id}
                          className="text-[10px] px-2 py-1 rounded-md border border-white/10 bg-black/20 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 hover:bg-black/30 transition-all disabled:opacity-50 font-medium"
                        >
                          {checkingCitation === item.id ? '...' : 'VERIFY'}
                        </button>
                      )}

                      {/* Open Link */}
                      {item.url && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-[10px] px-2 py-1 rounded-md border border-white/10 bg-black/20 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 hover:bg-black/30 transition-all flex items-center gap-1 font-medium"
                        >
                          <ExternalLink size={10} />
                          OPEN
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              );
                  })}
                </div>
              </section>
            ))}
            
            {/* Show More Button */}
            {items.length > displayLimit && (
              <div className="flex justify-center pt-4 pb-2">
                <button
                  onClick={() => {
                    const newLimit = displayLimit + 50;
                    setDisplayLimit(newLimit);
                    setHasMore(items.length > newLimit);
                  }}
                  className="px-6 py-2.5 rounded-lg bg-legal-gold/10 border border-legal-gold/30 text-legal-gold hover:bg-legal-gold/20 hover:border-legal-gold/50 transition-all duration-200 text-sm font-medium shadow-lg shadow-legal-gold/5 hover:shadow-legal-gold/10"
                >
                  Show More ({items.length - displayLimit} remaining)
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer with Info */}
      <div className="p-3 border-t border-white/10 bg-legal-surface/60">
        <p className="text-[10px] text-slate-500 text-center">
          🌐 Searches the internet · Drag any result to insert into analysis
        </p>
      </div>

      {/* Preview Modal */}
      {selectedPreviewItem && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-[1px] z-[60] flex items-center justify-center p-4">
          <div className="w-full max-w-3xl max-h-[85vh] bg-slate-950 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            <div className="p-4 border-b border-white/10 flex items-start justify-between gap-3 bg-white/5">
              <div className="min-w-0">
                <h4 className="text-sm font-semibold text-slate-100 truncate">{selectedPreviewItem.title}</h4>
                {selectedPreviewItem.url && (
                  <p className="text-[11px] text-legal-gold/70 truncate mt-1">
                    {selectedPreviewItem.url.replace(/^https?:\/\//, '')}
                  </p>
                )}
              </div>
              <button
                onClick={() => {
                  setSelectedPreviewItem(null);
                  setPreviewState({ status: 'idle' });
                }}
                className="text-slate-400 hover:text-white transition-colors"
                title="Close Preview"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4">
              {previewState.status === 'loading' && selectedPreviewItem.url === previewState.url && (
                <div className="py-12 flex flex-col items-center gap-2 text-slate-400">
                  <Loader2 size={20} className="animate-spin" />
                  <p className="text-sm">Fetching preview and extracting key content...</p>
                </div>
              )}

              {previewState.status === 'error' && selectedPreviewItem.url === previewState.url && (
                <div className="p-4 rounded-lg border border-red-500/20 bg-red-500/10 text-red-200 text-sm">
                  {previewState.message}
                </div>
              )}

              {previewState.status === 'ok' && selectedPreviewItem.url === previewState.url && (
                <>
                  {previewState.data.summary_ai && (
                    <div className="p-4 rounded-lg border border-legal-gold/20 bg-legal-gold/10">
                      <h5 className="text-xs font-bold text-legal-gold mb-2 uppercase tracking-wide">AI Summary</h5>
                      <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{previewState.data.summary_ai}</p>
                    </div>
                  )}

                  {previewState.data.key_points && previewState.data.key_points.length > 0 && (
                    <div className="p-4 rounded-lg border border-white/10 bg-white/5">
                      <h5 className="text-xs font-bold text-slate-300 mb-2 uppercase tracking-wide">Key Points</h5>
                      <ul className="list-disc list-inside space-y-1 text-sm text-slate-300">
                        {previewState.data.key_points.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="p-4 rounded-lg border border-white/10 bg-slate-900/70">
                    <h5 className="text-xs font-bold text-slate-300 mb-2 uppercase tracking-wide">Extracted Content</h5>
                    <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                      {previewState.data.content || 'No preview text extracted.'}
                    </p>
                  </div>
                </>
              )}
            </div>

            <div className="p-4 border-t border-white/10 bg-white/5 flex items-center justify-end gap-2">
              {selectedPreviewItem.url && (
                <a
                  href={selectedPreviewItem.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs px-3 py-1.5 rounded-md border border-white/10 bg-black/20 text-slate-300 hover:text-legal-gold hover:border-legal-gold/30 transition-all inline-flex items-center gap-1"
                >
                  <ExternalLink size={12} />
                  Open Original
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
