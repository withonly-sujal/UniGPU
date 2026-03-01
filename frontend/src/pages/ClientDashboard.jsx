import { useState, useEffect, useRef } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../api/client';

export default function ClientDashboard() {
    const [jobs, setJobs] = useState([]);
    const [wallet, setWallet] = useState(null);
    const [transactions, setTransactions] = useState([]);
    const [availableGPUs, setAvailableGPUs] = useState([]);
    const [selectedGPU, setSelectedGPU] = useState('');
    const [topupAmt, setTopupAmt] = useState('');
    const [script, setScript] = useState(null);
    const [reqs, setReqs] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    const [logModal, setLogModal] = useState(null);
    const [logs, setLogs] = useState('');
    const fileRef = useRef();
    const reqRef = useRef();

    const load = async () => {
        try {
            const [j, w, t, g] = await Promise.all([
                api.listJobs(), api.getWallet(), api.getTransactions(), api.availableGPUs(0)
            ]);
            setJobs(j);
            setWallet(w);
            setTransactions(t);
            setAvailableGPUs(g);
        } catch (e) { console.error(e); }
    };

    useEffect(() => { load(); const iv = setInterval(load, 15000); return () => clearInterval(iv); }, []);

    const handleSubmit = async () => {
        if (!script) return;
        setSubmitting(true);
        try {
            await api.submitJob(script, reqs || undefined, selectedGPU || undefined);
            setScript(null);
            setReqs(null);
            setSelectedGPU('');
            if (fileRef.current) fileRef.current.value = '';
            if (reqRef.current) reqRef.current.value = '';
            await load();
        } catch (e) { alert(e.detail || 'Submission failed'); }
        finally { setSubmitting(false); }
    };

    const handleTopup = async () => {
        const amt = parseFloat(topupAmt);
        if (!amt || amt <= 0) return;
        try {
            await api.topUp(amt);
            setTopupAmt('');
            await load();
        } catch (e) { alert(e.detail || 'Topup failed'); }
    };

    const viewLogs = async (jobId) => {
        setLogModal(jobId);
        try {
            const res = await api.getJobLogs(jobId);
            setLogs(res.logs || 'No logs yet.');
        } catch { setLogs('Failed to load logs.'); }
    };

    const downloadLogs = () => {
        const blob = new Blob([logs], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `job_${logModal.slice(0, 8)}_logs.txt`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const statusBadge = (s) => <span className={`badge badge-${s}`}>{s}</span>;

    return (
        <div className="layout">
            <Sidebar />
            <main className="main-content">
                <div className="page-header animate-in">
                    <h2>Client Dashboard</h2>
                    <p>Submit training jobs and manage your wallet</p>
                </div>

                {/* Stat Cards */}
                <div className="grid-4 animate-in">
                    <div className="glass stat-card">
                        <span className="stat-label">Wallet Balance</span>
                        <span className="stat-value green">₹{wallet?.balance?.toFixed(2) || '0.00'}</span>
                    </div>
                    <div className="glass stat-card">
                        <span className="stat-label">Total Jobs</span>
                        <span className="stat-value cyan">{jobs.length}</span>
                    </div>
                    <div className="glass stat-card">
                        <span className="stat-label">Running</span>
                        <span className="stat-value amber">{jobs.filter(j => j.status === 'running').length}</span>
                    </div>
                    <div className="glass stat-card">
                        <span className="stat-label">GPUs Online</span>
                        <span className="stat-value green">{availableGPUs.length}</span>
                    </div>
                </div>

                {/* Available GPUs */}
                <div className="section animate-in" style={{ marginTop: '12px' }}>
                    <div className="section-title">Available GPUs</div>
                    {availableGPUs.length === 0 ? (
                        <div className="glass" style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
                            No GPUs online right now. Jobs will be queued until a GPU becomes available.
                        </div>
                    ) : (
                        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                            {availableGPUs.map(gpu => (
                                <div key={gpu.id} className="glass" style={{
                                    padding: '16px 20px', flex: '1 1 220px', maxWidth: '320px',
                                    border: selectedGPU === gpu.id ? '2px solid var(--primary)' : '2px solid transparent',
                                    cursor: 'pointer', transition: 'border 0.2s',
                                }} onClick={() => setSelectedGPU(selectedGPU === gpu.id ? '' : gpu.id)}>
                                    <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: '4px' }}>
                                        {gpu.name}
                                    </div>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                        {gpu.vram_mb} MB VRAM · CUDA {gpu.cuda_version || 'N/A'}
                                    </div>
                                    <div style={{ marginTop: '6px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                                        {statusBadge(gpu.status)}
                                        {selectedGPU === gpu.id && (
                                            <span style={{ fontSize: '0.75rem', color: 'var(--primary)', fontWeight: 600 }}>
                                                ✓ Selected
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                    {selectedGPU && (
                        <div style={{ marginTop: '8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            Selected GPU: <strong>{availableGPUs.find(g => g.id === selectedGPU)?.name}</strong>
                            {' · '}
                            <span style={{ color: 'var(--primary)', cursor: 'pointer' }}
                                onClick={() => setSelectedGPU('')}>Clear selection</span>
                        </div>
                    )}
                </div>

                <div className="grid-2">
                    {/* Job Submission */}
                    <div className="section animate-in">
                        <div className="section-title">Submit a Job</div>
                        <div className="glass" style={{ padding: '24px' }}>
                            <div className="form-group" style={{ marginBottom: '14px' }}>
                                <label>Training Script *</label>
                                <div className="upload-zone" onClick={() => fileRef.current?.click()}>
                                    <div className="upload-icon">📄</div>
                                    <p>{script ? script.name : 'Click to select your .py script'}</p>
                                    <input ref={fileRef} type="file" accept=".py" hidden
                                        onChange={e => setScript(e.target.files[0])} />
                                </div>
                            </div>
                            <div className="form-group" style={{ marginBottom: '14px' }}>
                                <label>Requirements (optional)</label>
                                <div className="upload-zone" onClick={() => reqRef.current?.click()}
                                    style={{ padding: '20px' }}>
                                    <p>{reqs ? reqs.name : 'Click to select requirements.txt'}</p>
                                    <input ref={reqRef} type="file" accept=".txt" hidden
                                        onChange={e => setReqs(e.target.files[0])} />
                                </div>
                            </div>
                            <div className="form-group" style={{ marginBottom: '14px' }}>
                                <label>Target GPU</label>
                                <select className="input" value={selectedGPU}
                                    onChange={e => setSelectedGPU(e.target.value)}
                                    style={{ cursor: 'pointer' }}>
                                    <option value="">Auto-assign (best available)</option>
                                    {availableGPUs.map(gpu => (
                                        <option key={gpu.id} value={gpu.id}>
                                            {gpu.name} — {gpu.vram_mb} MB VRAM
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <button className="btn btn-primary" onClick={handleSubmit}
                                disabled={!script || submitting} style={{ width: '100%' }}>
                                {submitting ? 'Submitting...' : selectedGPU ? 'Submit to Selected GPU' : 'Submit Job'}
                            </button>
                        </div>
                    </div>

                    {/* Wallet */}
                    <div className="section animate-in">
                        <div className="section-title">Wallet</div>
                        <div className="glass" style={{ padding: '24px' }}>
                            <div className="wallet-balance">
                                <span className="currency">₹ </span>
                                {wallet?.balance?.toFixed(2) || '0.00'}
                            </div>
                            <div className="topup-row" style={{ marginTop: '16px' }}>
                                <input className="input" type="number" placeholder="Amount"
                                    value={topupAmt} onChange={e => setTopupAmt(e.target.value)} />
                                <button className="btn btn-primary" onClick={handleTopup}>Top Up</button>
                            </div>

                            {transactions.length > 0 && (
                                <div style={{ marginTop: '16px' }}>
                                    <div className="section-title">Recent Transactions</div>
                                    <div className="table-container">
                                        <table>
                                            <thead><tr><th>Type</th><th>Amount</th><th>Date</th></tr></thead>
                                            <tbody>
                                                {transactions.slice(0, 5).map(t => (
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

                {/* Jobs Table */}
                <div className="section animate-in" style={{ marginTop: '12px' }}>
                    <div className="section-title">My Jobs</div>
                    <div className="table-container glass">
                        <table>
                            <thead>
                                <tr>
                                    <th>Job ID</th>
                                    <th>Status</th>
                                    <th>Created</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {jobs.length === 0 ? (
                                    <tr><td colSpan="5" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                                        No jobs yet. Submit your first training script above!
                                    </td></tr>
                                ) : jobs.map(j => (
                                    <tr key={j.id}>
                                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                                            {j.id.slice(0, 8)}...
                                        </td>
                                        <td>{statusBadge(j.status)}</td>
                                        <td>{new Date(j.created_at).toLocaleString()}</td>
                                        <td>
                                            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                                <button className="btn btn-ghost btn-small" onClick={() => viewLogs(j.id)}>
                                                    📋 Logs
                                                </button>
                                                {j.status === 'pending' && (
                                                    <>
                                                        <button className="btn btn-ghost btn-small" style={{ color: 'var(--red)' }}
                                                            onClick={async () => {
                                                                if (!confirm('Delete this job permanently?')) return;
                                                                try { await api.deleteJob(j.id); await load(); }
                                                                catch (e) { alert(e.detail || 'Failed to delete job'); }
                                                            }}>
                                                            🗑 Delete
                                                        </button>
                                                    </>
                                                )}
                                                {['queued', 'running'].includes(j.status) && (
                                                    <>
                                                        <button className="btn btn-danger btn-small" onClick={async () => {
                                                            if (!confirm('Are you sure you want to stop this job?')) return;
                                                            try { await api.cancelJob(j.id); await load(); }
                                                            catch (e) { alert(e.detail || 'Failed to stop job'); }
                                                        }}>
                                                            ⛔ Stop
                                                        </button>
                                                        <button className="btn btn-ghost btn-small" style={{ color: 'var(--red)' }}
                                                            onClick={async () => {
                                                                if (!confirm('Delete this job permanently?')) return;
                                                                try { await api.cancelJob(j.id); await api.deleteJob(j.id); await load(); }
                                                                catch (e) { alert(e.detail || 'Failed to delete job'); }
                                                            }}>
                                                            🗑 Delete
                                                        </button>
                                                    </>
                                                )}
                                                {['completed', 'failed', 'cancelled'].includes(j.status) && (
                                                    <button className="btn btn-ghost btn-small" style={{ color: 'var(--red)' }}
                                                        onClick={async () => {
                                                            if (!confirm('Delete this job permanently?')) return;
                                                            try { await api.deleteJob(j.id); await load(); }
                                                            catch (e) { alert(e.detail || 'Failed to delete job'); }
                                                        }}>
                                                        🗑 Delete
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Log Modal */}
                {logModal && (
                    <div className="modal-overlay" onClick={() => setLogModal(null)}>
                        <div className="modal glass-elevated" onClick={e => e.stopPropagation()}>
                            <div className="modal-header">
                                <h3>Job Logs — {logModal.slice(0, 8)}...</h3>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                    <button className="btn btn-ghost btn-small" onClick={downloadLogs}
                                        style={{ fontSize: '0.8rem' }}>
                                        ⬇ Download
                                    </button>
                                    <button className="modal-close" onClick={() => setLogModal(null)}>×</button>
                                </div>
                            </div>
                            <div className="log-viewer">
                                {logs.split('\n').map((line, i) => (
                                    <div key={i} className="log-line">{line}</div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
