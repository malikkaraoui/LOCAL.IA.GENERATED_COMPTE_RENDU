import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { useMemo, useState } from 'react';
import ClientSelection from './pages/ClientSelection';
import Progress from './pages/Progress';
import Branding from './pages/Branding';
import Training from './pages/Training';
import ReportReview from './pages/ReportReview';
import { reportsAPI } from './services/api';
import './App.css';

function buildBackendUrl(pathname) {
  // On se base sur VITE_API_URL si fourni, sinon on suit la valeur par défaut du client API.
  // Exemples attendus:
  // - VITE_API_URL=http://localhost:8000/api     -> http://localhost:8000/api/docs
  // - VITE_API_URL=http://localhost:8000/api/    -> http://localhost:8000/api/docs
  // - VITE_API_URL=http://localhost:8000         -> http://localhost:8000/api/docs
  const raw = import.meta?.env?.VITE_API_URL || 'http://localhost:8000/api';
  const base = String(raw).replace(/\/+$/, '');
  const root = base.endsWith('/api') ? base : `${base}/api`;
  const cleanPath = String(pathname || '').startsWith('/') ? pathname : `/${pathname}`;
  return `${root}${cleanPath}`;
}

function buildStreamlitUrl(pathname) {
  // Permet de relier l'UI Streamlit (port 8501) depuis le frontend.
  // Priorité: VITE_STREAMLIT_URL, sinon on dérive depuis l'hôte courant.
  const raw = import.meta?.env?.VITE_STREAMLIT_URL;
  if (raw) {
    const base = String(raw).replace(/\/+$/, '');
    const cleanPath = String(pathname || '').startsWith('/') ? pathname : `/${pathname}`;
    return `${base}${cleanPath}`;
  }

  try {
    const { protocol, hostname } = window.location;
    const cleanPath = String(pathname || '').startsWith('/') ? pathname : `/${pathname}`;
    return `${protocol}//${hostname}:8501${cleanPath}`;
  } catch {
    const cleanPath = String(pathname || '').startsWith('/') ? pathname : `/${pathname}`;
    return `http://localhost:8501${cleanPath}`;
  }
}

function extractApiErrorDetail(err) {
  const detail = err?.response?.data?.detail;
  if (!detail) return null;
  if (typeof detail === 'string') return detail;
  if (typeof detail === 'object') {
    const msg = detail.message || detail.error || null;
    const hints = Array.isArray(detail.hints) ? detail.hints.filter(Boolean).join(' • ') : null;
    return [msg, hints].filter(Boolean).join(' — ');
  }
  return String(detail);
}

function AppHeader() {
  const location = useLocation();
  const navigate = useNavigate();
  const [killBusy, setKillBusy] = useState(false);
  const [killError, setKillError] = useState(null);

  const apiDocsUrl = useMemo(() => buildBackendUrl('/docs'), []);
  const apiHealthUrl = useMemo(() => buildBackendUrl('/health'), []);
  const streamlitUrl = useMemo(() => buildStreamlitUrl('/'), []);

  const jobId = useMemo(() => {
    const m = String(location.pathname || '').match(/^\/progress\/([^/]+)(?:\/|$)/);
    return m ? decodeURIComponent(m[1]) : null;
  }, [location.pathname]);

  const handleKill = async () => {
    if (!jobId || killBusy) return;
    const ok = window.confirm(
      `Demander l'annulation de la génération (job ${jobId}) ?\n\nLe job sera stoppé dès que possible et le résultat sera perdu.`
    );
    if (!ok) return;

    setKillBusy(true);
    setKillError(null);
    try {
      await reportsAPI.cancelReport(jobId);
      navigate('/', { replace: true });
    } catch (err) {
      setKillError(extractApiErrorDetail(err) || 'Erreur lors de l\'arrêt du job');
    } finally {
      setKillBusy(false);
    }
  };

  return (
    <header className="app-header">
      <h1>🤖 SCRIPT.IA - Générateur de Rapports par RAG</h1>
      <nav className="app-nav">
        <Link to="/">Rapports</Link>
        <span className="sep">•</span>
        <Link to="/branding">Branding DOCX</Link>
        <span className="sep">•</span>
        <Link to="/training">Entraînement</Link>

        <span className="sep">•</span>
        <a href={apiDocsUrl} target="_blank" rel="noreferrer" title="Ouvrir la documentation Swagger du backend">
          API
        </a>
        <span className="sep">•</span>
        <a href={apiHealthUrl} target="_blank" rel="noreferrer" title="Vérifier l'état du backend (healthcheck)">
          Serveur
        </a>
        <span className="sep">•</span>
        <a href={streamlitUrl} target="_blank" rel="noreferrer" title="Ouvrir l'interface d'entraînement Streamlit (port 8501)">
          Entraînement (8501)
        </a>

        {jobId && (
          <>
            <span className="sep">•</span>
            <button
              type="button"
              className="btn-danger btn-sm"
              onClick={handleKill}
              disabled={killBusy}
              title="Arrêter la génération en cours"
            >
              {killBusy ? 'Arrêt…' : '🛑 Kill'}
            </button>
          </>
        )}
      </nav>
      {killError && <div className="app-nav-error">{killError}</div>}
    </header>
  );
}

function App() {
  return (
    <Router>
      <div className="app">
        <AppHeader />
        
        <main className="app-main">
          <Routes>
            <Route path="/" element={<ClientSelection />} />
            <Route path="/progress/:jobId" element={<Progress />} />
            <Route path="/branding" element={<Branding />} />
            <Route path="/training" element={<Training />} />
            <Route path="/review/:jobId" element={<ReportReview />} />
          </Routes>
        </main>
        
        <footer className="app-footer">
          <p>© 2024 SCRIPT.IA - Powered by FastAPI + React + Malik 😉 </p>
        </footer>
      </div>
    </Router>
  );
}

export default App;

