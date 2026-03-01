import { Link } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowLeft, faLightbulb, faWrench, faUsers, faGraduationCap, faBriefcase } from '@fortawesome/free-solid-svg-icons';
import { Cloudinary } from '@cloudinary/url-gen';
import { AdvancedImage } from '@cloudinary/react';
import { fill } from '@cloudinary/url-gen/actions/resize';

// Initialize Cloudinary instance
const cld = new Cloudinary({
    cloud: {
        cloudName: 'dq6vf9rhv'
    }
});

export default function AboutUs() {
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

            <div className="main-content" style={{ maxWidth: '900px', margin: '0 auto', padding: '60px 30px', flex: 1 }}>
                <div className="page-header" style={{ textAlign: 'center', marginBottom: '80px' }}>
                    <h1 style={{ fontSize: '3.5rem', fontWeight: 800, marginBottom: '24px', letterSpacing: '-0.03em' }}>
                        About <span className="gradient-text">UniGPU</span>
                    </h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '1.25rem', lineHeight: '1.7', maxWidth: '700px', margin: '0 auto' }}>
                        Transforming idle student hardware into a powerful, accessible, and distributed compute network.
                    </p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '60px', marginBottom: '80px' }}>
                    {/* The Problem */}
                    <div className="glass-elevated" style={{ padding: '50px 40px', borderRadius: 'var(--radius-xl)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
                            <div className="feature-icon" style={{ fontSize: '1.8rem', color: 'var(--accent)', background: 'rgba(255, 62, 165, 0.1)', padding: '16px', borderRadius: '12px' }}>
                                <FontAwesomeIcon icon={faLightbulb} />
                            </div>
                            <h2 style={{ fontSize: '2rem', margin: 0, fontWeight: 700 }}>The Problem</h2>
                        </div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', lineHeight: '1.8' }}>
                            <p style={{ marginBottom: '16px' }}>
                                High-performance GPUs are expensive and inaccessible to many students, researchers, and early-stage startups. Training machine learning models, rendering graphics, and running GPU-accelerated workloads require powerful hardware that most individuals cannot afford.
                            </p>
                            <p style={{ marginBottom: '16px' }}>
                                At the same time, thousands of personal GPUs remain idle for long hours every day in student laptops and desktops. This creates a massive imbalance where compute demand is incredibly high, but distributed unused GPU resources are completely wasted.
                            </p>
                            <p style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                                Ultimately, the problem is the lack of an affordable, secure, and accessible platform that connects idle GPU providers with users who desperately need temporary high-performance compute power.
                            </p>
                        </div>
                    </div>

                    {/* The Solution */}
                    <div className="glass-elevated" style={{ padding: '50px 40px', borderRadius: 'var(--radius-xl)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
                            <div className="feature-icon" style={{ fontSize: '1.8rem', color: 'var(--cyan)', background: 'rgba(0, 240, 255, 0.1)', padding: '16px', borderRadius: '12px' }}>
                                <FontAwesomeIcon icon={faWrench} />
                            </div>
                            <h2 style={{ fontSize: '2rem', margin: 0, fontWeight: 700 }}>How We Solve It</h2>
                        </div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', lineHeight: '1.8' }}>
                            <p style={{ marginBottom: '16px' }}>
                                UniGPU is a centralized peer-to-peer GPU compute marketplace. It allows students to effortlessly rent out their idle GPUs and earn money, while simultaneously allowing clients to remotely execute heavy GPU-intensive workloads (like machine learning training, Blender rendering, and AI inference).
                            </p>
                            <p style={{ marginBottom: '16px' }}>
                                Our platform securely connects clients and providers through a robust backend orchestration system. Clients upload their workloads, which are then executed inside secure, isolated Docker containers on provider machines leveraging NVIDIA or AMD GPU runtimes.
                            </p>
                            <p>
                                We handle all the heavy lifting in the background: scheduling, secure execution, real-time telemetry monitoring, and usage-based billing.
                            </p>
                        </div>
                    </div>
                </div>

                {/* The Team */}
                <div style={{ marginBottom: '40px' }}>
                    <div style={{ textAlign: 'center', marginBottom: '40px' }}>
                        <div className="feature-icon" style={{ fontSize: '2rem', color: 'var(--purple)', marginBottom: '16px', display: 'inline-block' }}>
                            <FontAwesomeIcon icon={faUsers} />
                        </div>
                        <h2 style={{ fontSize: '2.5rem', fontWeight: 800, margin: 0 }}>Developed By</h2>
                    </div>

                    <div className="grid-2" style={{ gap: '30px' }}>
                        {/* Swanand Wakadmane */}
                        <div className="glass-elevated team-card" style={{ padding: '40px 30px', borderRadius: 'var(--radius-xl)', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            {/* Cloudinary Image */}
                            <AdvancedImage
                                cldImg={cld.image('Profile_Picture_1_baeuuo').resize(fill().width(120).height(120))}
                                style={{ width: '120px', height: '120px', borderRadius: '50%', marginBottom: '24px', border: '2px solid var(--border)', objectFit: 'cover' }}
                                alt="Swanand Wakadmane"
                            />
                            <h3 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 8px 0', color: 'var(--text-primary)' }}>Swanand Wakadmane</h3>
                            <p style={{ color: 'var(--cyan)', fontWeight: 600, fontSize: '1rem', margin: '0 0 24px 0' }}>Co-founder & Developer</p>

                            <div style={{ width: '100%', textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                <div>
                                    <h4 style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <FontAwesomeIcon icon={faGraduationCap} /> Education
                                    </h4>
                                    <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.95rem', lineHeight: '1.5' }}>
                                        [Insert Education Details Here] <br />
                                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Class of 202X</span>
                                    </p>
                                </div>
                                <div>
                                    <h4 style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <FontAwesomeIcon icon={faBriefcase} /> Experience & Skills
                                    </h4>
                                    <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.95rem', lineHeight: '1.5' }}>
                                        [Add a short bio, relevant experience, or key technical skills here.]
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Sujal Kadam */}
                        <div className="glass-elevated team-card" style={{ padding: '40px 30px', borderRadius: 'var(--radius-xl)', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                            {/* Cloudinary Image */}
                            <AdvancedImage
                                cldImg={cld.image('sujal_wumrpa').resize(fill().width(120).height(120))}
                                style={{ width: '120px', height: '120px', borderRadius: '50%', marginBottom: '24px', border: '2px solid var(--border)', objectFit: 'cover' }}
                                alt="Sujal Kadam"
                            />
                            <h3 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 8px 0', color: 'var(--text-primary)' }}>Sujal Kadam</h3>
                            <p style={{ color: 'var(--purple)', fontWeight: 600, fontSize: '1rem', margin: '0 0 24px 0' }}>Co-founder & Developer</p>

                            <div style={{ width: '100%', textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                <div>
                                    <h4 style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <FontAwesomeIcon icon={faGraduationCap} /> Education
                                    </h4>
                                    <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.95rem', lineHeight: '1.5' }}>
                                        [Insert Education Details Here] <br />
                                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Class of 202X</span>
                                    </p>
                                </div>
                                <div>
                                    <h4 style={{ fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <FontAwesomeIcon icon={faBriefcase} /> Experience & Skills
                                    </h4>
                                    <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.95rem', lineHeight: '1.5' }}>
                                        [Add a short bio, relevant experience, or key technical skills here.]
                                    </p>
                                </div>
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
