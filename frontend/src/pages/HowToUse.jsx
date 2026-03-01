import { Link } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowLeft, faRocket, faServer } from '@fortawesome/free-solid-svg-icons';

export default function HowToUse() {
    return (
        <div className="landing" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
            <nav className="landing-nav" style={{ padding: '20px 40px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Link to="/" className="brand" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span className="logo-icon" style={{ fontSize: '1.4rem' }}>⬡</span> UniGPU
                </Link>
                <div className="nav-btns">
                    <Link to="/" className="btn btn-ghost" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem' }}>
                        <FontAwesomeIcon icon={faArrowLeft} /> Back to Home
                    </Link>
                </div>
            </nav>

            <div className="main-content" style={{ maxWidth: '800px', margin: '0 auto', padding: '60px 30px', flex: 1 }}>
                <div className="page-header" style={{ textAlign: 'center', marginBottom: '60px' }}>
                    <h1 style={{ fontSize: '3rem', fontWeight: 800, marginBottom: '20px', letterSpacing: '-0.02em' }}>How to Use UniGPU</h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '1.15rem', lineHeight: '1.6', maxWidth: '600px', margin: '0 auto' }}>
                        A simple guide to submitting your training jobs and earning credits by sharing your GPU.
                    </p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '60px' }}>
                    {/* Client Section */}
                    <div className="glass-elevated" style={{ padding: '50px 40px', borderRadius: 'var(--radius-xl)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
                            <div className="feature-icon" style={{ fontSize: '1.8rem', color: 'var(--cyan)' }}>
                                <FontAwesomeIcon icon={faRocket} />
                            </div>
                            <h2 style={{ fontSize: '1.8rem', margin: 0, fontWeight: 700 }}>For Clients</h2>
                        </div>

                        <div className="sop-section" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                            <div>
                                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <span style={{ color: 'var(--cyan)', fontWeight: 800 }}>01</span> Prepare
                                </h3>
                                <ul style={{ color: 'var(--text-secondary)', paddingLeft: '34px', margin: 0, display: 'flex', flexDirection: 'column', gap: '12px', lineHeight: '1.7' }}>
                                    <li>Write your PyTorch/TensorFlow training script (e.g., <code>train.py</code>).</li>
                                    <li>Create a <code>requirements.txt</code> file in the same folder with your pip dependencies.</li>
                                    <li>Zip everything into a single <code>.zip</code> file.</li>
                                </ul>
                            </div>

                            <div>
                                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <span style={{ color: 'var(--cyan)', fontWeight: 800 }}>02</span> Submit
                                </h3>
                                <ul style={{ color: 'var(--text-secondary)', paddingLeft: '34px', margin: 0, display: 'flex', flexDirection: 'column', gap: '12px', lineHeight: '1.7' }}>
                                    <li>Log into the Client Dashboard.</li>
                                    <li>Upload your <code>.zip</code> file via the Submit Job form.</li>
                                    <li>Specify your entrypoint (e.g., <code>train.py</code>) and hit submit. The network will automatically allocate a GPU.</li>
                                </ul>
                            </div>

                            <div>
                                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <span style={{ color: 'var(--cyan)', fontWeight: 800 }}>03</span> Monitor
                                </h3>
                                <ul style={{ color: 'var(--text-secondary)', paddingLeft: '34px', margin: 0, display: 'flex', flexDirection: 'column', gap: '12px', lineHeight: '1.7' }}>
                                    <li>Track job status in your dashboard table.</li>
                                    <li>Click <strong>View Logs</strong> to watch a real-time terminal of your job.</li>
                                    <li>You can safely <strong>Stop</strong> or <strong>Delete</strong> jobs at any time from the actions menu.</li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    {/* Provider Section */}
                    <div className="glass-elevated" style={{ padding: '50px 40px', borderRadius: 'var(--radius-xl)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '32px' }}>
                            <div className="feature-icon" style={{ fontSize: '1.8rem', color: 'var(--purple)' }}>
                                <FontAwesomeIcon icon={faServer} />
                            </div>
                            <h2 style={{ fontSize: '1.8rem', margin: 0, fontWeight: 700 }}>For Providers</h2>
                        </div>

                        <div className="sop-section" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                            <div>
                                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <span style={{ color: 'var(--purple)', fontWeight: 800 }}>01</span> Setup
                                </h3>
                                <ul style={{ color: 'var(--text-secondary)', paddingLeft: '34px', margin: 0, display: 'flex', flexDirection: 'column', gap: '12px', lineHeight: '1.7' }}>
                                    <li>Install Python, Docker, and the NVIDIA Container Toolkit on your machine.</li>
                                    <li>Download the <strong>UniGPU Agent</strong> from your Provider Dashboard.</li>
                                    <li>Run <code>pip install -r requirements.txt</code> in the agent folder.</li>
                                </ul>
                            </div>

                            <div>
                                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <span style={{ color: 'var(--purple)', fontWeight: 800 }}>02</span> Connect
                                </h3>
                                <ul style={{ color: 'var(--text-secondary)', paddingLeft: '34px', margin: 0, display: 'flex', flexDirection: 'column', gap: '12px', lineHeight: '1.7' }}>
                                    <li>Start the agent using <code>python run.py</code>.</li>
                                    <li>The agent will automatically authenticate and connect securely via WebSockets.</li>
                                    <li>Leave it running in the background. It will automatically download jobs, build containers, and stream logs.</li>
                                </ul>
                            </div>

                            <div>
                                <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <span style={{ color: 'var(--purple)', fontWeight: 800 }}>03</span> Earn & Monitor
                                </h3>
                                <ul style={{ color: 'var(--text-secondary)', paddingLeft: '34px', margin: 0, display: 'flex', flexDirection: 'column', gap: '12px', lineHeight: '1.7' }}>
                                    <li>Open your Provider Dashboard to see your live telemetry.</li>
                                    <li>Monitor real-time GPU Usage, Memory, Temperature, and CPU load.</li>
                                    <li>Earn credits completely automatically while the agent safely processes queued jobs.</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <footer style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)', fontSize: '0.85rem', borderTop: '1px solid var(--border)' }}>
                UniGPU - Peer-to-Peer GPU Marketplace - Built for Students - By Students <br />
                © 2026 UniGPU. All rights reserved.
            </footer>
        </div>
    );
}
