import React, { useEffect, useState } from 'react';
import './ResearchPanel.css';
import {
  AlertTriangle,
  BookOpen,
  Search,
  ShieldAlert,
  X,
  Clock,
  Bookmark,
  ExternalLink
} from 'lucide-react';

export type ResearchItem = {
  id: string;
  title: string;
  type: string;
  summary?: string;
  source?: string;
  url?: string;
  publisher?: string;
  authority?: 'official' | 'study' | string;
  tags?: string[];
  size?: string;
  date?: string;
};

type Category = 'all' | 'case-law' | 'acts' | 'official' | 'study';

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

  // UI State
  const [bookmarks, setBookmarks] = useState<Set<string>>(new Set());
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [citationChecks, setCitationChecks] = useState<Record<string, { status: string; emoji: string; message: string }>>({});
  const [checkingCitation, setCheckingCitation] = useState<string | null>(null);

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
                <button
                  key={idx}
                  onClick={() => setQuery(h)}
                  className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:bg-white/5 transition-colors flex items-center gap-2"
                >
                  <Clock size={12} className="text-slate-500" />
                  {h}
                </button>
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
                  Showing <span className="text-legal-gold font-semibold">{displayLimit}</span> of <span className="text-legal-gold font-semibold">{items.length}</span> result{items.length === 1 ? '' : 's'}
                </>
              ) : (
                <>
                  Found <span className="text-legal-gold font-semibold">{items.length}</span> resource{items.length === 1 ? '' : 's'}
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
                <p className="text-sm font-medium text-legal-text mb-1">Searching Legal Sources</p>
                <p className="text-[11px] text-slate-500">Scanning databases & case law...</p>
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
              {query ? 'No Results Found' : 'Start Your Legal Research'}
            </p>
            <p className="text-[11px] text-slate-500 text-center leading-relaxed max-w-xs">
              {query 
                ? 'Try different keywords or check spelling. We search across official Indian legal databases.'
                : 'Search for cases, acts, judgments, or legal topics from trusted Indian legal sources.'}
            </p>
            {!query && (
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {['IPC Section 302', 'Contract Act', 'Supreme Court', 'Article 21'].map((suggestion) => (
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
          <div className="space-y-3">
            {items.slice(0, displayLimit).map((item) => {
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
                            : 'text-yellow-400 border-yellow-400/30 bg-yellow-400/10'
                        }`}
                      >
                        {item.type === 'Precedent' ? 'Case Law' : 
                         item.type === 'Act' ? 'Act' : 
                         item.type === 'Study' ? 'Study' :
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
                    </div>
                  </div>

                  {/* Content - Draggable */}
                  <div
                    className="cursor-grab active:cursor-grabbing mb-3"
                    onMouseDown={(e) => props.onDragStart(e, item)}
                  >
                    <h4 className="text-sm font-bold text-legal-text mb-2 font-serif leading-tight pr-4 group-hover:text-legal-gold transition-colors">
                      {item.title || 'Untitled Resource'}
                    </h4>
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
          💡 Drag any resource to insert into your case analysis
        </p>
      </div>
    </div>
  );
}
