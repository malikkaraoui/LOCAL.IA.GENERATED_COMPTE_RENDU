import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { adminAPI, ragAudioAPI, reportsAPI } from '../services/api';
import './Progress.css';

/**
 * Page de suivi — Swiss International Style.
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
  const [jobMeta, setJobMeta] = useState(null);

  const STAGE_LABEL = {
    pending: 'En attente',
    start: 'Preparation',
    context: 'Contexte',
    prompt: 'Envoi',
    response: 'Reception',
    retry: 'Correction',
    done: 'Termine',
    warning: 'Vide',
    error: 'Erreur',
  };

  const STATUS_LABEL = {
    PENDING: 'En attente',
    EXTRACTING: 'Lecture des documents',
    GENERATING: 'Redaction en cours',
    RENDERING: 'Mise en page',
    COMPLETED: 'Termine',
    FAILED: 'Echec',
  };

  const humanizeDelta = (seconds) => {
    if (seconds < 1) return '<1s';
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m${String(s).padStart(2, '0')}s`;
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
    if (data.job_meta) setJobMeta(data.job_meta);
  };

  // ── SSE ──
  useEffect(() => {
    if (!jobId) return;
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
            if (message.data.status) setStatus(message.data.status);
            break;
          case 'complete':
            setCompleted(true);
            if (message.data.status === 'failed') setError(message.data.error);
            break;
        }
      },
      (err) => {
        setError('Connexion au serveur perdue');
        console.error(err);
      }
    );
    return () => eventSource.close();
  }, [jobId]);

  // ── Actions ──
  const handleDownload = async () => {
    try { await reportsAPI.downloadReport(jobId); }
    catch { setError('Erreur lors du telechargement'); }
  };

  const handleRestartWorkers = async () => {
    if (!window.confirm('Redemarrer le processus de generation ?\nLes taches en cours seront interrompues.')) return;
    setAdminBusy(true); setAdminMessage(null); setError(null);
    try {
      const resp = await adminAPI.restartWorkers({ count: 1, kill: true });
      setAdminMessage(`Processus relance (PID: ${resp?.pids?.join(', ') || '-'})`);
    } catch (err) {
      setError(extractApiErrorDetail(err) || 'Erreur lors du redemarrage');
    } finally { setAdminBusy(false); }
  };

  const handleCancelJob = async () => {
    if (!window.confirm('Annuler cette generation ?')) return;
    setAdminBusy(true); setAdminMessage(null); setError(null);
    try {
      await reportsAPI.cancelReport(jobId);
      setAdminMessage('Annulation demandee...');
      setTimeout(() => { window.location.href = '/'; }, 700);
    } catch (err) {
      setError(extractApiErrorDetail(err) || "Erreur lors de l'annulation");
    } finally { setAdminBusy(false); }
  };

  const guessSourceId = () => {
    const dir = sourceStats?.source_dir;
    if (!dir) return null;
    const parts = String(dir).split('/').filter(Boolean);
    if (!parts.length) return null;
    const last = parts[parts.length - 1];
    return last === 'sources' && parts.length >= 2 ? parts[parts.length - 2] : last;
  };

  const handleIngestAudio = async () => {
    const sourceId = guessSourceId();
    if (!sourceId) { setError('Impossible de determiner le client pour la transcription.'); return; }
    if (!window.confirm(`Transcrire les fichiers audio du client "${sourceId}" ?`)) return;
    setRagBusy(true); setRagMessage(null); setError(null);
    try {
      const resp = await ragAudioAPI.ingestLocal({ sourceId, maxFiles: 50, skipAlreadyIngested: true });
      setRagMessage(`${resp?.queued ?? 0} fichier(s) audio en cours de transcription.`);
    } catch (err) {
      setError(extractApiErrorDetail(err) || 'Erreur lors de la transcription');
    } finally { setRagBusy(false); }
  };

  // ── Render: Sources ──
  const renderSources = () => {
    if (!sourceStats) return null;
    const total = sourceStats.total_files ?? 0;
    const byExt = sourceStats.by_ext || {};
    const extracted = sourceStats.extracted_docs;
    const audioTxt = sourceStats.audio_ingested?.txt ?? 0;
    const dir = sourceStats.source_dir;

    const types = ['.pdf', '.docx', '.txt', '.msg', '.m4a', '.mp3', '.wav'];
    const cells = types.map((k) => ({ key: k.replace('.', ''), value: byExt[k] || 0 })).filter((c) => c.value > 0);
    const sumCells = cells.reduce((a, c) => a + c.value, 0);
    const other = Math.max(0, total - sumCells);

    return (
      <div className="card">
        <div className="card-header">Documents source</div>
        <div className="card-body">
          <div className="sources-grid">
            <div className="stat-cell">
              <span className="stat-value">{total}</span>
              <span className="stat-label">Total</span>
            </div>
            {typeof extracted === 'number' && (
              <div className="stat-cell">
                <span className="stat-value">{extracted}</span>
                <span className="stat-label">Lus</span>
              </div>
            )}
            <div className="stat-cell">
              <span className="stat-value">{audioTxt}</span>
              <span className="stat-label">Audio</span>
            </div>
            {cells.map((c) => (
              <div className="stat-cell" key={c.key}>
                <span className="stat-value">{c.value}</span>
                <span className="stat-label">{c.key}</span>
              </div>
            ))}
            {other > 0 && (
              <div className="stat-cell">
                <span className="stat-value">{other}</span>
                <span className="stat-label">Autres</span>
              </div>
            )}
          </div>
          {dir && <div className="sources-path">{dir}</div>}
        </div>
      </div>
    );
  };

  // ── Render: Field progress ──
  const renderFields = () => {
    if (!fieldProgress || !Object.keys(fieldProgress).length) return null;

    const order = fieldOrder?.length ? fieldOrder : Object.keys(fieldProgress);
    const now = new Date();
    const STUCK = 120;
    const total = order.length;
    const done = order.filter((k) => ['done', 'warning', 'error'].includes(fieldProgress[k]?.stage)).length;
    const active = order.find((k) => {
      const s = fieldProgress[k]?.stage;
      return s && !['pending', 'done', 'warning', 'error'].includes(s);
    });

    return (
      <div className="card progress-grid-full">
        <div className="card-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>Progression</span>
          <span style={{ fontWeight: 400, fontSize: 12, letterSpacing: 0 }}>
            <strong>{done}</strong> / {total}
            {active && <span className="field-active-label">&#x2192; {active}</span>}
          </span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="fields-table">
            <thead>
              <tr>
                <th>Section</th>
                <th>Etat</th>
                <th>Duree</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {order.map((key) => {
                const info = fieldProgress[key];
                if (!info) return null;
                const stage = info.stage || 'pending';
                const label = STAGE_LABEL[stage] || stage;

                let elapsed = '';
                let stuck = false;
                const startedAt = info.started_at ? new Date(info.started_at) : null;
                if (startedAt && !Number.isNaN(startedAt.getTime())) {
                  if (['done', 'warning', 'error'].includes(stage) && info.elapsed_seconds != null) {
                    elapsed = humanizeDelta(info.elapsed_seconds);
                  } else if (!['done', 'warning', 'error', 'pending'].includes(stage)) {
                    const sec = (now.getTime() - startedAt.getTime()) / 1000;
                    elapsed = humanizeDelta(sec);
                    stuck = sec > STUCK;
                  } else if (info.elapsed_seconds != null) {
                    elapsed = humanizeDelta(info.elapsed_seconds);
                  }
                }

                const isActive = !['pending', 'done', 'warning', 'error'].includes(stage);
                const rowClass = [
                  isActive ? 'row-active' : '',
                  stage === 'error' ? 'row-error' : '',
                  stage === 'warning' ? 'row-warning' : '',
                  stuck ? 'row-stuck' : '',
                ].filter(Boolean).join(' ');

                return (
                  <tr key={key} className={rowClass}>
                    <td><span className="field-name">{key}</span></td>
                    <td>
                      <span className="field-status">
                        <span className={`field-dot field-dot-${stage}`} />
                        {label}
                      </span>
                    </td>
                    <td><span className="field-time">{elapsed || '\u2014'}</span></td>
                    <td><span className="field-detail">{info.message || '\u2014'}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // ── Render: Troubleshooting ──
  const renderTroubleshooting = () => {
    if (completed || (status !== 'PENDING' && status !== 'EXTRACTING')) return null;
    const byExt = sourceStats?.by_ext || {};
    const audioCount = (byExt['.m4a'] || 0) + (byExt['.mp3'] || 0) + (byExt['.wav'] || 0);
    const ingestedTxt = sourceStats?.audio_ingested?.txt || 0;

    return (
      <div className="card progress-grid-full">
        <div className="card-header">Depannage</div>
        <div className="card-body">
          <p className="troubleshooting-hint">
            Si la generation reste bloquee, le processus est peut-etre occupe ou arrete.
          </p>
          {adminMessage && <div className="admin-message">{adminMessage}</div>}
          {ragMessage && <div className="admin-message">{ragMessage}</div>}
          <div className="troubleshooting-actions">
            <button className="btn-action btn-action-danger" onClick={handleRestartWorkers} disabled={adminBusy}>
              {adminBusy ? '...' : 'Relancer le processus'}
            </button>
            {audioCount > 0 && !ingestedTxt && (
              <button className="btn-action btn-action-primary" onClick={handleIngestAudio} disabled={ragBusy}>
                {ragBusy ? '...' : 'Transcrire les audios'}
              </button>
            )}
            <button className="btn-action btn-action-secondary" onClick={handleCancelJob} disabled={adminBusy}>
              Annuler
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="progress-page">
      {/* Header */}
      <div className="progress-header">
        <h1>Generation</h1>
        <span className={`status-indicator status-${status.toLowerCase()}`}>
          {STATUS_LABEL[status] || status}
        </span>
        {!completed && <span className="spinner" />}
        <span className="job-id">{jobId}</span>
      </div>

      {/* Job meta */}
      {jobMeta && (
        <div className="job-meta-bar">
          <span className="meta-item"><span className="meta-check">{jobMeta.surname ? '\u2713' : '\u2014'}</span> {jobMeta.civility} {jobMeta.name} {jobMeta.surname}</span>
          <span className="meta-item"><span className="meta-check">{jobMeta.avs_number ? '\u2713' : '\u2014'}</span> AVS {jobMeta.avs_number || 'non renseigne'}</span>
          <span className="meta-item"><span className="meta-check">\u2713</span> {jobMeta.llm_model}</span>
          {jobMeta.report_type && <span className="meta-item">{jobMeta.report_type}</span>}
        </div>
      )}

      {error && (
        <div className="error-box">
          <strong>Erreur</strong>
          <pre>{error}</pre>
        </div>
      )}

      <div className="progress-grid">
        {/* Sources */}
        {renderSources()}

        {/* Terminal logs */}
        <div className="card">
          <div className="card-header">Journal</div>
          <div className="terminal">
            {logs.length === 0 ? (
              <div className="terminal-empty">En attente de donnees...</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="log-line">
                  <span className="log-time">
                    {log.timestamp ? new Date(log.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--:--'}
                  </span>
                  <span className={`log-tag log-tag-${(log.phase || 'info').toLowerCase()}`}>
                    {log.phase || 'INFO'}
                  </span>
                  <span className="log-msg">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Troubleshooting */}
        {renderTroubleshooting()}

        {/* Field progress */}
        {renderFields()}
      </div>

      {/* Actions finales */}
      {completed && status === 'COMPLETED' && (
        <div className="progress-actions">
          <button className="btn-action btn-action-primary" onClick={() => window.location.href = `/review/${jobId}`}>
            Revue du rapport
          </button>
          <button className="btn-action btn-action-primary" onClick={handleDownload}>
            Telecharger
          </button>
          <button className="btn-action btn-action-secondary" onClick={() => window.location.href = '/'}>
            Retour
          </button>
        </div>
      )}

      {completed && status === 'FAILED' && (
        <div className="progress-actions">
          <button className="btn-action btn-action-secondary" onClick={() => window.location.href = '/'}>
            Retour
          </button>
        </div>
      )}
    </div>
  );
}

export default Progress;
