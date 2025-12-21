import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { adminAPI, ragAudioAPI, reportsAPI } from '../services/api';
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
  const [sourceStats, setSourceStats] = useState(null);
  const [adminBusy, setAdminBusy] = useState(false);
  const [adminMessage, setAdminMessage] = useState(null);
  const [ragBusy, setRagBusy] = useState(false);
  const [ragMessage, setRagMessage] = useState(null);

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

  const extractApiErrorDetail = (err) => {
    const detail = err?.response?.data?.detail;
    if (!detail) return null;
    if (typeof detail === 'string') return detail;
    if (typeof detail === 'object') {
      const msg = detail.message || detail.error || null;
      const hints = Array.isArray(detail.hints) ? detail.hints.filter(Boolean).join('\n') : null;
      return [msg, hints].filter(Boolean).join('\n');
    }
    return String(detail);
  };

  const mergeProgressPayload = (data) => {
    if (!data) return;
    if (data.field_progress) setFieldProgress(data.field_progress);
    if (data.field_order) setFieldOrder(data.field_order);
    if (data.source_stats) setSourceStats(data.source_stats);
  };

  const renderSourceStats = () => {
    if (!sourceStats) return null;

    const total = sourceStats.total_files ?? 0;
    const byExt = sourceStats.by_ext || {};
    const extractedDocs = sourceStats.extracted_docs;
    const audioTxt = sourceStats.audio_ingested?.txt ?? 0;
    const sourceDir = sourceStats.source_dir;

    const keys = ['.pdf', '.docx', '.txt', '.m4a', '.mp3', '.wav'];
    const picked = keys
      .map((k) => ({ key: k, value: byExt[k] || 0 }))
      .filter((kv) => kv.value > 0);

    const sumPicked = picked.reduce((acc, kv) => acc + kv.value, 0);
    const otherCount = Math.max(0, total - sumPicked);

    return (
      <div className="logs-container">
        <h3>Sources détectées</h3>
        <div className="sources-meta">
          <div className="sources-pill"><span>Total</span><strong>{total}</strong></div>
          {typeof extractedDocs === 'number' && (
            <div className="sources-pill"><span>Extraits</span><strong>{extractedDocs}</strong></div>
          )}
          <div className="sources-pill"><span>Audio RAG (.txt)</span><strong>{audioTxt}</strong></div>
        </div>

        <div className="sources-grid">
          {picked.map((kv) => (
            <div key={kv.key} className="sources-pill">
              <span>{kv.key}</span>
              <strong>{kv.value}</strong>
            </div>
          ))}
          {otherCount > 0 && (
            <div className="sources-pill">
              <span>autres</span>
              <strong>{otherCount}</strong>
            </div>
          )}
        </div>

        {sourceDir && (
          <div className="sources-dir">
            <span>Dossier :</span> <code>{sourceDir}</code>
          </div>
        )}
      </div>
    );
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
    } catch {
      setError('Erreur lors du téléchargement');
    }
  };

  const handleRestartWorkers = async () => {
    if (!jobId) return;
    const ok = window.confirm(
      `Redémarrer les workers va interrompre les jobs en cours (ils peuvent passer en FAILED).\n\nContinuer ?`
    );
    if (!ok) return;

    setAdminBusy(true);
    setAdminMessage(null);
    setError(null);

    try {
      const resp = await adminAPI.restartWorkers({ count: 1, kill: true });
      setAdminMessage(`✅ Workers relancés (PID: ${resp?.pids?.join(', ') || 'n/a'}). Logs: ${resp?.logs?.[0] || '/tmp/worker.log'}`);
    } catch (err) {
      setError(extractApiErrorDetail(err) || 'Erreur lors du redémarrage des workers');
    } finally {
      setAdminBusy(false);
    }
  };

  const handleCancelJob = async () => {
    if (!jobId) return;
    const ok = window.confirm('Annuler ce job ? (Suppression de la queue / résultat perdu)');
    if (!ok) return;

    setAdminBusy(true);
    setAdminMessage(null);
    setError(null);
    try {
      await reportsAPI.deleteReport(jobId, { force: true });
      setAdminMessage('🗑️ Job supprimé. Retour à l\'accueil…');
      setTimeout(() => {
        window.location.href = '/';
      }, 700);
    } catch (err) {
      const statusCode = err?.response?.status;
      setError(extractApiErrorDetail(err) || (statusCode ? `Erreur HTTP ${statusCode} lors de l'annulation` : 'Erreur lors de l\'annulation'));
    } finally {
      setAdminBusy(false);
    }
  };

  const guessSourceIdFromSourceDir = () => {
    const dir = sourceStats?.source_dir;
    if (!dir) return null;
    const parts = String(dir).split('/').filter(Boolean);
    if (!parts.length) return null;
    const last = parts[parts.length - 1];
    if (last === 'sources' && parts.length >= 2) return parts[parts.length - 2];
    return last;
  };

  const handleIngestLocalAudio = async () => {
    const sourceId = guessSourceIdFromSourceDir();
    if (!sourceId) {
      setError("Impossible de déduire le client (source_id) depuis les sources.");
      return;
    }

    const ok = window.confirm(
      `Lancer la transcription (Whisper local) des audios du client “${sourceId}” ?\n\nCela peut prendre plusieurs minutes (CPU).`
    );
    if (!ok) return;

    setRagBusy(true);
    setRagMessage(null);
    setError(null);
    try {
      const resp = await ragAudioAPI.ingestLocal({ sourceId, maxFiles: 50, skipAlreadyIngested: true });
      const queued = resp?.queued ?? 0;
      setRagMessage(`🎙️ Ingestion en file: ${queued} audio(s). (Queue: rag) — Relance ensuite le rapport avec “force re-extract” pour les inclure.`);

      // Rafraîchir le compteur d'audio ingérés
      const st = await ragAudioAPI.status({ sourceId });
      const txt = st?.audio_ingested?.txt ?? 0;
      const js = st?.audio_ingested?.json ?? 0;
      setRagMessage((prev) => `${prev}\nStatut ingested_audio: ${txt} .txt / ${js} .json`);
    } catch (err) {
      setError(extractApiErrorDetail(err) || 'Erreur lors de l\'ingestion audio');
    } finally {
      setRagBusy(false);
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

      {renderSourceStats()}

      {!completed && (status === 'PENDING' || status === 'EXTRACTING') && (
        <div className="logs-container troubleshooting">
          <h3>Dépannage</h3>
          <p className="troubleshooting-hint">
            Si ça reste bloqué (pending / pas de logs), c'est souvent un worker occupé ou arrêté.
            Tu peux choisir de le relancer.
          </p>

          {adminMessage && (
            <div className="admin-message">{adminMessage}</div>
          )}

          {ragMessage && (
            <div className="admin-message">{ragMessage}</div>
          )}

          <div className="troubleshooting-actions">
            <button
              className="btn-danger"
              onClick={handleRestartWorkers}
              disabled={adminBusy}
              title="Coupe puis relance les workers"
            >
              {adminBusy ? '…' : '🛑 Redémarrer les workers'}
            </button>

            {(() => {
              const byExt = sourceStats?.by_ext || {};
              const audioCount = (byExt['.m4a'] || 0) + (byExt['.mp3'] || 0) + (byExt['.wav'] || 0);
              const ingestedTxt = sourceStats?.audio_ingested?.txt || 0;
              if (!audioCount || ingestedTxt > 0) return null;
              return (
                <button
                  className="btn-primary"
                  onClick={handleIngestLocalAudio}
                  disabled={ragBusy}
                  title="Transcrit (Whisper local) puis ajoute les .txt dans sources/ingested_audio"
                >
                  {ragBusy ? '…' : '🎙️ Ingest audios (RAG)'}
                </button>
              );
            })()}

            <button
              className="btn-secondary"
              onClick={handleCancelJob}
              disabled={adminBusy}
              title="Supprime ce job (force)"
            >
              🗑️ Annuler ce job
            </button>
          </div>
        </div>
      )}

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
