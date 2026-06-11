import { useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import "./Home.css";

export default function Home() {
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // Trigger the loaded state after mount for transition effects
    const timer = setTimeout(() => setLoaded(true), 100);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="home-page">
      {/* ===== Navbar ===== */}
      <nav className="home-navbar" id="home-navbar">
        <a href="/" className="navbar-logo">
          <img src="/car_Logo.png" alt="AutoSense Logo" className="navbar-logo-img" />
        </a>
        <ul className="navbar-links">
          <li><a href="/">Home</a></li>
          <li><a href="#services">Services</a></li>
          <li><a href="#contacts">Contacts</a></li>
        </ul>
      </nav>

      {/* ===== Hero Section with Video ===== */}
      <section className="hero-section" id="hero-section">
        <video
          ref={videoRef}
          className="hero-video"
          src="/hero-video.mp4"
          autoPlay
          muted
          loop
          playsInline
        />
        <div className="hero-overlay" />

        <div className="hero-content">
          <h1 className="hero-title">
            Auto<span className="title-highlight">Sense</span>
          </h1>
          <p className="hero-description">
            AutoSense uses AI to analyze simulated vehicle data, detect issues,
            and provide a clear health score for smarter maintenance.
          </p>
        </div>

        {/* Scroll indicator */}
        <div className="scroll-indicator">
          <div className="scroll-mouse" />
          <span>Scroll</span>
        </div>
      </section>

      {/* ===== CTA Section (Below Hero) ===== */}
      <section className="cta-section" id="cta-section">
        <div className="cta-divider" />
        <p className="cta-label">Ready to diagnose?</p>
        <button
          className="cta-button"
          id="start-simulation-btn"
          onClick={() => navigate("/dashboard")}
        >
          Start Simulation
          <span className="cta-button-arrow">→</span>
        </button>
      </section>
    </div>
  );
}