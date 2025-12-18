import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  BrainCircuit,
  ChevronRight,
  Clock,
  Eraser,
  FileText,
  Gavel,
  GripVertical,
  Home,
  LogOut,
  MessageSquare,
  Paperclip,
  Plus,
  Scale,
  Search,
  Send,
  ShieldAlert,
  Sparkles,
  Trash2,
  Upload,
  X,
} from 'lucide-react';

type View = 'landing' | 'selection' | 'wall';
type ActiveTab = 'dashboard' | 'strategy' | 'drafting';
type ToolId = 'research' | 'vault' | 'remove' | null;

type AnalyticsMode = 'judge' | 'devils';

type DevilsAdvocateAttackPoint = {
  title?: string;
  weakness?: string;
  counter_citation?: string;
  suggested_attack?: string;
  raw?: string;
};

type DevilsAdvocateResponse = {
  attack_points: DevilsAdvocateAttackPoint[];
  vulnerability_score: number;
  preparation_recommendations: string[];
};

type CaseData = {
  id: number;
  title: string;
  type: string;
  date: string;
  status: string;
};

type ResearchItem = {
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

type NodeStatus = 'Verified' | 'Pending' | 'Contested';
type NodeType = 'Evidence' | 'Precedent' | 'Statement' | 'Strategy';

type NodeData = {
  id: number;
  title: string;
  type: NodeType;
  date: string;
  status: NodeStatus;
  x: number;
  y: number;
  rotation: number;
  pinColor: 'red' | 'blue' | 'green' | 'yellow';
  source?: string;
  attachments?: Array<{
    name: string;
    kind: 'photo' | 'video' | 'audio' | 'document' | 'other';
    sizeBytes?: number;
  }>;
};

type Connection = {
  from: number;
  to: number;
  label: string;
  type: 'conflict' | 'normal' | 'suggested';
  reason?: string;
  confidence?: number;
};

type WallInsightSeverity = 'low' | 'medium' | 'high';

type WallAnalyzeResponse = {
  summary: string;
  insights: Array<{ title: string; detail: string; severity: WallInsightSeverity; node_ids: string[] }>;
  suggested_links: Array<{ source: string; target: string; label: string; confidence: number; reason?: string }>;
  next_actions: string[];
};

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
  hasConflict?: boolean;
  conflictDetail?: string;
};

type IconLike = React.ComponentType<{ size?: string | number; strokeWidth?: string | number }>;

type CourtValue =
  | 'supreme_court'
  | 'high_court'
  | 'district_court'
  | 'tribunal'
  | 'other';

type DocumentTemplate = {
  id: string;
  name: string;
  description: string;
};

type FormattingRules = {
  court: string;
  font_family: string;
  font_size: number;
  line_spacing: number;
  margins: { top: number; bottom: number; left: number; right: number };
  paragraph_indent: number;
  page_numbering: string;
};

type ShepardizeStatus = 'good_law' | 'distinguished' | 'overruled' | 'unknown';
type ShepardizeResult = {
  status: ShepardizeStatus;
  status_emoji?: string;
  message?: string;
};

