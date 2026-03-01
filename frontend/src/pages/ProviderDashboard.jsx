import { useState, useEffect, useRef } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTemperatureQuarter } from '@fortawesome/free-solid-svg-icons';
import { faServer } from '@fortawesome/free-solid-svg-icons';
import { faMicrochip } from '@fortawesome/free-solid-svg-icons';
import { faMemory } from '@fortawesome/free-solid-svg-icons';

const WS_BASE = 'ws://localhost:8000';

export default function ProviderDashboard() {
    const { user } = useAuth();
    const [gpus, setGPUs] = useState([]);
    const [wallet, setWallet] = useState(null);
    const [transactions, setTransactions] = useState([]);
    const [showRegister, setShowRegister] = useState(false);
    const [form, setForm] = useState({ name: '', vram_mb: '', cuda_version: '' });

    // Live data from WebSocket
    const [metrics, setMetrics] = useState({});      // gpu_id → latest metrics
    const [agentLogs, setAgentLogs] = useState([]);   // array of log lines
    const [wsConnected, setWsConnected] = useState(false);
    const [agentConnecting, setAgentConnecting] = useState(false); // shows progress bar

    const logEndRef = useRef(null);
    const wsRef = useRef(null);
    const MAX_LOG_LINES = 500;

    const load = async () => {
        try {
            const [g, w, t] = await Promise.all([api.listGPUs(), api.getWallet(), api.getTransactions()]);
            setGPUs(g);
            setWallet(w);
            setTransactions(t);
        } catch (e) { console.error(e); }
    };

    useEffect(() => { load(); }, []);

    // WebSocket connection for real-time updates
    useEffect(() => {
        if (!user?.id) return;

        let ws;
        let reconnectTimer;

        const connect = () => {
            ws = new WebSocket(`${WS_BASE}/ws/provider/${user.id}`);
            wsRef.current = ws;

            ws.onopen = () => {
                setWsConnected(true);
                console.log('Provider WS connected');
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);

                    if (msg.type === 'metrics') {
                        setMetrics(prev => ({ ...prev, [msg.gpu_id]: msg.data }));
                        setAgentConnecting(false); // Agent is back — hide progress bar
                    } else if (msg.type === 'agent_log') {
                        setAgentLogs(prev => {
                            const next = [...prev, { time: new Date().toLocaleTimeString(), text: msg.data, gpu_id: msg.gpu_id }];
                            return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next;
                        });
                    } else if (msg.type === 'job_log') {
                        setAgentLogs(prev => {
                            const next = [...prev, { time: new Date().toLocaleTimeString(), text: `[JOB ${msg.job_id?.slice(0, 8)}] ${msg.data}`, gpu_id: msg.gpu_id, isJob: true }];
                            return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next;
                        });
                    } else if (msg.type === 'job_status') {
                        setAgentLogs(prev => {
                            const next = [...prev, { time: new Date().toLocaleTimeString(), text: `[JOB ${msg.job_id?.slice(0, 8)}] Status → ${msg.status}`, gpu_id: msg.gpu_id, isStatus: true }];
                            return next.length > MAX_LOG_LINES ? next.slice(-MAX_LOG_LINES) : next;
                        });
                        load(); // Refresh data on job status changes
                    } else if (msg.type === 'agent_status') {
                        load(); // Refresh GPU list on status changes
                    }
                } catch (err) {
                    console.error('WS message parse error:', err);
                }
            };

            ws.onclose = () => {
                setWsConnected(false);
                console.log('Provider WS disconnected, reconnecting in 3s…');
                reconnectTimer = setTimeout(connect, 3000);
            };

            ws.onerror = (err) => {
                console.error('Provider WS error:', err);
                ws.close();
            };
        };

        connect();

        return () => {
            clearTimeout(reconnectTimer);
            if (wsRef.current) {
                wsRef.current.onclose = null; // prevent reconnect on unmount
                wsRef.current.close();
            }
        };
    }, [user?.id]);

    // Auto-scroll logs
    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [agentLogs]);

    const handleRegisterGPU = async () => {
        try {
            await api.registerGPU({
                name: form.name,
                vram_mb: parseInt(form.vram_mb),
                cuda_version: form.cuda_version,
            });
            setShowRegister(false);
            setForm({ name: '', vram_mb: '', cuda_version: '' });
            await load();
        } catch (e) { alert(e.detail || 'Registration failed'); }
    };

    const toggleStatus = async (gpu) => {
        const newStatus = gpu.status === 'online' ? 'offline' : 'online';
        try {
            if (newStatus === 'online') {
                setAgentConnecting(true); // Show progress bar
            } else {
                setAgentConnecting(false);
                setMetrics(prev => { const next = { ...prev }; delete next[gpu.id]; return next; });
            }
            await api.updateGPU(gpu.id, { status: newStatus });
            await load();
        } catch (e) {
            setAgentConnecting(false);
            alert(e.detail || 'Update failed');
        }
    };

    const statusBadge = (s) => <span className={`badge badge-${s}`}>{s}</span>;

    // Get combined metrics (show first GPU's metrics if available)
    const activeGpuId = gpus.find(g => g.status === 'online' || g.status === 'busy')?.id;
    const liveMetrics = activeGpuId ? metrics[activeGpuId] : null;

    return (
        <div className="layout">
            <Sidebar />
            <main className="main-content">
                <div className="page-header animate-in">
                    <h2>Provider Dashboard</h2>
                    <p>Manage your GPUs and track earnings</p>
                </div>

                {/* Stat Cards */}
                <div className="grid-4 animate-in">
                    <div className="glass stat-card">
                        <span className="stat-label">Total GPUs</span>
                        <span className="stat-value cyan">{gpus.length}</span>
                    </div>
                    <div className="glass stat-card">
                        <span className="stat-label">Online</span>
                        <span className="stat-value green">{gpus.filter(g => g.status === 'online' || g.status === 'busy').length}</span>
                    </div>
                    <div className="glass stat-card">
                        <span className="stat-label">Busy</span>
                        <span className="stat-value amber">{gpus.filter(g => g.status === 'busy').length}</span>
                    </div>
                    <div className="glass stat-card">
                        <span className="stat-label">Earnings</span>
                        <span className="stat-value green">₹ {wallet?.balance?.toFixed(2) || '0.00'}</span>
                    </div>
                </div>

                {/* Connecting Progress Bar */}
                {agentConnecting && (
                    <div className="connecting-bar-wrapper animate-in">
                        <div className="connecting-bar-content">
                            <div className="connecting-spinner" />
                            <span>Connecting to agent…</span>
                        </div>
                        <div className="connecting-progress">
                            <div className="connecting-progress-fill" />
                        </div>
                    </div>
                )}

                {/* Live System Metrics */}
                <div className="section animate-in">
                    <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        Live System Metrics
                        <span className={`ws-indicator ${wsConnected ? 'ws-connected' : 'ws-disconnected'}`}>
                            {wsConnected ? '● Connected' : '○ Disconnected'}
                        </span>
                    </div>
                    {liveMetrics ? (
                        <div className="grid-4">
                            <div className="glass metric-card">
                                <div className="metric-icon"><FontAwesomeIcon icon={faTemperatureQuarter} /></div>
                                <div className="metric-info">
                                    <span className="metric-label">GPU Temp</span>
                                    <span className={`metric-value ${(liveMetrics.gpu_temp_c || 0) > 80 ? 'red' : (liveMetrics.gpu_temp_c || 0) > 65 ? 'amber' : 'green'}`}>
                                        {liveMetrics.gpu_temp_c ?? '—'}°C
                                    </span>
                                </div>
                                <div className="metric-bar-wrapper">
                                    <div className="metric-bar" style={{
                                        width: `${Math.min((liveMetrics.gpu_temp_c || 0) / 100 * 100, 100)}%`,
                                        background: (liveMetrics.gpu_temp_c || 0) > 80 ? 'var(--red)' : (liveMetrics.gpu_temp_c || 0) > 65 ? 'var(--amber)' : 'var(--green)'
                                    }} />
                                </div>
                            </div>
                            <div className="glass metric-card">
                                <div className="metric-icon"><FontAwesomeIcon icon={faMicrochip} /></div>
                                <div className="metric-info">
                                    <span className="metric-label">GPU Usage</span>
                                    <span className={`metric-value ${(liveMetrics.gpu_util_pct || 0) > 90 ? 'red' : (liveMetrics.gpu_util_pct || 0) > 60 ? 'amber' : 'green'}`}>
                                        {liveMetrics.gpu_util_pct ?? '—'}%
                                    </span>
                                </div>
                                <div className="metric-bar-wrapper">
                                    <div className="metric-bar" style={{
                                        width: `{liveMetrics.gpu_util_pct || 0}%`,
                                        background: (liveMetrics.gpu_util_pct || 0) > 90 ? 'var(--red)' : (liveMetrics.gpu_util_pct || 0) > 60 ? 'var(--amber)' : 'var(--green)'
                                    }} />
                                </div>
                            </div>
                            <div className="glass metric-card">
                                <div className="metric-icon"><FontAwesomeIcon icon={faServer} /></div>
                                <div className="metric-info">
                                    <span className="metric-label">CPU Usage</span>
                                    <span className={`metric-value ${(liveMetrics.cpu_pct || 0) > 90 ? 'red' : (liveMetrics.cpu_pct || 0) > 60 ? 'amber' : 'green'}`}>
                                        {liveMetrics.cpu_pct ?? '—'}%
                                    </span>
                                </div>
                                <div className="metric-bar-wrapper">
                                    <div className="metric-bar" style={{
                                        width: `${liveMetrics.cpu_pct || 0}%`,
                                        background: (liveMetrics.cpu_pct || 0) > 90 ? 'var(--red)' : (liveMetrics.cpu_pct || 0) > 60 ? 'var(--amber)' : 'var(--green)'
                                    }} />
                                </div>
                            </div>
                            <div className="glass metric-card">
                                <div className="metric-icon"><FontAwesomeIcon icon={faMemory} /></div>
                                <div className="metric-info">
                                    <span className="metric-label">Memory</span>
                                    <span className={`metric-value ${(liveMetrics.mem_pct || 0) > 90 ? 'red' : (liveMetrics.mem_pct || 0) > 70 ? 'amber' : 'green'}`}>
                                        {liveMetrics.mem_pct ?? '—'}%
                                    </span>
                                </div>
                                <div className="metric-bar-wrapper">
                                    <div className="metric-bar" style={{
                                        width: `${liveMetrics.mem_pct || 0}%`,
                                        background: (liveMetrics.mem_pct || 0) > 90 ? 'var(--red)' : (liveMetrics.mem_pct || 0) > 70 ? 'var(--amber)' : 'var(--green)'
                                    }} />
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="glass" style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                            {wsConnected
                                ? 'Waiting for agent metrics… Make sure the agent is running.'
                                : 'WebSocket not connected. Metrics will appear once the agent is online.'}
                        </div>
                    )}
                </div>

                <div className="grid-2">
                    {/* GPU List */}
                    <div className="section animate-in">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <div className="section-title" style={{ margin: 0 }}>My GPUs</div>
                            <button className="btn btn-primary btn-small" onClick={() => setShowRegister(true)}>
                                + Register GPU
                            </button>
                        </div>
                        {gpus.length === 0 ? (
                            <div className="glass" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                                No GPUs registered yet. Click "Register GPU" to get started.
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                {gpus.map(gpu => (
                                    <div key={gpu.id} className="glass" style={{ padding: '20px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div>
                                                <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: '4px' }}>
                                                    {gpu.name}
                                                </div>
                                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                                    {gpu.vram_mb} MB VRAM · CUDA {gpu.cuda_version || 'N/A'}
                                                </div>
                                                <div style={{ marginTop: '6px' }}>{statusBadge(gpu.status)}</div>
                                            </div>
                                            <button
                                                className={`btn btn-small ${gpu.status === 'online' ? 'btn-danger' : 'btn-primary'}`}
                                                onClick={() => toggleStatus(gpu)}>
                                                {gpu.status === 'online' ? 'Go Offline' : 'Go Online'}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Earnings */}
                    <div className="section animate-in">
                        <div className="section-title">Earnings</div>
                        <div className="glass" style={{ padding: '24px' }}>
                            <div className="wallet-balance">
                                <span className="currency">₹ </span>
                                {wallet?.balance?.toFixed(2) || '0.00'}
                            </div>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '8px' }}>
                                You earn credits when your GPU runs training jobs for clients.
                            </p>

                            {transactions.length > 0 && (
                                <div style={{ marginTop: '16px' }}>
                                    <div className="section-title">Transaction History</div>
                                    <div className="table-container">
                                        <table>
                                            <thead><tr><th>Type</th><th>Amount</th><th>Date</th></tr></thead>
                                            <tbody>
                                                {transactions.slice(0, 10).map(t => (
                                                    <tr key={t.id}>
                                                        <td>{t.type}</td>
                                                        <td style={{ color: t.type === 'credit' ? 'var(--green)' : 'var(--red)' }}>
                                                            {t.type === 'credit' ? '+' : '-'}{t.amount.toFixed(2)}
                                                        </td>
                                                        <td>{new Date(t.created_at).toLocaleDateString()}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Agent Logs Terminal */}
                <div className="section animate-in">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            📋 Agent Logs
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                                {agentLogs.length} lines
                            </span>
                        </div>
                        <button
                            className="btn btn-small"
                            style={{ background: 'var(--glass-bg)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                            onClick={() => setAgentLogs([])}
                        >
                            Clear
                        </button>
                    </div>
                    <div className="log-terminal">
                        {agentLogs.length === 0 ? (
                            <div className="log-empty">
                                No logs yet. Logs will appear here when the agent is running.
                            </div>
                        ) : (
                            agentLogs.map((log, i) => (
                                <div key={i} className={`log-line ${log.isJob ? 'log-job' : ''} ${log.isStatus ? 'log-status' : ''}`}>
                                    <span className="log-time">{log.time}</span>
                                    <span className="log-text">{log.text}</span>
                                </div>
                            ))
                        )}
                        <div ref={logEndRef} />
                    </div>
                </div>

                {/* Register GPU Modal */}
                {showRegister && (
                    <div className="modal-overlay" onClick={() => setShowRegister(false)}>
                        <div className="modal glass-elevated" onClick={e => e.stopPropagation()}>
                            <div className="modal-header">
                                <h3>Register New GPU</h3>
                                <button className="modal-close" onClick={() => setShowRegister(false)}>×</button>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                                <div className="form-group">
                                    <label>GPU Name</label>
                                    <input className="input" placeholder="e.g. RTX 4090"
                                        value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label>VRAM (MB)</label>
                                    <input className="input" type="number" placeholder="e.g. 24576"
                                        value={form.vram_mb} onChange={e => setForm({ ...form, vram_mb: e.target.value })} />
                                </div>
                                <div className="form-group">
                                    <label>CUDA Version</label>
                                    <input className="input" placeholder="e.g. 12.3"
                                        value={form.cuda_version} onChange={e => setForm({ ...form, cuda_version: e.target.value })} />
                                </div>
                                <button className="btn btn-primary" onClick={handleRegisterGPU} style={{ width: '100%' }}>
                                    Register GPU
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
