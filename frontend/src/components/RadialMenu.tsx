import { useEffect, useRef, useState } from 'react';
import { BrainCircuit, FileText, LogOut, Plus, Scale } from 'lucide-react';
import { LayoutIcon } from './LayoutIcon';
import type { ActiveTab, IconLike } from '../types';
import './RadialMenu.css';

const RADIAL_MENU_ITEMS: Array<{
  id: ActiveTab | 'home';
  icon: IconLike;
  label: string;
}> = [
  { id: 'dashboard', icon: LayoutIcon, label: 'Detective Wall' },
  { id: 'strategy', icon: BrainCircuit, label: 'Strategy & Analytics' },
  { id: 'drafting', icon: FileText, label: 'Drafting Studio' },
  { id: 'home', icon: LogOut, label: 'Exit Case' },
];

export function RadialMenu({ activeTab, setActiveTab, onBack }: { activeTab: ActiveTab; setActiveTab: (t: ActiveTab) => void; onBack: () => void }) {
  const [isOpen, setIsOpen] = useState(false);
  
  // Draggable state
  const [pos, setPos] = useState<{ x: number; y: number }>(() => {
    try {
      const saved = localStorage.getItem('junior:radialPos');
      if (saved) return JSON.parse(saved);
    } catch {}
    // Default to bottom-left (approximate)
    return { x: 32, y: window.innerHeight - 96 };
  });

  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0, initialX: 0, initialY: 0 });
  const hasDraggedRef = useRef(false);

  useEffect(() => {
    if (!isDragging) return;

    const handleMove = (e: MouseEvent) => {
      const dx = e.clientX - dragStartRef.current.x;
      const dy = e.clientY - dragStartRef.current.y;
      
      if (Math.abs(dx) + Math.abs(dy) > 5) {
        hasDraggedRef.current = true;
      }

      setPos({
        x: dragStartRef.current.initialX + dx,
        y: dragStartRef.current.initialY + dy
      });
    };

    const handleUp = () => {
      setIsDragging(false);
      if (hasDraggedRef.current) {
        localStorage.setItem('junior:radialPos', JSON.stringify(pos));
      }
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [isDragging, pos]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.preventDefault();
    setIsDragging(true);
    hasDraggedRef.current = false;
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      initialX: pos.x,
      initialY: pos.y
    };
  };

  // Fan layout for bottom-left corner (Quarter circle: 0 to 90 degrees)
  const positions = [
    { x: 0, y: -130 },       // 90° (Up)
    { x: 65, y: -112.5 },    // 60°
    { x: 112.5, y: -65 },    // 30°
    { x: 130, y: 0 },        // 0° (Right)
  ];

  return (
    <div
      className="radial-menu-root"
      style={{
        '--radial-x': `${pos.x}px`,
        '--radial-y': `${pos.y}px`
      } as React.CSSProperties}
    >
      {/* Menu Items */}
      <div className="absolute bottom-0 left-0 w-0 h-0">
        {RADIAL_MENU_ITEMS.map((item, idx) => {
          const itemPos = positions[idx] || { x: 0, y: 0 };
          const isVisible = isOpen;
          
          return (
            <button
              key={item.id}
              onClick={() => {
                if (item.id === 'home') {
                  onBack();
                } else {
                  setActiveTab(item.id as ActiveTab);
                }
                setIsOpen(false);
              }}
              className={`radial-menu-item glass-panel border backdrop-blur-xl shadow-xl group
                ${activeTab === item.id 
                  ? 'bg-legal-gold/20 border-legal-gold text-legal-gold shadow-glow scale-110' 
                  : 'bg-legal-surface/90 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/50 hover:scale-110'
                }
                ${isVisible ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none scale-50'}
              `}
              style={{
                '--item-x': isVisible ? `${itemPos.x}px` : '0',
                '--item-y': isVisible ? `${itemPos.y}px` : '0',
                '--item-delay': isVisible ? `${idx * 50}ms` : '0ms'
              } as React.CSSProperties}
              title={item.label}
            >
              <item.icon size={20} strokeWidth={2.5} />
              {/* Label */}
              <span className={`absolute left-1/2 -translate-x-1/2 -bottom-8 px-2 py-1 text-[10px] font-bold uppercase tracking-wider bg-legal-surface/90 border border-white/10 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50`}>
                {item.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Main Toggle Button */}
      <button
        onMouseDown={handleMouseDown}
        onClick={() => {
          if (!hasDraggedRef.current) {
            setIsOpen(!isOpen);
          }
        }}
        className={`relative z-10 flex items-center justify-center w-16 h-16 rounded-full glass-panel border-2 shadow-2xl transition-all duration-300 group cursor-move
          ${isOpen 
            ? 'bg-legal-gold text-legal-surface border-legal-gold rotate-45 scale-110 shadow-glow' 
            : 'bg-legal-surface/90 text-legal-gold border-legal-gold/50 hover:border-legal-gold hover:scale-105'
          }`}
      >
        {isOpen ? <Plus size={32} strokeWidth={3} /> : <Scale size={32} strokeWidth={2.5} />}
        
        {/* Orb Glow Effect */}
        {!isOpen && (
          <span className="absolute inset-0 rounded-full bg-legal-gold/20 animate-pulse"></span>
        )}
      </button>
    </div>
  );
}
