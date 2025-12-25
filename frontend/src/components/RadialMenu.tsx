import { useState, useEffect, useRef } from 'react';
import { BrainCircuit, FileText, LogOut, Scale } from 'lucide-react';
import { LayoutIcon } from './LayoutIcon';
import type { ActiveTab } from '../types';

const RADIAL_MENU_ITEMS = [
  { id: 'dashboard', icon: LayoutIcon, label: 'Detective Wall' },
  { id: 'strategy', icon: BrainCircuit, label: 'Strategy & Analytics' },
  { id: 'drafting', icon: FileText, label: 'Drafting Studio' },
  { id: 'home', icon: LogOut, label: 'Exit Case' },
] as const;

export function RadialMenu({ 
  activeTab, 
  setActiveTab, 
  onBack 
}: { 
  activeTab: ActiveTab; 
  setActiveTab: (t: ActiveTab) => void; 
  onBack: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  
  // Draggable state
  const [pos, setPos] = useState<{ x: number; y: number }>(() => {
    try {
      const saved = localStorage.getItem('junior:radialPos');
      if (saved) return JSON.parse(saved);
    } catch {}
    return { x: 32, y: 32 };
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
    setIsDragging(true);
    hasDraggedRef.current = false;
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      initialX: pos.x,
      initialY: pos.y
    };
  };

  // Menu item positions (radial fan layout)
  const positions = [
    { x: 0, y: -120 },      // Up
    { x: 60, y: -104 },     // Up-Right
    { x: 104, y: -60 },     // Right-Up
    { x: 120, y: 0 },       // Right
  ];

  return (
    <div
      style={{
        position: 'fixed',
        left: `${pos.x}px`,
        top: `${pos.y}px`,
        zIndex: 9999,
      }}
    >
      {/* Menu Items */}
      {isOpen && RADIAL_MENU_ITEMS.map((item, idx) => {
        const itemPos = positions[idx];
        const Icon = item.icon;
        
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
            style={{
              position: 'absolute',
              left: '0',
              bottom: '0',
              transform: `translate(${itemPos.x}px, ${itemPos.y}px)`,
              transition: 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
              transitionDelay: `${idx * 50}ms`,
            }}
            className={`flex items-center justify-center w-12 h-12 rounded-full border backdrop-blur-xl shadow-xl
              ${activeTab === item.id 
                ? 'bg-amber-500/20 border-amber-500 text-amber-500' 
                : 'bg-slate-800/90 border-white/10 text-slate-400 hover:text-amber-500 hover:border-amber-500/50'
              }`}
            title={item.label}
          >
            <Icon size={20} strokeWidth={2.5} />
          </button>
        );
      })}

      {/* Main Toggle Button */}
      <button
        onMouseDown={handleMouseDown}
        onClick={() => {
          if (!hasDraggedRef.current) {
            setIsOpen(!isOpen);
          }
        }}
        style={{
          position: 'relative',
          zIndex: 10,
          cursor: isDragging ? 'grabbing' : 'grab',
        }}
        className={`flex items-center justify-center w-16 h-16 rounded-full border-2 shadow-2xl transition-all duration-300
          ${isOpen 
            ? 'bg-amber-500 text-slate-900 border-amber-500 rotate-45' 
            : 'bg-slate-800/90 text-amber-500 border-amber-500/50 hover:border-amber-500'
          }`}
      >
        <Scale size={32} strokeWidth={2.5} />
      </button>
    </div>
  );
}
