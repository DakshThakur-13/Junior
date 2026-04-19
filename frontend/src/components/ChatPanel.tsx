import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Languages, Mic, Paperclip, Scale, Send, ShieldAlert, Sparkles, Square, X } from 'lucide-react';
import type { ChatMessage } from '../types';

type ChatLanguage = 'en' | 'hi' | 'mr' | 'hi-latn';
type OutputScript = 'native' | 'roman';

export function ChatPanel(props: {
  isOpen: boolean;
  toggleChat: () => void;
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  onRetryLast: () => void;
  onStopResponse: () => void;
  isLoading: boolean;
  suggestActions: boolean;
  onToggleSuggestActions: () => void;
  caseTitle?: string;
  language: ChatLanguage;
  outputScript: OutputScript;
  onChangeLanguage: (lang: ChatLanguage) => void;
  onChangeOutputScript: (script: OutputScript) => void;
  renderMessageContent?: (content: string, msg?: ChatMessage) => React.ReactNode;
}) {
  const [inputValue, setInputValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const attachInputRef = useRef<HTMLInputElement | null>(null);
  const quickPrompts = [
    'Summarize my current case and list top 3 risks.',
    'What evidence gaps should I fill before filing?',
    'Draft a concise next-hearing prep checklist.',
  ];

  const canUseMic = useMemo(() => {
    return typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [props.messages]);

  const handleSend = () => {
    if (inputValue.trim() && !props.isLoading && !isTranscribing) {
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

  const stopRecording = async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;

    try {
      recorder.stop();
    } catch {
      // ignore
    }
  };

  const startRecording = async () => {
    if (!canUseMic || props.isLoading || isTranscribing) return;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaStreamRef.current = stream;

    const recorder = new MediaRecorder(stream);
    recordedChunksRef.current = [];
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (evt) => {
      if (evt.data && evt.data.size > 0) recordedChunksRef.current.push(evt.data);
    };

    recorder.onstop = async () => {
      setIsRecording(false);
      setIsTranscribing(true);
      try {
        const blob = new Blob(recordedChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        const form = new FormData();
        form.append('file', blob, 'recording.webm');

        const res = await fetch('/api/v1/audio/transcribe', {
          method: 'POST',
          body: form,
        });

        if (!res.ok) {
          throw new Error(await res.text());
        }

        const data = (await res.json()) as { text?: string };
        const text = (data.text || '').trim();
        if (text) {
          setInputValue((prev) => (prev ? `${prev} ${text}` : text));
        }
      } catch {
        // keep it quiet; user can retry
      } finally {
        setIsTranscribing(false);
        // stop tracks
        try {
          mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
        } catch {
          // ignore
        }
        mediaStreamRef.current = null;
        mediaRecorderRef.current = null;
        recordedChunksRef.current = [];
      }
    };

    recorder.start();
    setIsRecording(true);
  };

  const handleMicClick = async () => {
    try {
      if (isRecording) {
        await stopRecording();
      } else {
        await startRecording();
      }
    } catch {
      setIsRecording(false);
      try {
        mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
      } catch {
        // ignore
      }
      mediaStreamRef.current = null;
      mediaRecorderRef.current = null;
    }
  };

  if (!props.isOpen) return null;

  return (
    <div className="chat-panel-shell fixed right-0 top-0 h-full w-full sm:w-[400px] glass-panel border-l border-white/10 flex flex-col shadow-2xl">
      <div className="p-4 border-b border-white/10 flex flex-col gap-3 bg-legal-surface/50">
        {/* Header row with title and close button */}
        <div className="flex justify-between items-center">
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
          {/* Larger, more visible close button */}
          <button
            onClick={props.toggleChat}
            className="p-2.5 hover:bg-red-500/20 rounded-xl text-slate-400 hover:text-red-400 transition-all border border-white/10 hover:border-red-500/30 flex-shrink-0"
            title="Close Chat"
            aria-label="Close Chat"
          >
            <X size={20} className="stroke-[2.5]" />
          </button>
        </div>
        {/* Controls row */}
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={props.language}
            onChange={(e) => props.onChangeLanguage(e.target.value as ChatLanguage)}
            className="text-[10px] uppercase tracking-wide px-2.5 py-1.5 rounded-lg border border-white/10 bg-black/30 text-slate-300 hover:border-legal-gold/40 focus:outline-none focus:ring-2 focus:ring-legal-gold/20"
            title="Response language"
            disabled={props.isLoading || isTranscribing}
          >
            <option value="en">English</option>
            <option value="hi">हिंदी (Hindi)</option>
            <option value="hi-latn">Hinglish</option>
            <option value="mr">मराठी (Marathi)</option>
          </select>
          <select
            value={props.outputScript}
            onChange={(e) => props.onChangeOutputScript(e.target.value as OutputScript)}
            className="text-[10px] uppercase tracking-wide px-2.5 py-1.5 rounded-lg border border-white/10 bg-black/30 text-slate-300 hover:border-legal-gold/40 focus:outline-none focus:ring-2 focus:ring-legal-gold/20"
            title="Output script"
            disabled={props.isLoading || isTranscribing || props.language === 'en' || props.language === 'hi-latn'}
          >
            <option value="native">Native</option>
            <option value="roman">Roman</option>
          </select>
          <button
            type="button"
            onClick={props.onToggleSuggestActions}
            className={`text-[10px] uppercase tracking-wide px-3 py-1.5 rounded-lg border transition-all ${
              props.suggestActions
                ? 'border-legal-gold/40 bg-legal-gold/10 text-legal-gold'
                : 'border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/40'
            }`}
            title="Toggle proactive action suggestions"
          >
            {props.suggestActions ? 'Hints On' : 'Hints Off'}
          </button>
          <button
            type="button"
            onClick={props.onRetryLast}
            disabled={props.isLoading || isTranscribing || props.messages.length < 2}
            className="text-[10px] uppercase tracking-wide px-3 py-1.5 rounded-lg border border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/40 disabled:opacity-50"
            title="Retry the last prompt"
          >
            Retry
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {props.messages.map((msg, idx) => (
          <div key={msg.id ?? idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
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
                className={`p-4 rounded-2xl text-sm shadow-lg backdrop-blur-sm relative group ${
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
                <p className="leading-relaxed whitespace-pre-wrap">
                  {props.renderMessageContent ? props.renderMessageContent(msg.content, msg) : msg.content}
                </p>
                {msg.role === 'assistant' && Array.isArray(msg.sources) && msg.sources.length > 0 && (
                  <div className="mt-3 border-t border-white/10 pt-2">
                    <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">Sources</div>
                    <div className="flex flex-col gap-1">
                      {msg.sources.slice(0, 3).map((src) => (
                        <a
                          key={src}
                          href={src}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[11px] text-legal-gold hover:underline break-all"
                        >
                          {src}
                        </a>
                      ))}
                    </div>
                  </div>
                )}
                {msg.role === 'assistant' && Array.isArray(msg.citations) && msg.citations.length > 0 && (
                  <div className="mt-3 border-t border-white/10 pt-2">
                    <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">Legal citations</div>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.citations.slice(0, 5).map((citation) => (
                        <span
                          key={citation}
                          className="text-[10px] px-2 py-1 rounded-md border border-legal-gold/20 bg-legal-gold/10 text-legal-gold"
                        >
                          {citation}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {msg.role === 'assistant' && Array.isArray(msg.suggestedActions) && msg.suggestedActions.length > 0 && (
                  <div className="mt-3 border-t border-white/10 pt-2">
                    <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">Suggested next steps</div>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.suggestedActions.slice(0, 3).map((action) => (
                        <button
                          key={action}
                          type="button"
                          onClick={() => props.onSendMessage(action)}
                          disabled={props.isLoading || isTranscribing}
                          className="text-[10px] px-2 py-1 rounded-md border border-white/10 text-slate-300 hover:text-legal-gold hover:border-legal-gold/40 disabled:opacity-50"
                        >
                          {action}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {/* Translate button for assistant messages */}
                {msg.role === 'assistant' && msg.content && (
                  <button
                    onClick={async () => {
                      try {
                        const targetLang = props.language === 'en' ? 'hi' : 'en';
                        const res = await fetch('/api/v1/translate/', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            text: msg.content,
                            target_language: targetLang,
                            preserve_legal_terms: true
                          })
                        });
                        if (res.ok) {
                          const data = await res.json();
                          alert(data.translated_text || msg.content);
                        }
                      } catch {
                        alert('Translation failed. Please try again.');
                      }
                    }}
                    className="absolute top-2 right-2 p-1.5 bg-black/40 hover:bg-legal-gold/20 rounded-lg text-slate-400 hover:text-legal-gold transition-all opacity-0 group-hover:opacity-100 border border-white/10"
                    title="Translate this message"
                    aria-label="Translate"
                  >
                    <Languages size={14} />
                  </button>
                )}
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
        {props.suggestActions && !inputValue.trim() && !props.isLoading && (
          <div className="mb-3 flex flex-wrap gap-2">
            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => setInputValue(prompt)}
                className="text-[10px] px-2.5 py-1.5 rounded-lg border border-white/10 text-slate-300 hover:text-legal-gold hover:border-legal-gold/40 bg-black/20"
                title="Use this prompt"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}
        <div className="relative group">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask Junior to research, draft, or analyze..."
            className="w-full bg-black/20 border border-white/10 rounded-xl pl-4 pr-28 py-4 text-sm text-slate-200 focus:outline-none focus:border-legal-gold/50 transition-all shadow-inner placeholder-slate-500 glass-input"
            disabled={props.isLoading || isTranscribing}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
            <button
              type="button"
              onClick={() => void handleMicClick()}
              disabled={!canUseMic || props.isLoading || isTranscribing}
              className={`p-2 transition-colors rounded-lg hover:bg-white/5 ${
                isRecording ? 'text-rose-400' : 'text-slate-500 hover:text-legal-gold'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title={isRecording ? 'Stop recording' : 'Speak (speech-to-text)'}
              aria-label={isRecording ? 'Stop recording' : 'Speak'}
            >
              {isRecording ? <Square size={18} /> : <Mic size={18} />}
            </button>
            <button
              type="button"
              onClick={() => attachInputRef.current?.click()}
              className="p-2 text-slate-500 hover:text-legal-gold transition-colors rounded-lg hover:bg-white/5"
              title="Attach"
              aria-label="Attach"
            >
              <Paperclip size={18} />
            </button>
            <input
              ref={attachInputRef}
              type="file"
              multiple
              className="hidden"
              aria-label="Attach files"
              title="Attach files"
              onChange={(e) => {
                const files = Array.from(e.target.files ?? []);
                if (!files.length) return;
                const names = files.map((f) => f.name).join(', ');
                setInputValue((prev) => (prev ? `${prev}\n[Attached: ${names}]` : `[Attached: ${names}]`));
                e.currentTarget.value = '';
              }}
            />
            <button
              onClick={props.isLoading ? props.onStopResponse : handleSend}
              disabled={isTranscribing || (!props.isLoading && !inputValue.trim())}
              className="p-2 bg-legal-gold/10 text-legal-gold hover:bg-legal-gold/20 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed border border-legal-gold/20"
              title={props.isLoading ? 'Stop response' : 'Send'}
              aria-label={props.isLoading ? 'Stop response' : 'Send'}
            >
              {props.isLoading ? <Square size={18} /> : <Send size={18} />}
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