const RADIAL_MENU_ITEMS: Array<{
  id: ActiveTab | 'home';
  icon: IconLike;
function Sidebar({ activeTab, setActiveTab, onBack }: { activeTab: ActiveTab; setActiveTab: (t: ActiveTab) => void; onBack: () => void }) {
  const tabs: { id: ActiveTab; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Detective Wall', icon: <LayoutIcon size={18} /> },
    { id: 'strategy', label: 'Strategy & Analytics', icon: <BrainCircuit size={18} /> },
    { id: 'drafting', label: 'Drafting Studio', icon: <FileText size={18} /> },
  ];

  return (
    <div className="w-64 bg-legal-surface/80 backdrop-blur-xl border-r border-white/10 flex flex-col z-50 h-screen shrink-0">
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3 text-legal-gold">
          <Scale size={24} />
          <span className="font-serif text-xl font-bold tracking-wide">ZeroDay</span>
        </div>
      </div>

      <div className="flex-1 py-6 px-3 space-y-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-300 ${
              activeTab === tab.id
                ? 'bg-legal-gold/10 text-legal-gold border border-legal-gold/20 shadow-glow'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="p-4 border-t border-white/10">
        <button
          onClick={onBack}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-colors"
        >
          <LogOut size={18} />
          <span>Exit Case</span>
        </button>
      </div>
    </div>
  );
}

function ToolsDock(props: {
  isOpen: boolean;
  activeTool: ToolId;
  setActiveTool: (tool: ToolId) => void;
  onToggleRemove: () => void;
  isRemoveMode: boolean;
}) {
  if (!props.isOpen) return null;

  const tools = [
    { id: 'research' as const, icon: Search, label: 'Research' },
    { id: 'vault' as const, icon: ShieldAlert, label: 'Vault' },
    { id: 'remove' as const, icon: Eraser, label: 'Remove' },
  ];

  return (
    <div className="fixed top-20 left-4 right-4 sm:left-40 sm:right-auto sm:top-24 z-40 flex flex-wrap gap-2 max-w-[calc(100vw-2rem)] sm:max-w-none animate-fade-in-left">
      {tools.map((tool) => (
        <button
          key={tool.id}
          onClick={() => {
            if (tool.id === 'remove') {
              props.onToggleRemove();
            } else {
              props.setActiveTool(tool.id);
            }
          }}
          className={`flex items-center gap-2 px-4 py-2 rounded-full border backdrop-blur-md shadow-lg transition-all duration-200
            ${
              tool.id === 'remove' && props.isRemoveMode
                ? 'bg-rose-500/20 border-rose-500 text-rose-400'
                : props.activeTool === tool.id
                  ? 'bg-amber-500 text-slate-900 border-amber-400'
                  : 'bg-black/40 border-white/10 text-slate-400 hover:bg-white/10 hover:text-white hover:border-white/20'
            }`}
        >
          <tool.icon size={16} />
          <span className="text-xs font-bold uppercase tracking-wider">{tool.label}</span>
        </button>
      ))}
    </div>
  );
}

function VaultPanel(props: {
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

function DocumentNode(props: {
  id: number;
  title: string;
  type: NodeType;
  date: string;
  status: NodeStatus;
  x: number;
  y: number;
  rotation: number;
  pinColor: NodeData['pinColor'];
  onDrag: (id: number, pos: { x: number; y: number }) => void;
  onDelete: (id: number) => void;
  isSelected: boolean;
  onSelect: (id: number | null) => void;
  scale: number;
  isRemoveMode: boolean;
  insightSeverity?: WallInsightSeverity;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, initialX: 0, initialY: 0 });
  const nodeRef = useRef<HTMLDivElement | null>(null);

  const statusColors: Record<NodeStatus, string> = {
    Verified: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
    Pending: 'text-legal-gold bg-legal-gold/10 border-legal-gold/20',
    Contested: 'text-rose-400 bg-rose-400/10 border-rose-400/20',
  };

  const typeIcons: Record<NodeType, IconLike> = {
    Evidence: FileText,
    Precedent: BookOpen,
    Statement: MessageSquare,
    Strategy: Gavel,
  };

  const Icon = typeIcons[props.type] ?? FileText;

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (props.isRemoveMode) {
      e.stopPropagation();
      props.onDelete(props.id);
      return;
    }

    const target = e.target as HTMLElement | null;
    if (target?.closest('button')) return;

    e.stopPropagation();
    setIsDragging(true);
    props.onSelect(props.id);
    dragStart.current = {
      x: e.clientX,
      y: e.clientY,
      initialX: props.x,
      initialY: props.y,
    };
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const dx = (e.clientX - dragStart.current.x) / props.scale;
      const dy = (e.clientY - dragStart.current.y) / props.scale;
      props.onDrag(props.id, { x: dragStart.current.initialX + dx, y: dragStart.current.initialY + dy });
    };
    const handleMouseUp = () => setIsDragging(false);

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, props]);

  useEffect(() => {
    const el = nodeRef.current;
    if (!el) return;
    el.style.left = `${props.x}px`;
    el.style.top = `${props.y}px`;
    el.style.transform = `rotate(${props.rotation}deg)`;
  }, [props.rotation, props.x, props.y]);

  const cursorClass = props.isRemoveMode ? 'cursor-crosshair' : isDragging ? 'cursor-grabbing' : 'cursor-grab';
  const zClass = isDragging ? 'z-50' : props.isSelected ? 'z-40' : 'z-10';

  const insightBorderClass = (() => {
    if (!props.insightSeverity) return '';
    if (props.insightSeverity === 'high') return 'border-rose-500/50 shadow-[0_0_30px_rgba(244,63,94,0.10)]';
    if (props.insightSeverity === 'medium') return 'border-legal-gold/40 shadow-[0_0_30px_rgba(212,175,55,0.08)]';
    return 'border-emerald-400/25 shadow-[0_0_30px_rgba(52,211,153,0.06)]';
  })();

  return (
    <div
      ref={nodeRef}
      className={`absolute w-80 group select-none ${zClass} ${cursorClass}`}
      onMouseDown={handleMouseDown}
      role="group"
      aria-label={`${props.title} node`}
    >
      <div
        className={`relative ${
          isDragging ? 'scale-105 transition-none shadow-2xl' : 'transition-all duration-300 ease-out hover:scale-[1.02]'
        } ${props.isRemoveMode ? 'hover:opacity-50 hover:scale-95' : ''}`}
      >
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-20">
          <div
            className={`w-3 h-3 rounded-full shadow-[0_0_10px_rgba(0,0,0,0.5)] ${
              props.pinColor === 'red'
                ? 'bg-rose-500'
                : props.pinColor === 'blue'
                  ? 'bg-blue-500'
                  : props.pinColor === 'green'
                    ? 'bg-emerald-500'
                    : 'bg-legal-gold'
            }`}
          />
        </div>
        <div
          className={`glass-panel border rounded-xl overflow-hidden transition-all duration-300 ${
            props.isSelected
              ? 'border-legal-gold/50 shadow-[0_0_30px_rgba(212,175,55,0.1)]'
              : `border-white/5 hover:border-white/10 shadow-xl ${insightBorderClass}`
          } ${props.isRemoveMode ? 'group-hover:border-rose-500 group-hover:bg-rose-950/30' : ''}`}
        >
          <div className="p-5">
          <div className="flex justify-between items-start mb-4">
            <div
              className={`text-[10px] font-semibold uppercase tracking-widest px-3 py-1 rounded-full border ${
                statusColors[props.status]
              }`}
            >
              {props.status}
            </div>
            {!props.isRemoveMode && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  props.onDelete(props.id);
                }}
                title="Delete"
                aria-label="Delete"
                className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-500 hover:text-rose-400"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
          <div className="flex items-start gap-4 mb-4">
            <div className="p-3 bg-white/5 rounded-xl text-slate-400">
              <Icon size={20} strokeWidth={1.5} />
            </div>
            <div className="flex-1 min-w-0 pt-1">
              <h4 className="text-base font-medium text-legal-text leading-tight mb-1 font-serif truncate">{props.title}</h4>
              <span className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">{props.type}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-slate-600 border-t border-white/5 pt-3 font-mono">
            <Clock size={12} />
            <span>FILED: {props.date}</span>
          </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ConnectionLine(props: {
  start: { x: number; y: number };
  end: { x: number; y: number };
  label: string;
  type: 'conflict' | 'normal' | 'suggested';
  reason?: string;
}) {
  const strokeColor = props.type === 'conflict' ? '#f43f5e' : props.type === 'suggested' ? '#D4AF37' : '#64748b';
  const startX = props.start.x + 160;
  const startY = props.start.y + 60;
  const endX = props.end.x + 160;
  const endY = props.end.y + 60;
  const midX = (startX + endX) / 2;
  const midY = (startY + endY) / 2;
  const controlY = midY - 30;

  return (
    <svg className="absolute top-0 left-0 w-full h-full z-0 overflow-visible pointer-events-none">
      <path
        d={`M ${startX} ${startY} Q ${midX} ${controlY}, ${endX} ${endY}`}
        stroke={strokeColor}
        strokeWidth={props.type === 'conflict' ? 2 : 1.5}
        strokeDasharray={props.type === 'suggested' ? '6 6' : undefined}
        fill="none"
      />
      <foreignObject
        x={midX - 45}
        y={controlY - 14}
        width="90"
        height="28"
        className="pointer-events-auto"
      >
        <div
          className={`pointer-events-auto ${props.reason ? 'cursor-help' : ''} text-[10px] font-bold text-center px-2 py-1 rounded-full shadow-lg border backdrop-blur-sm ${
            props.type === 'conflict'
              ? 'bg-rose-950/90 text-rose-400 border-rose-700'
              : props.type === 'suggested'
                ? 'bg-legal-gold/20 text-legal-gold border-legal-gold/40'
              : 'bg-legal-surface/90 text-slate-400 border-white/10'
          }`}
          title={props.reason || props.label}
        >
          {props.label}
        </div>
      </foreignObject>
    </svg>
  );
}

