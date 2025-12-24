import { ChevronRight } from 'lucide-react';

export function LandingPage(props: { onEnter: () => void }) {
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
