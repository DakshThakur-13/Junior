export function ConnectionLine(props: {
  start: { x: number; y: number };
  end: { x: number; y: number };
  label: string;
  type: 'conflict' | 'normal' | 'suggested';
  reason?: string;
  dimmed?: boolean;
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
    <svg
      className={`absolute top-0 left-0 w-full h-full z-0 overflow-visible pointer-events-none transition-opacity duration-200 ${
        props.dimmed ? 'opacity-20' : 'opacity-100'
      }`}
    >
      <path
        d={`M ${startX} ${startY} Q ${midX} ${controlY}, ${endX} ${endY}`}
        stroke={strokeColor}
        strokeWidth={props.type === 'conflict' ? 2 : 1.5}
        strokeDasharray={props.type === 'suggested' ? '6 6' : undefined}
        strokeOpacity={props.dimmed ? 0.35 : 1}
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
          } ${props.dimmed ? 'opacity-60' : ''}`}
          title={props.reason || props.label}
        >
          {props.label}
        </div>
      </foreignObject>
    </svg>
  );
}
