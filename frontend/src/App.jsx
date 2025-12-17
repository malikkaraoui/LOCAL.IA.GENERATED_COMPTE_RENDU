import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ClientSelection from './pages/ClientSelection';
import Progress from './pages/Progress';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <h1>🤖 SCRIPT.IA - Générateur de Rapports par RAG</h1>
        </header>
        
        <main className="app-main">
          <Routes>
            <Route path="/" element={<ClientSelection />} />
            <Route path="/progress/:jobId" element={<Progress />} />
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

