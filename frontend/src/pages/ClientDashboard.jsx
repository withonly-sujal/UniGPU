import { useState, useEffect, useRef } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../api/client';

export default function ClientDashboard() {
    const [jobs, setJobs] = useState([]);
    const [wallet, setWallet] = useState(null);
    const [transactions, setTransactions] = useState([]);
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
            const [j, w, t] = await Promise.all([api.listJobs(), api.getWallet(), api.getTransactions()]);
            setJobs(j);
            setWallet(w);
            setTransactions(t);
        } catch (e) { console.error(e); }
    };

    useEffect(() => { load(); }, []);

    const handleSubmit = async () => {
        if (!script) return;
        setSubmitting(true);
        try {
            await api.submitJob(script, reqs || undefined);
            setScript(null);
            setReqs(null);
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
                        <span className="stat-value green">${wallet?.balance?.toFixed(2) || '0.00'}</span>
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
                        <span className="stat-label">Completed</span>
                        <span className="stat-value purple">{jobs.filter(j => j.status === 'completed').length}</span>
                    </div>
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
                            <button className="btn btn-primary" onClick={handleSubmit}
                                disabled={!script || submitting} style={{ width: '100%' }}>
                                {submitting ? 'Submitting...' : 'Submit Job'}
                            </button>
                        </div>
                    </div>

                    {/* Wallet */}
                    <div className="section animate-in">
                        <div className="section-title">Wallet</div>
                        <div className="glass" style={{ padding: '24px' }}>
                            <div className="wallet-balance">
                                <span className="currency">$ </span>
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
                                    <tr><td colSpan="4" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
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
                                            <button className="btn btn-ghost btn-small" onClick={() => viewLogs(j.id)}>
                                                View Logs
                                            </button>
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
                                <button className="modal-close" onClick={() => setLogModal(null)}>×</button>
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
