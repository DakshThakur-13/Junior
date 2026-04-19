import { useState } from 'react';

type AuthUser = {
  id: string;
  email: string;
  name?: string;
  role?: string;
};

export function AuthPage(props: { onAuthenticated: (token: string, user: AuthUser) => void }) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [barCouncilId, setBarCouncilId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const endpoint = mode === 'signin' ? '/api/v1/auth/signin' : '/api/v1/auth/signup';
      const payload =
        mode === 'signin'
          ? { email, password }
          : { email, password, name, bar_council_id: barCouncilId || null };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || 'Authentication failed');
      }

      props.onAuthenticated(data.access_token, data.user as AuthUser);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center px-4 text-legal-text relative overflow-hidden bg-legal-bg">
      <div className="absolute inset-0 container-bg z-0 opacity-50"></div>
      <div className="z-10 w-full max-w-md glass-panel border border-white/10 rounded-2xl p-6 shadow-2xl">
        <h1 className="text-3xl font-bold font-serif mb-1 text-center">Junior AI</h1>
        <p className="text-slate-400 text-sm text-center mb-6">Secure access for advocates</p>

        <div className="mb-5 flex rounded-xl border border-white/10 bg-black/20 p-1">
          <button
            type="button"
            onClick={() => setMode('signin')}
            className={`flex-1 rounded-lg px-3 py-2 text-sm ${mode === 'signin' ? 'bg-legal-gold/20 text-legal-gold' : 'text-slate-300'}`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => setMode('signup')}
            className={`flex-1 rounded-lg px-3 py-2 text-sm ${mode === 'signup' ? 'bg-legal-gold/20 text-legal-gold' : 'text-slate-300'}`}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {mode === 'signup' && (
            <>
              <input
                className="w-full glass-input rounded-xl px-3 py-2 text-sm"
                placeholder="Full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
              <input
                className="w-full glass-input rounded-xl px-3 py-2 text-sm"
                placeholder="Bar Council ID (optional)"
                value={barCouncilId}
                onChange={(e) => setBarCouncilId(e.target.value)}
              />
            </>
          )}

          <input
            type="email"
            className="w-full glass-input rounded-xl px-3 py-2 text-sm"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            className="w-full glass-input rounded-xl px-3 py-2 text-sm"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />

          {error && <div className="text-sm text-rose-300">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl border border-legal-gold/40 bg-legal-gold/15 px-4 py-2 text-sm font-semibold text-legal-gold hover:bg-legal-gold/25 disabled:opacity-50"
          >
            {loading ? 'Please wait...' : mode === 'signin' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
}
