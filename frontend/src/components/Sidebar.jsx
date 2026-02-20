import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV = {
    client: [
        { to: '/dashboard/client', icon: '📊', label: 'Dashboard' },
    ],
    provider: [
        { to: '/dashboard/provider', icon: '📊', label: 'Dashboard' },
    ],
    admin: [
        { to: '/dashboard/admin', icon: '📊', label: 'Dashboard' },
    ],
};

export default function Sidebar() {
    const { user, logout } = useAuth();
    const links = NAV[user?.role] || [];

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <span className="logo-icon">⬡</span>
                <h1>UniGPU</h1>
            </div>

            <nav className="sidebar-nav">
                {links.map(l => (
                    <NavLink key={l.to} to={l.to}
                        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        <span className="nav-icon">{l.icon}</span>
                        {l.label}
                    </NavLink>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                    Signed in as <strong style={{ color: 'var(--text-secondary)' }}>{user?.username}</strong>
                    <br />
                    <span className="badge badge-online" style={{ marginTop: '4px' }}>{user?.role}</span>
                </div>
                <button className="btn btn-ghost btn-small" onClick={logout} style={{ width: '100%' }}>
                    Sign Out
                </button>
            </div>
        </aside>
    );
}
