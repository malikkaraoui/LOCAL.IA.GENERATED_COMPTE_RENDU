import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { reportsAPI } from '../services/api';
import './Progress.css';

/**
 * Page de suivi de la progression du rapport avec SSE.
 */
function Progress() {
  const { jobId } = useParams();
  const [status, setStatus] = useState('PENDING');
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [completed, setCompleted] = useState(false);
  const [fieldProgress, setFieldProgress] = useState(null);
  const [fieldOrder, setFieldOrder] = useState(null);

  const FIELD_STAGE_LABELS = {
    pending: 'En attente',
    start: 'Préparation',
    context: 'Contexte prêt',
    prompt: 'Prompt envoyé',
    response: 'Réponse reçue',
    retry: 'Correction',
    done: 'Terminé',
    warning: 'Réponse vide',
    error: 'Erreur',
  };

  const FIELD_STAGE_ICONS = {
    pending: '⏳',
    start: '⚙️',
    context: '📚',
    prompt: '📤',
    response: '📥',
    retry: '♻️',
    done: '✅',
    warning: '⚠️',
    error: '❌',
  };

  const humanizeDelta = (seconds) => {
    if (seconds < 1) return 'juste maintenant';
    if (seconds < 60) return `${Math.floor(seconds)} s`;
    const minutes = Math.floor(seconds / 60);
    const rest = Math.floor(seconds % 60);
    if (minutes < 60) return `${minutes} min ${String(rest).padStart(2, '0')} s`;
    const hours = Math.floor(minutes / 60);
    const m = minutes % 60;
    return `${hours} h ${m} min`;
  };

  const mergeProgressPayload = (data) => {
    if (!data) return;
    if (data.field_progress) setFieldProgress(data.field_progress);
    if (data.field_order) setFieldOrder(data.field_order);
  };

  useEffect(() => {
    if (!jobId) return;

    // Connexion SSE pour suivre la progression
    const eventSource = reportsAPI.streamReportProgress(
      jobId,
      (message) => {
        switch (message.type) {
          case 'status':
            setStatus(message.data.status);
            mergeProgressPayload(message.data);
            break;
          
          case 'log':
            setLogs((prev) => [...prev, message.data]);
            mergeProgressPayload(message.data);
            break;

          case 'progress':
            mergeProgressPayload(message.data);
            // Certains backends peuvent aussi pousser un status/progress ici
            if (message.data.status) setStatus(message.data.status);
            break;
          
          case 'complete':
            setCompleted(true);
            if (message.data.status === 'failed') {
              setError(message.data.error);
            }
            break;
        }
      },
      (err) => {
        setError('Erreur de connexion au serveur');
        console.error(err);
      }
    );

    // Cleanup
    return () => {
      eventSource.close();
    };
  }, [jobId]);

  const handleDownload = async () => {
    try {
      await reportsAPI.downloadReport(jobId);
    } catch (err) {
      setError('Erreur lors du téléchargement');
    }
  };

  const statusLabels = {
    'PENDING': 'En attente',
    'EXTRACTING': 'Extraction du document',
    'GENERATING': 'Génération du contenu',
    'RENDERING': 'Création du document',
    'COMPLETED': 'Terminé',
    'FAILED': 'Échec',
  };

  const renderFieldProgressTable = () => {
    if (!fieldProgress || !Object.keys(fieldProgress).length) {
      return (
        <div className="field-progress-empty">
          Lance la génération pour suivre les champs ici.
        </div>
      );
    }

    const order = (fieldOrder && fieldOrder.length) ? fieldOrder : Object.keys(fieldProgress);
    const now = new Date();
    const STUCK_THRESHOLD_SECONDS = 90;

    return (
      <div className="field-progress">
        <h3>Progression des champs LLM</h3>
        <div className="field-progress-table-wrap">
          <table className="field-progress-table">
            <thead>
              <tr>
                <th>Champ</th>
                <th>Statut</th>
                <th>Activité</th>
                <th>Détails</th>
              </tr>
            </thead>
            <tbody>
              {order.map((key) => {
                const info = fieldProgress[key];
                if (!info) return null;
                const stage = info.stage || 'pending';
                const icon = FIELD_STAGE_ICONS[stage] || '•';
                const stageLabel = FIELD_STAGE_LABELS[stage] || stage;
                const updatedAt = info.updated_at ? new Date(info.updated_at) : null;
                let activity = '—';
                let warn = false;
                if (updatedAt && !Number.isNaN(updatedAt.getTime())) {
                  const ageSeconds = (now.getTime() - updatedAt.getTime()) / 1000;
                  activity = humanizeDelta(ageSeconds);
                  warn = !['done', 'warning', 'error'].includes(stage) && ageSeconds > STUCK_THRESHOLD_SECONDS;
                }
                const msg = info.message || '—';
                return (
                  <tr key={key} className={`field-row field-stage-${stage}`}>
                    <td className="field-key"><code>{key}</code></td>
                    <td className="field-stage">{icon} {stageLabel}</td>
                    <td className="field-activity">{activity}{warn ? ' ⚠️' : ''}</td>
                    <td className="field-message">{msg}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="progress-page">
      <h1>Génération du Rapport</h1>
      <p className="job-id">Job ID: {jobId}</p>

      <div className="status-card">
        <div className={`status-indicator status-${status.toLowerCase()}`}>
          {statusLabels[status] || status}
        </div>

        {!completed && (
          <div className="spinner"></div>
        )}
      </div>

      {error && (
        <div className="error-box">
          <h3>❌ Erreur</h3>
          <pre>{error}</pre>
        </div>
      )}

      <div className="logs-container">
        <h3>Logs</h3>
        <div className="logs">
          {logs.length === 0 ? (
            <p className="no-logs">Aucun log pour le moment...</p>
          ) : (
            logs.map((log, index) => (
              <div key={index} className={`log-entry log-${log.phase?.toLowerCase() || 'info'}`}>
                <span className="log-time">{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString()}</span>
                <span className="log-phase">[{log.phase || 'INFO'}]</span>
                <span className="log-message">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="logs-container">
        {renderFieldProgressTable()}
      </div>

      {completed && status === 'COMPLETED' && (
        <div className="actions">
          <button onClick={handleDownload} className="btn-download">
            📥 Télécharger le Rapport
          </button>
          <button onClick={() => window.location.href = '/'} className="btn-secondary">
            ← Retour à l'accueil
          </button>
        </div>
      )}

      {completed && status === 'FAILED' && (
        <button onClick={() => window.location.href = '/'} className="btn-secondary">
          ← Retour à l'accueil
        </button>
      )}
    </div>
  );
}

export default Progress;
