import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import api from '../api/client';

export default function AdminDashboard() {
    const [stats, setStats] = useState(null);
    const [gpus, setGPUs] = useState([]);
    const [jobs, setJobs] = useState([]);
    const [users, setUsers] = useState([]);
    const [tab, setTab] = useState('overview');

    const load = async () => {
        try {
            const [s, g, j, u] = await Promise.all([
                api.adminStats(), api.adminGPUs(), api.adminJobs(), api.adminUsers(),
            ]);
            setStats(s);
            setGPUs(g);
            setJobs(j);
            setUsers(u);
        } catch (e) { console.error(e); }
    };

    useEffect(() => { load(); }, []);

    const statusBadge = (s) => <span className={`badge badge-${s}`}>{s}</span>;

    const tabs = [
        { key: 'overview', label: 'Overview', icon: '📊' },
        { key: 'gpus', label: 'GPU Fleet', icon: '🖥️' },
        { key: 'jobs', label: 'Jobs', icon: '⚡' },
        { key: 'users', label: 'Users', icon: '👥' },
    ];

    return (
        <div className="layout">
            <Sidebar />
            <main className="main-content">
                <div className="page-header animate-in">
                    <h2>Admin Dashboard</h2>
                    <p>Platform overview and management</p>
                </div>

                {/* Tab Navigation */}
                <div style={{ display: 'flex', gap: '4px', marginBottom: '24px' }} className="animate-in">
                    {tabs.map(t => (
                        <button key={t.key}
                            className={`btn ${tab === t.key ? 'btn-primary' : 'btn-ghost'} btn-small`}
                            onClick={() => setTab(t.key)}>
                            {t.icon} {t.label}
                        </button>
                    ))}
                </div>

                {/* Overview Tab */}
                {tab === 'overview' && (
                    <>
                        <div className="grid-4 animate-in">
                            <div className="glass stat-card">
                                <span className="stat-label">Total GPUs</span>
                                <span className="stat-value cyan">{stats?.total_gpus ?? '-'}</span>
                            </div>
                            <div className="glass stat-card">
                                <span className="stat-label">Online GPUs</span>
                                <span className="stat-value green">{stats?.online_gpus ?? '-'}</span>
                            </div>
                            <div className="glass stat-card">
                                <span className="stat-label">Total Jobs</span>
                                <span className="stat-value purple">{stats?.total_jobs ?? '-'}</span>
                            </div>
                            <div className="glass stat-card">
                                <span className="stat-label">Total Users</span>
                                <span className="stat-value amber">{stats?.total_users ?? '-'}</span>
                            </div>
                        </div>

                        <div className="grid-2 animate-in">
                            <div className="section">
                                <div className="section-title">Recent Jobs</div>
                                <div className="table-container glass">
                                    <table>
                                        <thead><tr><th>Job ID</th><th>Status</th><th>Created</th></tr></thead>
                                        <tbody>
                                            {jobs.slice(0, 5).map(j => (
                                                <tr key={j.id}>
                                                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                                                        {j.id.slice(0, 8)}...
                                                    </td>
                                                    <td>{statusBadge(j.status)}</td>
                                                    <td>{new Date(j.created_at).toLocaleString()}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            <div className="section">
                                <div className="section-title">GPU Fleet Status</div>
                                <div className="table-container glass">
                                    <table>
                                        <thead><tr><th>GPU</th><th>VRAM</th><th>Status</th></tr></thead>
                                        <tbody>
                                            {gpus.slice(0, 5).map(g => (
                                                <tr key={g.id}>
                                                    <td style={{ fontWeight: 600 }}>{g.name}</td>
                                                    <td>{g.vram_mb} MB</td>
                                                    <td>{statusBadge(g.status)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </>
                )}

                {/* GPU Fleet Tab */}
                {tab === 'gpus' && (
                    <div className="section animate-in">
                        <div className="table-container glass">
                            <table>
                                <thead>
                                    <tr><th>GPU Name</th><th>VRAM</th><th>CUDA</th><th>Status</th><th>Last Heartbeat</th></tr>
                                </thead>
                                <tbody>
                                    {gpus.map(g => (
                                        <tr key={g.id}>
                                            <td style={{ fontWeight: 600 }}>{g.name}</td>
                                            <td>{g.vram_mb} MB</td>
                                            <td>{g.cuda_version || '-'}</td>
                                            <td>{statusBadge(g.status)}</td>
                                            <td>{g.last_heartbeat ? new Date(g.last_heartbeat).toLocaleString() : 'Never'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Jobs Tab */}
                {tab === 'jobs' && (
                    <div className="section animate-in">
                        <div className="table-container glass">
                            <table>
                                <thead>
                                    <tr><th>Job ID</th><th>Client</th><th>GPU</th><th>Status</th><th>Created</th></tr>
                                </thead>
                                <tbody>
                                    {jobs.map(j => (
                                        <tr key={j.id}>
                                            <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                                                {j.id.slice(0, 8)}...
                                            </td>
                                            <td>{j.client_id?.slice(0, 8) || '-'}...</td>
                                            <td>{j.gpu_id ? j.gpu_id.slice(0, 8) + '...' : 'Unassigned'}</td>
                                            <td>{statusBadge(j.status)}</td>
                                            <td>{new Date(j.created_at).toLocaleString()}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Users Tab */}
                {tab === 'users' && (
                    <div className="section animate-in">
                        <div className="table-container glass">
                            <table>
                                <thead>
                                    <tr><th>Username</th><th>Email</th><th>Role</th><th>Joined</th></tr>
                                </thead>
                                <tbody>
                                    {users.map(u => (
                                        <tr key={u.id}>
                                            <td style={{ fontWeight: 600 }}>{u.username}</td>
                                            <td>{u.email}</td>
                                            <td>{statusBadge(u.role)}</td>
                                            <td>{new Date(u.created_at).toLocaleDateString()}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