function NodeDetailsPanel(props: {
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
                  <span className="text-[10px] text-slate-400 font-mono">{a.kind.toUpperCase()}</span>
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

function ChatPanel(props: {
  isOpen: boolean;
  toggleChat: () => void;
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [props.messages]);

  const handleSend = () => {
    if (inputValue.trim() && !props.isLoading) {
      props.onSendMessage(inputValue);
      setInputValue('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!props.isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-full sm:w-[400px] glass-panel border-l border-white/10 flex flex-col z-50 shadow-2xl">
      <div className="p-5 border-b border-white/10 flex justify-between items-center bg-legal-surface/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-legal-gold/20 rounded-xl flex items-center justify-center border border-legal-gold/30 shadow-glow">
            <Scale size={20} className="text-legal-gold" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-legal-text font-serif tracking-wide">Junior AI</h3>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.6)]"></span>
              <span className="text-[10px] text-emerald-400 font-medium tracking-wider uppercase">Online</span>
            </div>
          </div>
        </div>
        <button
          onClick={props.toggleChat}
          className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
          title="Close"
          aria-label="Close"
        >
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {props.messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div
              className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center mt-1 shadow-md border ${
                msg.role === 'user'
                  ? 'bg-slate-800 text-xs text-slate-300 border-slate-600'
                  : 'bg-legal-gold/10 border-legal-gold/30'
              }`}
            >
              {msg.role === 'user' ? 'YOU' : <span className="text-legal-gold font-bold text-xs font-serif">J</span>}
            </div>
            <div className={`max-w-[85%] ${msg.role === 'user' ? 'text-right' : ''}`}>
              <div
                className={`p-4 rounded-2xl text-sm shadow-lg backdrop-blur-sm ${
                  msg.role === 'user'
                    ? 'bg-legal-surface border border-white/10 text-slate-200 rounded-tr-none'
                    : 'bg-legal-surface/60 border border-white/5 text-slate-300 rounded-tl-none'
                }`}
              >
                {msg.role === 'assistant' && msg.hasConflict && (
                  <div className="bg-rose-950/30 p-3 rounded-lg border border-rose-500/20 mb-3">
                    <div className="flex items-start gap-2">
                      <AlertTriangle size={14} className="text-rose-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <span className="text-xs font-bold text-rose-400 uppercase tracking-wide block mb-1">
                          Conflict Detected
                        </span>
                        <p className="text-xs text-rose-200/80 leading-relaxed">{msg.conflictDetail}</p>
                      </div>
                    </div>
                  </div>
                )}
                <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          </div>
        ))}

        {props.isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 bg-legal-gold/10 border border-legal-gold/30 rounded-full flex-shrink-0 flex items-center justify-center shadow-md">
              <span className="text-legal-gold font-bold text-xs font-serif">J</span>
            </div>
            <div className="bg-legal-surface/60 border border-white/5 p-4 rounded-2xl rounded-tl-none">
              <div className="flex items-center gap-2 text-xs text-slate-400 mb-2">
                <Sparkles size={14} className="animate-spin text-legal-gold" />
                <span className="text-legal-gold">Analyzing case files...</span>
              </div>
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 bg-legal-gold rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-1.5 h-1.5 bg-legal-gold rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-1.5 h-1.5 bg-legal-gold rounded-full animate-bounce"></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-5 border-t border-white/10 bg-legal-surface/80 backdrop-blur-md">
        <div className="relative group">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask Junior to research, draft, or analyze..."
            className="w-full bg-black/20 border border-white/10 rounded-xl pl-4 pr-28 py-4 text-sm text-slate-200 focus:outline-none focus:border-legal-gold/50 transition-all shadow-inner placeholder-slate-500 glass-input"
            disabled={props.isLoading}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            <button className="p-2 text-slate-500 hover:text-legal-gold transition-colors rounded-lg hover:bg-white/5" title="Attach" aria-label="Attach">
              <Paperclip size={18} />
            </button>
            <button
              onClick={handleSend}
              disabled={props.isLoading || !inputValue.trim()}
              className="p-2 bg-legal-gold/10 text-legal-gold hover:bg-legal-gold/20 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed border border-legal-gold/20"
              title="Send"
              aria-label="Send"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
        <div className="flex justify-between items-center mt-3 px-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-500 font-bold tracking-wider">BRAIN:</span>
            <span className="text-[10px] bg-black/30 text-slate-400 px-2 py-0.5 rounded border border-white/10 font-mono">
              Llama 3.3
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
            <ShieldAlert size={10} />
            <span className="font-medium">DPDP SAFE</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function LandingPage(props: { onEnter: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen w-full text-legal-text relative overflow-hidden px-4 bg-legal-bg">
      <div className="absolute inset-0 container-bg z-0 opacity-50"></div>
      <div className="z-10 flex flex-col items-center animate-fade-in-up">
        <div className="w-24 h-24 bg-legal-gold/20 border border-legal-gold/30 rounded-3xl flex items-center justify-center text-legal-gold font-bold text-5xl font-serif shadow-glow mb-8">
          J
        </div>
        <h1 className="text-6xl font-bold font-serif mb-4 tracking-tight text-legal-text">Junior AI</h1>
        <p className="text-slate-400 text-lg mb-12 tracking-wide font-light">Your Intelligent Legal Assistant</p>
        <button
          onClick={props.onEnter}
          className="group relative px-8 py-4 bg-legal-surface hover:bg-legal-surface/80 text-legal-text rounded-full border border-white/10 hover:border-legal-gold/50 transition-all duration-300 shadow-lg hover:shadow-legal-gold/20 flex items-center gap-3"
        >
          <span className="font-medium tracking-wider">ACCESS CASE FILES</span>
          <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform text-legal-gold" />
        </button>
      </div>
    </div>
  );
}

function CaseSelection(props: { onSelectCase: (c: CaseData) => void; onNewCase: () => void }) {
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

function ResearchPanel(props: {
  isOpen: boolean;
  onClose: () => void;
  onDragStart: (e: React.MouseEvent<HTMLElement>, item: ResearchItem) => void;
}) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<'all' | 'Official' | 'Study' | 'Law' | 'Precedent' | 'Act' | 'Constitution'>('all');
  const [items, setItems] = useState<ResearchItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Fallback list if backend is unavailable.
  const fallback: ResearchItem[] = [
    { id: 'fallback_india_code', title: 'India Code', type: 'Official', summary: 'Central Acts/Rules/Regulations (official).', source: 'Legislative Department', url: 'https://www.indiacode.nic.in/', authority: 'official' },
    { id: 'fallback_egazette', title: 'e-Gazette of India', type: 'Official', summary: 'Gazette publications and notifications.', source: 'Department of Publication', url: 'https://egazette.nic.in/', authority: 'official' },
    { id: 'fallback_sci', title: 'Supreme Court — Judgments', type: 'Official', summary: 'SC judgments/orders (official portal).', source: 'Supreme Court of India', url: 'https://main.sci.gov.in/judgments', authority: 'official' },
    { id: 'fallback_ecourts', title: 'eCourts Services', type: 'Official', summary: 'Case status/orders/cause lists across courts.', source: 'eCommittee (SCI)', url: 'https://ecourts.gov.in/', authority: 'official' },
  ];

  useEffect(() => {
    if (!props.isOpen) return;

    let cancelled = false;
    const controller = new AbortController();

    const run = async () => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const res = await fetch('/api/v1/research/sources/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            category: category === 'all' ? null : category,
            authority: category === 'Official' ? 'official' : category === 'Study' ? 'study' : null,
            limit: 25,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const detail = await res.text();
          throw new Error(detail || `API error: ${res.status}`);
        }

        const data = (await res.json()) as { results?: ResearchItem[] };
        if (!cancelled) {
          setItems(Array.isArray(data.results) ? data.results : []);
        }
      } catch (e) {
        if (!cancelled && !(e instanceof DOMException && e.name === 'AbortError')) {
          setLoadError('Sources unavailable (backend not running).');
          // Keep UI useful even if backend is down.
          setItems(fallback);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    const t = window.setTimeout(() => void run(), 200);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
      controller.abort();
    };
  }, [props.isOpen, query, category]);

  const filtered = items.filter(
    (item) =>
      (category === 'all' || item.type === category || (category === 'Official' && item.authority === 'official') || (category === 'Study' && item.authority === 'study')) &&
      (item.title.toLowerCase().includes(query.toLowerCase()) || (item.summary ?? '').toLowerCase().includes(query.toLowerCase()) || (item.source ?? '').toLowerCase().includes(query.toLowerCase()))
  );

  if (!props.isOpen) return null;

  return (
    <div className="fixed left-4 right-4 top-20 bottom-4 sm:left-28 sm:right-auto sm:top-8 sm:bottom-8 sm:w-80 glass-panel border border-white/10 rounded-2xl shadow-2xl flex flex-col z-40 overflow-hidden animate-fade-in-left">
      <div className="p-5 border-b border-white/10 flex justify-between items-center bg-legal-surface/50">
        <div className="flex items-center gap-2 text-legal-gold">
          <Search size={18} />
          <h3 className="font-serif font-bold text-base tracking-wide text-legal-text">Legal Research</h3>
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
            placeholder="Search acts, judgments..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-black/20 border border-white/10 rounded-lg pl-9 pr-4 py-2.5 text-xs text-slate-200 focus:border-legal-gold/50 outline-none glass-input transition-all"
          />
        </div>

        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          {(['all', 'Official', 'Study', 'Law', 'Precedent', 'Act', 'Constitution'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`px-3 py-1 rounded-full text-[10px] font-medium whitespace-nowrap transition-colors ${
                category === cat
                  ? 'bg-legal-gold/20 text-legal-gold border border-legal-gold/30'
                  : 'bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10'
              }`}
            >
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        <div className="flex items-center gap-2 text-[10px] text-slate-500 font-medium mb-2">
          <Sparkles size={10} className="text-legal-gold" />
          <span>AI RECOMMENDATIONS</span>

        </div>

        {isLoading && (
          <div className="text-xs text-slate-500">Loading sources…</div>
        )}

        {loadError && (
          <div className="text-xs text-rose-300 bg-rose-950/30 border border-rose-900/40 rounded-lg p-2">
            {loadError}
          </div>
        )}

        {filtered.map((item) => (
          <button
            type="button"
            key={item.id}
            onMouseDown={(e) => props.onDragStart(e, item)}
            className="w-full text-left bg-legal-surface/40 border border-white/5 rounded-xl p-4 cursor-grab active:cursor-grabbing hover:border-legal-gold/30 hover:bg-legal-surface/60 transition-all group select-none"
            aria-label={`Drag ${item.title}`}
          >
            <div className="flex justify-between items-start mb-1">
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded border ${
                    item.type === 'Precedent'
                      ? 'text-blue-400 border-blue-400/20 bg-blue-400/10'
                      : 'text-emerald-400 border-emerald-400/20 bg-emerald-400/10'
                  }`}
                >
                  {item.type}
                </span>
                {item.authority && (
                  <span
                    className={`text-[10px] px-1.5 py-0.5 rounded border ${
                      item.authority === 'official'
                        ? 'text-emerald-300 border-emerald-500/30 bg-emerald-500/10'
                        : 'text-legal-gold border-legal-gold/30 bg-legal-gold/10'
                    }`}
                    title={item.authority === 'official' ? 'Official source' : 'Study / manual'}
                    aria-label={item.authority === 'official' ? 'Official source' : 'Study / manual'}
                  >
                    {item.authority === 'official' ? 'OFFICIAL' : 'STUDY'}
                  </span>
                )}
              </div>
              <GripVertical size={14} className="text-slate-600 group-hover:text-slate-400" />
            </div>
            <h4 className="text-sm font-bold text-legal-text mb-1 font-serif">{item.title}</h4>
            <p className="text-[11px] text-slate-400 line-clamp-2 mb-3 leading-relaxed">{item.summary}</p>
            <div className="flex items-center justify-between gap-2 text-[10px] text-slate-500 font-mono">
              <div className="flex items-center gap-1 min-w-0">
                <ShieldAlert size={10} />
                <span className="truncate">{item.source}</span>
              </div>
              {item.url && (
                <button
                  type="button"
                  onMouseDown={(e) => {
                    e.stopPropagation();
                  }}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    window.open(item.url, '_blank', 'noopener,noreferrer');
                  }}
                  className="text-[10px] px-2 py-1 rounded-md border border-white/10 bg-black/20 text-slate-300 hover:text-legal-gold hover:border-legal-gold/30 transition-colors"
                  aria-label={`Open ${item.title}`}
                  title="Open source"
                >
                  OPEN
                </button>
              )}
            </div>
          </button>
        ))}

        {!isLoading && filtered.length === 0 && (
          <div className="text-xs text-slate-500">No sources found.</div>
        )}
      </div>
    </div>
  );
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

  const [connections, setConnections] = useState<Connection[]>([
    { from: 1, to: 2, label: 'Contradicts', type: 'conflict' },
    { from: 2, to: 3, label: 'Disproves', type: 'conflict' },
    { from: 3, to: 4, label: 'Supports', type: 'normal' },
  ]);

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

    void handleAnalyzeWall({ nodes: nextNodes, connections, silent: true });
  };

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        "Welcome! I'm Junior, your AI Legal Assistant. I've analyzed the case documents on your canvas.\n\nThere's a critical timeline discrepancy between the Witness Statement and CCTV evidence. Would you like me to draft a Discharge Petition?",
      hasConflict: true,
      conflictDetail: 'Witness A claims seeing the accused at 10:00 PM, but CCTV shows him at ATM at 10:05 PM, 5km away.',
    },
  ]);

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
          y: y - 50,
          rotation: Math.random() * 6 - 3,
          pinColor: 'blue',
          source: draggedResearchItem.item.source,
          attachments: [{ name: draggedResearchItem.item.title, kind: 'document' }],
        };

        let nextNodes: NodeData[] = [];
        setNodes((prev) => {
          nextNodes = [...prev, newNode];
          return nextNodes;
        });

        // Auto-analyze to generate links + reasons
        void handleAnalyzeWall({ nodes: nextNodes, connections, silent: true });
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
    try {
      const response = await fetch('/api/v1/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, language: 'en' }),
      });

      if (response.ok) {
        const data = (await response.json()) as { message?: { content?: string } };
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: data.message?.content || "I've processed your request." },
        ]);
      } else {
        throw new Error('API Error');
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            "I'm in demo mode. In production, I'd analyze your query against Indian case law databases with verified citations.\n\nTry asking about:\n- Discharge petition strategies\n- Timeline conflict analysis\n- Supreme Court rulings",
        },
      ]);
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
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} onBack={props.onBack} />
        <StrategyAnalytics activeCase={props.activeCase} />
      </div>
    );
  }

  if (activeTab === 'drafting') {
    return (
      <div className="flex min-h-screen w-full text-legal-text font-sans overflow-hidden relative bg-legal-bg">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} onBack={props.onBack} />
        <DraftingStudio />
      </div>
    );
  }

  return (
    <div className={`flex min-h-screen w-full text-legal-text font-sans overflow-hidden relative bg-legal-bg ${isRemoveMode ? 'cursor-crosshair' : ''}`}>
      <div className="absolute inset-0 container-bg z-0"></div>
      
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} onBack={props.onBack} />

      <div className="flex-1 relative flex flex-col h-screen overflow-hidden">
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

function LayoutIcon({ size = 20 }: { size?: string | number }) {
  // Matches the previous menu icon usage without changing UI behavior.
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect width="7" height="9" x="3" y="3" />
      <rect width="7" height="5" x="14" y="3" />
      <rect width="7" height="9" x="14" y="12" />
      <rect width="7" height="5" x="3" y="16" />
    </svg>
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
