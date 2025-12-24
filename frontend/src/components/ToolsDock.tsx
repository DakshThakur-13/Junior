import { Eraser, Search, ShieldAlert } from 'lucide-react';
import type { ToolId } from '../types';

export function ToolsDock(props: {
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
    <div className="absolute top-full right-0 mt-3 flex flex-col gap-2 min-w-[140px] animate-fade-in-down origin-top-right z-50">
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
          className={`flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl shadow-xl transition-all duration-200 text-left
            ${
              tool.id === 'remove' && props.isRemoveMode
                ? 'bg-rose-500/20 border-rose-500 text-rose-400'
                : props.activeTool === tool.id
                  ? 'bg-legal-gold text-slate-900 border-legal-gold'
                  : 'bg-legal-surface/90 border-white/10 text-slate-400 hover:bg-white/10 hover:text-white hover:border-white/20'
            }`}
        >
          <tool.icon size={16} />
          <span className="text-xs font-bold uppercase tracking-wider">{tool.label}</span>
        </button>
      ))}
    </div>
  );
}
