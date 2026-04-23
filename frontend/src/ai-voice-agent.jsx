import { useState, useEffect, useRef, useCallback } from "react";

const API = "http://127.0.0.1:5000";

// ── Icons ──
const I = ({ d, size = 20, sw = 1.8 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">{typeof d === "string" ? <path d={d} /> : d}</svg>
);
const PhoneCall = ({ size }) => <I size={size} d={<><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></>} />;
const PhoneOff = ({ size }) => <I size={size} d={<><path d="m2 2 20 20"/><path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67"/><path d="M8.09 9.91a16 16 0 0 1-.68-.97 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91z"/></>} />;
const Mic = ({ size }) => <I size={size} d={<><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></>} />;
const Clock = ({ size }) => <I size={size} d={<><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></>} />;
const Backspace = ({ size }) => <I size={size} d={<><path d="M21 4H8l-7 8 7 8h13a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z"/><line x1="18" x2="12" y1="9" y2="15"/><line x1="12" x2="18" y1="9" y2="15"/></>} />;
const HistIcon = ({ size }) => <I size={size} d={<><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></>} />;
const ChevUp = ({ size }) => <I size={size} d="m18 15-6-6-6 6" />;
const Heart = ({ size }) => <I size={size} d={<><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></>} />;
const User = ({ size }) => <I size={size} d={<><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></>} />;

const fmt = s => `${String(Math.floor(s/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;
const fmtTime = d => new Date(d).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

// ── Waveform ──
function Wave({ active }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2.5, height: 44, justifyContent: "center" }}>
      {Array.from({ length: 28 }).map((_, i) => (
        <div key={i} style={{
          width: 3, borderRadius: 4,
          background: active ? "var(--pri)" : "var(--border)",
          height: active ? undefined : 3,
          animation: active ? `wave 1.1s ease-in-out ${i * 0.045}s infinite alternate` : "none",
        }} />
      ))}
    </div>
  );
}

// ── Dial Pad ──
const KEYS = [["1",""],["2","ABC"],["3","DEF"],["4","GHI"],["5","JKL"],["6","MNO"],["7","PQRS"],["8","TUV"],["9","WXYZ"],["*",""],["0","+"],["#",""]];

function Pad({ onPress, disabled }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8, maxWidth: 264, margin: "0 auto" }}>
      {KEYS.map(([d, l]) => (
        <button key={d} disabled={disabled} onClick={() => onPress(d)} style={{
          background: "var(--card)", border: "1px solid var(--border)", borderRadius: 14,
          padding: "14px 0 10px", cursor: disabled ? "not-allowed" : "pointer",
          color: "var(--text)", fontFamily: "var(--mono)", fontSize: 20, fontWeight: 500,
          display: "flex", flexDirection: "column", alignItems: "center", gap: 1,
          opacity: disabled ? 0.3 : 1, transition: "all .12s",
        }}
          onMouseDown={e => { if (!disabled) { e.currentTarget.style.background = "var(--pri-dim)"; e.currentTarget.style.borderColor = "var(--pri)"; }}}
          onMouseUp={e => { e.currentTarget.style.background = "var(--card)"; e.currentTarget.style.borderColor = "var(--border)"; }}
          onMouseLeave={e => { e.currentTarget.style.background = "var(--card)"; e.currentTarget.style.borderColor = "var(--border)"; }}
        >
          {d}
          <span style={{ fontSize: 8, letterSpacing: 2.5, color: "var(--muted)", fontWeight: 700 }}>{l}</span>
        </button>
      ))}
    </div>
  );
}

// ── Call Log Row ──
function LogRow({ c }) {
  const color = c.status === "initiated" ? "var(--pri)" : c.status === "failed" ? "var(--danger)" : "var(--muted)";
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 14, padding: "13px 18px",
      borderBottom: "1px solid var(--border)", transition: "background .12s",
    }}
      onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.02)"}
      onMouseLeave={e => e.currentTarget.style.background = "transparent"}
    >
      <div style={{ width: 36, height: 36, borderRadius: 10, flexShrink: 0, background: `${color}12`, display: "flex", alignItems: "center", justifyContent: "center", color }}>
        <PhoneCall size={14} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontFamily: "var(--mono)", fontWeight: 500, color: "var(--text)" }}>{c.phone}</div>
        <div style={{ fontSize: 10.5, color: "var(--muted)", marginTop: 3, display: "flex", gap: 10 }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 3 }}><Clock size={9} /> {fmtTime(c.started_at)}</span>
          {c.call_sid && <span style={{ opacity: 0.5 }}>...{c.call_sid.slice(-6)}</span>}
        </div>
      </div>
      <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: .8, textTransform: "uppercase", color, background: `${color}10`, padding: "3px 9px", borderRadius: 6 }}>{c.status}</span>
    </div>
  );
}

// ════════════════════ MAIN ════════════════════
export default function CynergyAI() {
  const [phone, setPhone] = useState("");
  const [state, setState] = useState("idle");  // idle | connecting | ringing | active | ended | error
  const [dur, setDur] = useState(0);
  const [log, setLog] = useState([]);
  const [pad, setPad] = useState(false);
  const [err, setErr] = useState("");
  const [activeSid, setActiveSid] = useState("");
  const [convId, setConvId] = useState("");
  const [panel, setPanel] = useState("dialer");
  const timer = useRef(null);
  const pollRef = useRef(null);

  // Timer — ONLY runs in "active" state
  useEffect(() => {
    if (state === "active") {
      timer.current = setInterval(() => setDur(d => d + 1), 1000);
    } else {
      clearInterval(timer.current);
    }
    return () => clearInterval(timer.current);
  }, [state]);

  // Poll conversation status to detect when call is actually answered
  useEffect(() => {
    if (state === "ringing" && convId) {
      pollRef.current = setInterval(async () => {
        try {
          const r = await fetch(`${API}/call-status/${convId}`);
          if (r.ok) {
            const d = await r.json();
            if (d.status === "active" || d.status === "in-progress") {
              setState("active");
              clearInterval(pollRef.current);
            } else if (d.status === "failed" || d.status === "done") {
              setState("ended");
              clearInterval(pollRef.current);
            }
          }
        } catch {}
      }, 2000);
    }
    return () => clearInterval(pollRef.current);
  }, [state, convId]);

  // Fallback: if polling doesn't detect active after 15s, assume active
  useEffect(() => {
    if (state === "ringing") {
      const fallback = setTimeout(() => {
        setState(prev => prev === "ringing" ? "active" : prev);
      }, 15000);
      return () => clearTimeout(fallback);
    }
  }, [state]);

  const fetchLog = useCallback(async () => {
    try { const r = await fetch(`${API}/calls`); if (r.ok) setLog(await r.json()); } catch {}
  }, []);

  useEffect(() => { fetchLog(); }, [fetchLog]);

  const startCall = async () => {
    if (!phone.trim()) return;
    setErr(""); setState("connecting"); setDur(0);
    try {
      const res = await fetch(`${API}/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.replace(/\s/g, "") }),
      });
      const data = await res.json();
      if (!res.ok) {
        setErr(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
        setState("error"); return;
      }
      setActiveSid(data.call_sid || "");
      setConvId(data.conversation_id || "");
      setState("ringing");
    } catch (e) {
      setErr("Cannot reach backend. Is the server running?");
      setState("error");
    }
  };

  const endCall = () => {
    clearInterval(pollRef.current);
    setState("ended"); fetchLog();
    setTimeout(() => { setState("idle"); setDur(0); setActiveSid(""); setConvId(""); }, 2000);
  };

  const isLive = ["connecting", "ringing", "active"].includes(state);
  const statusMap = {
    idle:       { label: "Ready",           color: "var(--muted)" },
    connecting: { label: "Connecting",      color: "var(--warn)" },
    ringing:    { label: "Ringing",         color: "var(--warn)" },
    active:     { label: "Agent Live",      color: "var(--pri)" },
    ended:      { label: "Call Ended",      color: "var(--muted)" },
    error:      { label: "Error",           color: "var(--danger)" },
  };
  const { label: statusLabel, color: statusColor } = statusMap[state];

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", fontFamily: "var(--sans)", color: "var(--text)", display: "flex", flexDirection: "column", alignItems: "center", padding: "0 16px" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
        :root {
          --bg:#060810; --surface:#0c0f18; --card:#111525; --border:rgba(255,255,255,.06);
          --border-hi:rgba(255,255,255,.1); --text:#e2e6f0; --text-sec:#8e99b0; --muted:#4a5574;
          --pri:#3b9eff; --pri-soft:#2563eb; --pri-dim:rgba(59,158,255,.08); --pri-glow:rgba(59,158,255,.18);
          --danger:#ef4444; --warn:#f59e0b;
          --sans:'Plus Jakarta Sans',sans-serif; --mono:'JetBrains Mono',monospace;
        }
        *{box-sizing:border-box;margin:0;padding:0}
        @keyframes wave{0%{height:3px}100%{height:36px}}
        @keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
        @keyframes pulse{0%,100%{opacity:.4;transform:scale(.85)}50%{opacity:1;transform:scale(1.2)}}
        @keyframes ringPulse{0%{transform:scale(.85);opacity:.6}100%{transform:scale(1.7);opacity:0}}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes breathe{0%,100%{box-shadow:0 0 24px var(--pri-glow)}50%{box-shadow:0 0 48px var(--pri-glow), 0 0 96px rgba(59,158,255,.06)}}
        ::-webkit-scrollbar{width:3px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border-hi);border-radius:3px}
        input:focus{outline:none}button{font-family:var(--sans);border:none;cursor:pointer}button:disabled{cursor:not-allowed}
      `}</style>

      {/* ── Header ── */}
      <header style={{ width: "100%", maxWidth: 420, padding: "28px 0 16px", display: "flex", alignItems: "center", justifyContent: "space-between", animation: "fadeUp .4s ease-out" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          <div style={{ width: 34, height: 34, borderRadius: 10, background: "linear-gradient(140deg, #3b9eff, #2563eb)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 3px 14px var(--pri-glow)" }}>
            <Heart size={16} />
          </div>
          <div>
            <h1 style={{ fontSize: 16, fontWeight: 800, letterSpacing: -.4, lineHeight: 1, background: "linear-gradient(135deg, #3b9eff, #60b4ff)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Cynergy AI</h1>
            <p style={{ fontSize: 9, color: "var(--muted)", fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginTop: 3 }}>Healthcare Voice Agent</p>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, background: `${statusColor}0c`, padding: "5px 12px", borderRadius: 20, border: `1px solid ${statusColor}18` }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: statusColor, boxShadow: `0 0 8px ${statusColor}`, animation: isLive ? "pulse 1.6s infinite" : "none" }} />
          <span style={{ fontSize: 10.5, fontWeight: 700, color: statusColor, letterSpacing: .3 }}>{statusLabel}</span>
        </div>
      </header>

      {/* ── Tabs ── */}
      <div style={{ width: "100%", maxWidth: 420, display: "flex", gap: 4, marginBottom: 12, background: "var(--surface)", borderRadius: 13, padding: 4, border: "1px solid var(--border)", animation: "fadeUp .45s ease-out" }}>
        {[["dialer", <PhoneCall size={13} />, "Dialer"], ["history", <HistIcon size={13} />, "History"]].map(([id, icon, lbl]) => (
          <button key={id} onClick={() => { setPanel(id); if(id==="history") fetchLog(); }}
            style={{ flex: 1, padding: "10px 0", borderRadius: 10, background: panel===id?"var(--card)":"transparent", color: panel===id?"var(--text)":"var(--muted)", fontSize: 12, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, border: panel===id?"1px solid var(--border-hi)":"1px solid transparent", transition: "all .15s" }}>
            {icon} {lbl}
          </button>
        ))}
      </div>

      {/* ══════════ DIALER ══════════ */}
      {panel === "dialer" && (
        <div style={{
          width: "100%", maxWidth: 420, background: "var(--surface)", borderRadius: 22,
          border: "1px solid var(--border)", overflow: "hidden", animation: "fadeUp .5s ease-out",
          boxShadow: state === "active" ? undefined : "0 16px 56px rgba(0,0,0,.4)",
          ...(state === "active" ? { animation: "breathe 4s ease-in-out infinite" } : {}),
        }}>
          <div style={{ padding: "40px 24px 20px", textAlign: "center", position: "relative" }}>

            {/* Ambient glow */}
            {isLive && <div style={{ position: "absolute", top: -60, left: "50%", transform: "translateX(-50%)", width: 300, height: 200, borderRadius: "50%", background: `radial-gradient(ellipse,${statusColor}06 0%,transparent 70%)`, pointerEvents: "none" }} />}

            {/* Avatar */}
            <div style={{ width: 80, height: 80, borderRadius: 24, margin: "0 auto 22px", background: isLive ? `${statusColor}0c` : "var(--card)", border: `1.5px solid ${isLive ? statusColor+"25" : "var(--border)"}`, display: "flex", alignItems: "center", justifyContent: "center", position: "relative", transition: "all .4s" }}>
              {state === "ringing" && [0,1,2].map(i => (
                <div key={i} style={{ position: "absolute", width: 80+i*26, height: 80+i*26, borderRadius: 24+i*3, border: `1px solid ${statusColor}${25-i*7}`, pointerEvents: "none", animation: `ringPulse 2.4s ease-out ${i*.5}s infinite` }} />
              ))}
              {state === "connecting" && (
                <div style={{ position: "absolute", width: 90, height: 90, borderRadius: 26, border: "2px solid transparent", borderTop: `2px solid ${statusColor}`, animation: "spin 1s linear infinite", pointerEvents: "none" }} />
              )}
              {state === "active" ? <Mic size={32} /> : isLive ? <PhoneCall size={28} /> : <User size={30} />}
            </div>

            {/* Phone Input */}
            <div style={{ position: "relative", marginBottom: 8 }}>
              <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} placeholder="+91 00000 00000" disabled={isLive}
                style={{ width: "100%", textAlign: "center", fontSize: 26, fontWeight: 600, fontFamily: "var(--mono)", letterSpacing: 2, background: "transparent", border: "none", color: "var(--text)", padding: "8px 44px", opacity: isLive ? 0.5 : 1, transition: "opacity .3s" }} />
              {phone && !isLive && (
                <button onClick={() => setPhone(p => p.slice(0,-1))} style={{ position: "absolute", right: 4, top: "50%", transform: "translateY(-50%)", background: "none", color: "var(--muted)", padding: 6, display: "flex", borderRadius: 8 }}>
                  <Backspace size={18} />
                </button>
              )}
            </div>

            {/* Duration — ONLY in active state */}
            {state === "active" && (
              <div style={{ fontSize: 40, fontWeight: 700, fontFamily: "var(--mono)", color: "var(--pri)", letterSpacing: 4, marginBottom: 4, animation: "fadeUp .3s ease-out" }}>
                {fmt(dur)}
              </div>
            )}

            {/* Waveform — ONLY in active state */}
            <div style={{ margin: "12px 0 6px" }}>
              <Wave active={state === "active"} />
            </div>

            {/* Status messages */}
            {state === "active" && (
              <p style={{ fontSize: 11, color: "var(--pri)", fontWeight: 600, marginTop: 10, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, animation: "fadeUp .4s ease-out" }}>
                <Mic size={12} /> Clara is handling the conversation
              </p>
            )}
            {state === "ringing" && (
              <p style={{ fontSize: 11.5, color: "var(--warn)", fontWeight: 600, marginTop: 10, animation: "fadeUp .3s" }}>
                Calling... waiting for answer
              </p>
            )}
            {state === "connecting" && (
              <p style={{ fontSize: 11.5, color: "var(--warn)", fontWeight: 600, marginTop: 10, animation: "fadeUp .3s" }}>
                Initiating call...
              </p>
            )}
            {state === "error" && err && (
              <div style={{ margin: "10px 0 0", padding: "10px 14px", borderRadius: 12, background: "rgba(239,68,68,.06)", border: "1px solid rgba(239,68,68,.12)", animation: "fadeUp .3s" }}>
                <p style={{ fontSize: 12, color: "var(--danger)", fontWeight: 500 }}>{err}</p>
              </div>
            )}

            {/* SID / Conv ID */}
            {(activeSid || convId) && isLive && (
              <div style={{ marginTop: 14, display: "flex", justifyContent: "center", gap: 16 }}>
                {activeSid && <span style={{ fontSize: 9, color: "var(--muted)", fontFamily: "var(--mono)", background: "var(--card)", padding: "3px 8px", borderRadius: 5 }}>SID ...{activeSid.slice(-6)}</span>}
                {convId && <span style={{ fontSize: 9, color: "var(--muted)", fontFamily: "var(--mono)", background: "var(--card)", padding: "3px 8px", borderRadius: 5 }}>CONV ...{convId.slice(-6)}</span>}
              </div>
            )}
          </div>

          {/* Dial Pad Toggle */}
          {!isLive && state !== "ended" && (
            <div style={{ padding: "0 24px" }}>
              <button onClick={() => setPad(!pad)} style={{ width: "100%", background: "none", color: "var(--muted)", fontSize: 10.5, fontWeight: 700, padding: "8px 0", letterSpacing: 1.2, display: "flex", alignItems: "center", justifyContent: "center", gap: 5, textTransform: "uppercase", transition: "color .15s" }}
                onMouseEnter={e => e.currentTarget.style.color = "var(--text-sec)"}
                onMouseLeave={e => e.currentTarget.style.color = "var(--muted)"}
              >
                <span style={{ transform: pad ? "rotate(0)" : "rotate(180deg)", transition: "transform .2s", display: "inline-flex" }}><ChevUp size={12} /></span>
                {pad ? "Hide dialpad" : "Show dialpad"}
              </button>
              {pad && <div style={{ paddingBottom: 14, animation: "fadeUp .2s ease-out" }}><Pad onPress={d => phone.length < 20 && setPhone(p => p + d)} disabled={isLive} /></div>}
            </div>
          )}

          {/* Action Button */}
          <div style={{ padding: "10px 24px 28px" }}>
            {!isLive && state !== "ended" ? (
              <button onClick={startCall} disabled={!phone.trim()} style={{
                width: "100%", padding: "17px 0", borderRadius: 14,
                background: phone.trim() ? "linear-gradient(135deg, #3b9eff, #2563eb)" : "var(--card)",
                color: phone.trim() ? "#fff" : "var(--muted)",
                fontSize: 13.5, fontWeight: 700, letterSpacing: .6,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 9,
                transition: "all .2s",
                boxShadow: phone.trim() ? "0 6px 28px var(--pri-glow)" : "none",
                opacity: phone.trim() ? 1 : .4,
              }}>
                <PhoneCall size={17} /> Start call
              </button>
            ) : isLive ? (
              <button onClick={endCall} style={{
                width: "100%", padding: "17px 0", borderRadius: 14,
                background: "linear-gradient(135deg, #ef4444, #dc2626)",
                color: "#fff", fontSize: 13.5, fontWeight: 700, letterSpacing: .6,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 9,
                boxShadow: "0 6px 24px rgba(239,68,68,.18)", transition: "all .2s",
              }}>
                <PhoneOff size={17} /> End call
              </button>
            ) : (
              <button onClick={() => { setState("idle"); setDur(0); }} style={{
                width: "100%", padding: "17px 0", borderRadius: 14,
                background: "var(--card)", color: "var(--text)",
                border: "1px solid var(--border-hi)", fontSize: 13.5, fontWeight: 600, transition: "all .2s",
              }}>
                New call
              </button>
            )}
          </div>
        </div>
      )}

      {/* ══════════ HISTORY ══════════ */}
      {panel === "history" && (
        <div style={{ width: "100%", maxWidth: 420, background: "var(--surface)", borderRadius: 22, border: "1px solid var(--border)", overflow: "hidden", animation: "fadeUp .4s ease-out", boxShadow: "0 16px 56px rgba(0,0,0,.4)" }}>
          <div style={{ padding: "15px 18px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, color: "var(--muted)", textTransform: "uppercase" }}>Call history</span>
            <button onClick={fetchLog} style={{ fontSize: 10, fontWeight: 700, color: "var(--pri)", background: "var(--pri-dim)", padding: "4px 10px", borderRadius: 6, letterSpacing: .3 }}>Refresh</button>
          </div>
          <div style={{ maxHeight: 420, overflowY: "auto" }}>
            {log.length === 0 ? (
              <div style={{ padding: "48px 16px", textAlign: "center" }}>
                <div style={{ color: "var(--muted)", marginBottom: 8 }}><HistIcon size={28} /></div>
                <p style={{ fontSize: 13, color: "var(--muted)", fontWeight: 500 }}>No calls yet</p>
                <p style={{ fontSize: 11, color: "var(--border-hi)", marginTop: 4 }}>Calls appear here after you make them</p>
              </div>
            ) : log.map((c, i) => <LogRow key={c.call_sid || i} c={c} />)}
          </div>
        </div>
      )}

      <p style={{ fontSize: 8.5, color: "var(--muted)", letterSpacing: 1.8, padding: "24px 0 20px", textAlign: "center", textTransform: "uppercase", fontWeight: 600, opacity: .5 }}>
        Cynergy AI &middot; ElevenLabs &middot; Twilio
      </p>
    </div>
  );
}