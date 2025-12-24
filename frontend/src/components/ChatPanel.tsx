import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Paperclip, Scale, Send, ShieldAlert, Sparkles, X } from 'lucide-react';
import type { ChatMessage } from '../types';

export function ChatPanel(props: {
  isOpen: boolean;
  toggleChat: () => void;
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  suggestActions: boolean;
  onToggleSuggestActions: () => void;
  caseTitle?: string;
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
              {props.caseTitle && (
                <span className="text-[10px] text-slate-400 bg-black/30 border border-white/10 px-2 py-0.5 rounded-full ml-2 truncate max-w-[120px]" title={props.caseTitle}>
                  {props.caseTitle}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={props.onToggleSuggestActions}
            className={`text-[10px] uppercase tracking-wide px-3 py-1 rounded-full border transition-all ${
              props.suggestActions
                ? 'border-legal-gold/40 bg-legal-gold/10 text-legal-gold'
                : 'border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/40'
            }`}
            title="Toggle proactive action suggestions"
          >
            {props.suggestActions ? 'Action Hints On' : 'Action Hints Off'}
          </button>
          <button
            onClick={props.toggleChat}
            className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-colors"
            title="Close"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
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
