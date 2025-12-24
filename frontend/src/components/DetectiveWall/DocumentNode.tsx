import { useEffect, useRef, useState } from 'react';
import { BookOpen, Clock, FileText, Gavel, MessageSquare, Trash2 } from 'lucide-react';
import type { NodeData, NodeStatus, NodeType, WallInsightSeverity, IconLike } from '../../types';

export function DocumentNode(props: {
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
