import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
    const [email, setEmail] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('client');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await register({ email, username, password, role });
            navigate('/login');
        } catch (err) {
            setError(err.detail || 'Registration failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card glass-elevated animate-in">
                <h2>Create Account</h2>
                <p className="subtitle">Join the UniGPU marketplace</p>

                {error && <div className="error-msg">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>I want to</label>
                        <div className="role-selector">
                            <button type="button" className={`role-btn ${role === 'client' ? 'selected' : ''}`}
                                onClick={() => setRole('client')}>🚀 Submit Jobs</button>
                            <button type="button" className={`role-btn ${role === 'provider' ? 'selected' : ''}`}
                                onClick={() => setRole('provider')}>⚡ Share GPU</button>
                        </div>
                    </div>
                    <div className="form-group">
                        <label>Email</label>
                        <input className="input" type="email" placeholder="you@university.edu"
                            value={email} onChange={e => setEmail(e.target.value)} required />
                    </div>
                    <div className="form-group">
                        <label>Username</label>
                        <input className="input" type="text" placeholder="Choose a username"
                            value={username} onChange={e => setUsername(e.target.value)} required />
                    </div>
                    <div className="form-group">
                        <label>Password</label>
                        <input className="input" type="password" placeholder="Choose a password"
                            value={password} onChange={e => setPassword(e.target.value)} required />
                    </div>
                    <button className="btn btn-primary" type="submit" disabled={loading}
                        style={{ width: '100%', marginTop: '8px' }}>
                        {loading ? 'Creating...' : 'Create Account'}
                    </button>
                </form>

                <div className="auth-footer">
                    Already have an account? <Link to="/login">Sign In</Link>
                </div>
            </div>
        </div>
    );
}
