import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Landing() {
    const { user } = useAuth();

    return (
        <div className="landing">
            <nav className="landing-nav">
                <span className="brand">⬡ UniGPU</span>
                <div className="nav-btns">
                    {user ? (
                        <Link to="/dashboard" className="btn btn-primary">Dashboard</Link>
                    ) : (
                        <>
                            <Link to="/login" className="btn btn-ghost">Log In</Link>
                            <Link to="/register" className="btn btn-primary">Get Started</Link>
                        </>
                    )}
                </div>
            </nav>

            <section className="hero">
                <h1>
                    Share GPUs.<br />
                    <span className="gradient-text">Train Faster.</span>
                </h1>
                <p>
                    UniGPU connects idle student GPUs into a powerful compute marketplace.
                    Submit training jobs, share your GPU, and earn — all peer-to-peer.
                </p>
                <div className="hero-buttons">
                    <Link to="/register" className="btn btn-primary">Start Sharing</Link>
                    <Link to="/register" className="btn btn-secondary">Submit a Job</Link>
                </div>
            </section>

            <section className="features">
                <div className="feature-card glass animate-in">
                    <div className="feature-icon">🚀</div>
                    <h3>Submit Jobs</h3>
                    <p>Upload your training script and requirements. We find the best GPU and run it for you.</p>
                </div>
                <div className="feature-card glass animate-in" style={{ animationDelay: '0.1s' }}>
                    <div className="feature-icon">⚡</div>
                    <h3>Share Your GPU</h3>
                    <p>Install the lightweight agent on your machine. Earn credits while your GPU is idle.</p>
                </div>
                <div className="feature-card glass animate-in" style={{ animationDelay: '0.2s' }}>
                    <div className="feature-icon">🔒</div>
                    <h3>Secure & Isolated</h3>
                    <p>Every job runs inside a Docker container with resource limits. Your machine stays safe.</p>
                </div>
            </section>

            <footer style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                UniGPU — Peer-to-Peer GPU Marketplace · Built for Students
            </footer>
        </div>
    );
}
