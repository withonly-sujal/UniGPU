import { Link } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowLeft, faDownload, faTerminal } from '@fortawesome/free-solid-svg-icons';
import { faWindows, faLinux, faApple } from '@fortawesome/free-brands-svg-icons';

export default function Download() {
    return (
        <div className="landing" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
            <nav className="landing-nav" style={{ padding: '20px 40px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Link to="/" className="brand" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span className="logo-icon" style={{ fontSize: '1.4rem' }}>⬡</span> UniGPU
                </Link>
                <div className="nav-btns" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <Link to="/" className="btn btn-ghost" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem' }}>
                        <FontAwesomeIcon icon={faArrowLeft} /> Back to Home
                    </Link>
                </div>
            </nav>

            <div className="main-content" style={{ maxWidth: '900px', margin: '0 auto', padding: '60px 30px', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>

                <div className="glass-elevated" style={{ padding: '60px 40px', borderRadius: 'var(--radius-xl)', textAlign: 'center', width: '100%', maxWidth: '700px' }}>
                    <div className="feature-icon" style={{ fontSize: '3rem', color: 'var(--cyan)', marginBottom: '24px', display: 'inline-block' }}>
                        <FontAwesomeIcon icon={faDownload} />
                    </div>

                    <h1 style={{ fontSize: '3rem', fontWeight: 800, marginBottom: '16px', letterSpacing: '-0.03em' }}>
                        Download <span className="gradient-text">Agent</span>
                    </h1>

                    <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', lineHeight: '1.6', marginBottom: '40px' }}>
                        Ready to share your idle GPU and earn credits? Download the UniGPU agent executable below to get started connecting to the network.
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', alignItems: 'center' }}>
                        {/* Windows Download Button */}
                        <a
                            href="https://drive.google.com/drive/folders/1hWBlrREX4sN9YadDd1aFh1V-ogHUW0W-?usp=sharing"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-primary"
                            style={{ padding: '16px 32px', fontSize: '1.1rem', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '400px', display: 'flex', justifyContent: 'center', gap: '12px' }}
                        >
                            <FontAwesomeIcon icon={faWindows} style={{ fontSize: '1.3rem' }} />
                            Download for Windows (.exe)
                        </a>

                        {/* Other Platforms Mention */}
                        <div style={{ display: 'flex', gap: '16px', color: 'var(--text-muted)', fontSize: '0.95rem' }}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <FontAwesomeIcon icon={faLinux} /> Linux support coming soon
                            </span>
                            <span>•</span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <FontAwesomeIcon icon={faApple} /> macOS support coming soon
                            </span>
                        </div>
                    </div>

                    <div style={{ marginTop: '50px', paddingTop: '30px', borderTop: '1px solid var(--border)', textAlign: 'left' }}>
                        <h3 style={{ fontSize: '1.1rem', marginBottom: '16px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <FontAwesomeIcon icon={faTerminal} style={{ color: 'var(--purple)' }} /> Command Line Verification
                        </h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: '12px' }}>
                            After downloading, you can verify the executable by opening your terminal or command prompt and running it with the help flag:
                        </p>
                        <div style={{ background: 'var(--bg-deep)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', fontFamily: 'var(--font-mono)', color: 'var(--cyan)', fontSize: '0.9rem' }}>
                            .\unigpu-agent.exe --help
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
