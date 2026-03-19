import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { reviewAPI } from '../services/api';
import './ReportReview.css';

const STATUS_COLORS = {
  BON: '#22c55e',
  A_REVOIR: '#f59e0b',
  VIDE: '#ef4444',
};

const STATUS_LABELS = {
  BON: 'Bon',
  A_REVOIR: 'A revoir',
  VIDE: 'Vide',
};

function ReportReview() {
  const { jobId } = useParams();
  const navigate = useNavigate();

  const [reviewData, setReviewData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected section
  const [selectedKey, setSelectedKey] = useState(null);
  const [editText, setEditText] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  // Regeneration
  const [regenerating, setRegenerating] = useState(false);
  const [hintText, setHintText] = useState('');
  const [showHint, setShowHint] = useState(false);

  // Export
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadReview();
  }, [jobId]);

  const loadReview = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reviewAPI.getReview(jobId);
      setReviewData(data);
      if (data.sections?.length > 0 && !selectedKey) {
        setSelectedKey(data.sections[0].key);
        setEditText(data.sections[0].text || '');
      }
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || 'Impossible de charger la revue du rapport');
    } finally {
      setLoading(false);
    }
  };

  const selectedSection = reviewData?.sections?.find(s => s.key === selectedKey);

  const handleSelectSection = (key) => {
    if (isDirty) {
      if (!window.confirm('Modifications non sauvegardees. Changer de section ?')) return;
    }
    setSelectedKey(key);
    const section = reviewData?.sections?.find(s => s.key === key);
    setEditText(section?.text || '');
    setIsDirty(false);
    setShowHint(false);
    setHintText('');
  };

  const handleTextChange = (e) => {
    setEditText(e.target.value);
    setIsDirty(true);
  };

  const handleSave = async () => {
    if (!selectedKey) return;
    setSaving(true);
    try {
      const result = await reviewAPI.updateSection(jobId, selectedKey, editText);
      // Update local state
      setReviewData(prev => ({
        ...prev,
        sections: prev.sections.map(s =>
          s.key === selectedKey
            ? { ...s, text: result.text, evaluation: result.evaluation }
            : s
        ),
      }));
      setIsDirty(false);
    } catch (err) {
      alert(err?.response?.data?.detail || 'Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  const handleRegenerate = async () => {
    if (!selectedKey) return;
    setRegenerating(true);
    try {
      const result = await reviewAPI.regenerateSection(jobId, selectedKey, hintText || null);
      setEditText(result.text);
      setReviewData(prev => ({
        ...prev,
        sections: prev.sections.map(s =>
          s.key === selectedKey
            ? { ...s, text: result.text, evaluation: result.evaluation }
            : s
        ),
      }));
      setIsDirty(false);
      setShowHint(false);
      setHintText('');
    } catch (err) {
      alert(err?.response?.data?.detail || 'Erreur lors de la regeneration');
    } finally {
      setRegenerating(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await reviewAPI.exportReport(jobId);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `rapport_${jobId}.docx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err?.response?.data?.detail || 'Erreur lors de l\'export');
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="review-loading">
        <div className="spinner" />
        <p>Chargement de la revue...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="review-error">
        <h2>Erreur</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/')}>Retour</button>
      </div>
    );
  }

  if (!reviewData) return null;

  const { sections, summary } = reviewData;

  return (
    <div className="review-container">
      {/* Header */}
      <div className="review-header">
        <h2>Revue du rapport</h2>
        <div className="review-summary">
          <span className="summary-badge bon">{summary.bon} Bon</span>
          <span className="summary-badge a-revoir">{summary.a_revoir} A revoir</span>
          <span className="summary-badge vide">{summary.vide} Vide</span>
          <span className="summary-total">{summary.total} sections</span>
        </div>
        <button
          className="btn-export"
          onClick={handleExport}
          disabled={exporting}
        >
          {exporting ? 'Export...' : 'Exporter DOCX'}
        </button>
      </div>

      <div className="review-columns">
        {/* Left: Section list */}
        <div className="review-sidebar">
          <h3>Sections</h3>
          <ul className="section-list">
            {sections.map((s) => (
              <li
                key={s.key}
                className={`section-item ${s.key === selectedKey ? 'active' : ''}`}
                onClick={() => handleSelectSection(s.key)}
              >
                <span
                  className="status-dot"
                  style={{ backgroundColor: STATUS_COLORS[s.evaluation.status] }}
                  title={STATUS_LABELS[s.evaluation.status]}
                />
                <span className="section-label">{s.key.replace(/_/g, ' ')}</span>
                {s.immutable && <span className="immutable-badge" title="Immutable">lock</span>}
              </li>
            ))}
          </ul>
        </div>

        {/* Main: Editor + Evaluation below */}
        <div className="review-main">
          {selectedSection ? (
            <>
              {/* Editor */}
              <div className="review-editor">
                <div className="editor-header">
                  <h3>{selectedKey.replace(/_/g, ' ')}</h3>
                  <span
                    className="status-badge"
                    style={{ backgroundColor: STATUS_COLORS[selectedSection.evaluation.status] }}
                  >
                    {STATUS_LABELS[selectedSection.evaluation.status]}
                    {selectedSection.evaluation.score > 0 && ` (${Math.round(selectedSection.evaluation.score * 100)}%)`}
                  </span>
                </div>

                <textarea
                  className="section-textarea"
                  value={editText}
                  onChange={handleTextChange}
                  rows={15}
                  placeholder="Contenu de la section..."
                />

                <div className="editor-actions">
                  <button
                    className="btn-save"
                    onClick={handleSave}
                    disabled={!isDirty || saving}
                  >
                    {saving ? 'Sauvegarde...' : 'Sauvegarder'}
                  </button>

                  <button
                    className="btn-hint"
                    onClick={() => setShowHint(!showHint)}
                  >
                    Relancer
                  </button>
                </div>

                {showHint && (
                  <div className="hint-box">
                    <input
                      type="text"
                      value={hintText}
                      onChange={(e) => setHintText(e.target.value)}
                      placeholder="Indication pour le LLM (optionnel)..."
                      className="hint-input"
                    />
                    <button
                      className="btn-regenerate"
                      onClick={handleRegenerate}
                      disabled={regenerating}
                    >
                      {regenerating ? 'Regeneration...' : 'Regenerer'}
                    </button>
                  </div>
                )}
              </div>

              {/* Evaluation panel — below editor */}
              <div className="review-eval">
                <div className="eval-grid">
                  {/* Score + Criteres */}
                  <div className="eval-col">
                    <h3>Evaluation</h3>
                    <div className="eval-score">
                      Score: {Math.round(selectedSection.evaluation.score * 100)}%
                    </div>
                    {selectedSection.evaluation.comment && (
                      <div className="eval-comment">
                        {selectedSection.evaluation.comment}
                      </div>
                    )}
                    <h4>Criteres</h4>
                    <ul className="checks-list">
                      {selectedSection.evaluation.checks.map((check) => (
                        <li key={check.element} className={`check-item ${check.found ? 'found' : 'missing'}`}>
                          <span className="check-icon">{check.found ? '\u2713' : '\u2717'}</span>
                          <span className="check-label">{check.element.replace(/_/g, ' ')}</span>
                          {check.found && check.keywords_matched.length > 0 && (
                            <span className="check-keywords">
                              ({check.keywords_matched.slice(0, 3).join(', ')})
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                    <h4>Sources attendues</h4>
                    <div className="sources-list">
                      {selectedSection.sources.map((src) => (
                        <span key={src} className="source-tag">{src}</span>
                      ))}
                    </div>
                  </div>

                  {/* Generation metadata */}
                  {selectedSection.generation_meta && Object.keys(selectedSection.generation_meta).length > 0 && (
                    <div className="eval-col">
                      <h3>Generation</h3>
                      <div className="gen-meta">
                        <div className="gen-meta-row">
                          <span className="gen-meta-label">Fichiers</span>
                          <span className="gen-meta-value">{selectedSection.generation_meta.source_count || 0}</span>
                        </div>
                        <div className="gen-meta-row">
                          <span className="gen-meta-label">Passages</span>
                          <span className="gen-meta-value">{selectedSection.generation_meta.chunk_count || 0}</span>
                        </div>
                        <div className="gen-meta-row">
                          <span className="gen-meta-label">Retries</span>
                          <span className="gen-meta-value">{selectedSection.generation_meta.retries || 0}</span>
                        </div>
                        <div className="gen-meta-row">
                          <span className="gen-meta-label">Prompt</span>
                          <span className="gen-meta-value">{selectedSection.generation_meta.prompt_length || 0} chars</span>
                        </div>
                        {selectedSection.generation_meta.had_prior_sections && (
                          <div className="gen-meta-row">
                            <span className="gen-meta-label">Contexte</span>
                            <span className="gen-meta-value gen-meta-tag">+ sections precedentes</span>
                          </div>
                        )}
                        {selectedSection.generation_meta.source_files?.length > 0 && (
                          <div className="gen-meta-files">
                            <span className="gen-meta-label">Documents utilises</span>
                            <ul className="gen-file-list">
                              {selectedSection.generation_meta.source_files.map((f) => (
                                <li key={f} className="gen-file-item">{f}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {selectedSection.generation_meta.instructions && (
                          <div className="gen-meta-files">
                            <span className="gen-meta-label">Consigne LLM</span>
                            <div className="gen-instructions">{selectedSection.generation_meta.instructions}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <p className="no-selection">Selectionnez une section</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default ReportReview;
