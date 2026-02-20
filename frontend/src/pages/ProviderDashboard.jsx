import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../api/client';

export default function ProviderDashboard() {
    const [gpus, setGPUs] = useState([]);
    const [wallet, setWallet] = useState(null);
    const [transactions, setTransactions] = useState([]);
    const [showRegister, setShowRegister] = useState(false);
    const [form, setForm] = useState({ name: '', vram_mb: '', cuda_version: '' });

    const load = async () => {
        try {
            const [g, w, t] = await Promise.all([api.listGPUs(), api.getWallet(), api.getTransactions()]);
            setGPUs(g);
            setWallet(w);
            setTransactions(t);
        } catch (e) { console.error(e); }
    };

    useEffect(() => { load(); }, []);

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
            await api.updateGPU(gpu.id, { status: newStatus });
            await load();
        } catch (e) { alert(e.detail || 'Update failed'); }
    };

    const statusBadge = (s) => <span className={`badge badge-${s}`}>{s}</span>;

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
                        <span className="stat-value green">{gpus.filter(g => g.status === 'online').length}</span>
                    </div>
                    <div className="glass stat-card">
                        <span className="stat-label">Busy</span>
                        <span className="stat-value amber">{gpus.filter(g => g.status === 'busy').length}</span>
                    </div>
                    <div className="glass stat-card">
                        <span className="stat-label">Earnings</span>
                        <span className="stat-value green">${wallet?.balance?.toFixed(2) || '0.00'}</span>
                    </div>
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
                                <span className="currency">$ </span>
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
                                                        <td style={{ color: t.amount >= 0 ? 'var(--green)' : 'var(--red)' }}>
                                                            {t.amount >= 0 ? '+' : ''}{t.amount.toFixed(2)}
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
