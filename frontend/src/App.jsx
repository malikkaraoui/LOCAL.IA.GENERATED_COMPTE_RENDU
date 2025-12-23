import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { useMemo, useState } from 'react';
import ClientSelection from './pages/ClientSelection';
import Progress from './pages/Progress';
import Branding from './pages/Branding';
import Training from './pages/Training';
import { reportsAPI } from './services/api';
import './App.css';

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

  const jobId = useMemo(() => {
    const m = String(location.pathname || '').match(/^\/progress\/([^/]+)(?:\/|$)/);
    return m ? decodeURIComponent(m[1]) : null;
  }, [location.pathname]);

  const handleKill = async () => {
    if (!jobId || killBusy) return;
    const ok = window.confirm(
      `Stopper immédiatement la génération (job ${jobId}) ?\n\nLe job sera marqué FAILED/annulé et le résultat sera perdu.`
    );
    if (!ok) return;

    setKillBusy(true);
    setKillError(null);
    try {
      await reportsAPI.deleteReport(jobId, { force: true });
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

