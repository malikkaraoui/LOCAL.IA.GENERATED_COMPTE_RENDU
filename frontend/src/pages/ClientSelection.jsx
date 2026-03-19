import { useState, useEffect } from 'react';
import { reportsAPI, healthAPI, brandingAPI } from '../services/api';
import './ClientSelection.css';

/**
 * Page de configuration et génération de rapport.
 * Design: Swiss International Style — Unica77, pleine largeur, pas de violet.
 */
function ClientSelection() {
  // États principaux
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Identité
  const [name, setName] = useState('');
  const [surname, setSurname] = useState('');
  const [civility, setCivility] = useState('Monsieur');
  const [avsNumber, setAvsNumber] = useState('');

  // Localisation et date
  const [locationCity, setLocationCity] = useState('Genève');
  const [autoDate, setAutoDate] = useState(true);
  const [manualDate, setManualDate] = useState('');

  // Chemins
  const [clientsRoot, setClientsRoot] = useState('./CLIENTS');
  const [outputDir, setOutputDir] = useState('./out');

  // Template — upload uniquement, pas de mémoire serveur
  const [templateLocalFile, setTemplateLocalFile] = useState(null);
  const [templateUploading, setTemplateUploading] = useState(false);
  const [templateServerName, setTemplateServerName] = useState('');

  // LLM
  const [llmHost, setLlmHost] = useState('http://localhost:11434');
  const [llmModel, setLlmModel] = useState('llama3.1:8b');
  const [llmCustom, setLlmCustom] = useState('');
  const [useCustomModel, setUseCustomModel] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [llmRestarting, setLlmRestarting] = useState(false);
  const [llmRestartMessage, setLlmRestartMessage] = useState(null);
  const [llmModelsError, setLlmModelsError] = useState(null);

  // Type de rapport (V3)
  const [reportTypes, setReportTypes] = useState([]);
  const [selectedReportType, setSelectedReportType] = useState('rapport_initial');

  // Options avancées
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [topK, setTopK] = useState(10);
  const [temperature, setTemperature] = useState(0.2);
  const [topP, setTopP] = useState(0.9);
  const [includeFilters, setIncludeFilters] = useState('');
  const [excludeFilters, setExcludeFilters] = useState('');
  const [forceReextract, setForceReextract] = useState(false);
  const [enableSoffice, setEnableSoffice] = useState(false);
  const [autoPdf, setAutoPdf] = useState(false);

  // Branding
  const [brandingEnabled, setBrandingEnabled] = useState(false);
  const [brandingTitreDocument, setBrandingTitreDocument] = useState('');
  const [brandingSociete, setBrandingSociete] = useState('');
  const [brandingRue, setBrandingRue] = useState('');
  const [brandingNumero, setBrandingNumero] = useState('');
  const [brandingCp, setBrandingCp] = useState('');
  const [brandingVille, setBrandingVille] = useState('');
  const [brandingTel, setBrandingTel] = useState('');
  const [brandingEmail, setBrandingEmail] = useState('');
  const [brandingLogoHeader, setBrandingLogoHeader] = useState(null);
  const [brandingLogoFooter, setBrandingLogoFooter] = useState(null);

  // ── Chargement initial ──
  const loadOllamaModels = async () => {
    setModelsLoading(true);
    setLlmModelsError(null);
    try {
      const response = await healthAPI.getOllamaModels(llmHost);
      setAvailableModels(response.models || []);
      if (response.models?.length > 0 && !llmModel) {
        setLlmModel(response.models[0].name);
      }
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message;
      setLlmModelsError(detail || 'Impossible de charger les modèles');
      setAvailableModels([
        { name: 'qwen3-next:latest', available: false },
        { name: 'mistral:latest', available: false },
        { name: 'llama3.1:8b', available: false },
      ]);
    } finally {
      setModelsLoading(false);
    }
  };

  const restartAllLlm = async () => {
    setLlmRestarting(true);
    setLlmRestartMessage(null);
    try {
      const resp = await healthAPI.restartOllama(llmHost);
      const unloaded = Array.isArray(resp?.unloaded) ? resp.unloaded.length : 0;
      const running = Array.isArray(resp?.running_models) ? resp.running_models.length : 0;
      const errs = Array.isArray(resp?.errors) ? resp.errors.length : 0;
      const msg = running === 0
        ? 'Aucun modele actif (serveur OK)'
        : `${unloaded}/${running} modele(s) decharge(s)${errs ? ` (${errs} erreur(s))` : ''}`;
      setLlmRestartMessage({ type: errs ? 'warning' : 'success', text: msg });
      await loadOllamaModels();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setLlmRestartMessage({ type: 'error', text: detail || 'Impossible de redemarrer le serveur IA' });
    } finally {
      setLlmRestarting(false);
    }
  };

  useEffect(() => {
    loadOllamaModels();
    (async () => {
      try {
        const resp = await reportsAPI.listClients();
        setClients(resp.clients || []);
      } catch {
        setClients(['KARAOUI Malik']);
      }
    })();
    (async () => {
      try {
        const resp = await reportsAPI.getReportTypes();
        setReportTypes(resp.types || []);
      } catch {}
    })();
  }, []);

  // ── Template upload ──
  const handleTemplateFileSelected = async (file) => {
    if (!file) return;
    setTemplateLocalFile(file);
    if (!file.name?.toLowerCase().endsWith('.docx')) {
      setError('Le modele de document doit etre un fichier .docx');
      return;
    }
    setTemplateUploading(true);
    setError(null);
    try {
      const resp = await reportsAPI.uploadTemplate(file);
      setTemplateServerName(resp.template_name || '');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || "Erreur lors de l'envoi du modele");
    } finally {
      setTemplateUploading(false);
    }
  };

  // ── Branding ──
  const extractDetailFromAxiosBlobError = async (err) => {
    const data = err?.response?.data;
    const ct = err?.response?.headers?.['content-type'] || err?.response?.headers?.['Content-Type'];
    if (data instanceof Blob) {
      try {
        const text = await data.text();
        if ((ct && String(ct).includes('application/json')) || text.trim().startsWith('{')) {
          const parsed = JSON.parse(text);
          return parsed?.detail || text;
        }
        return text;
      } catch { return null; }
    }
    return err?.response?.data?.detail || null;
  };

  const applyBrandingAndUpload = async () => {
    if (!brandingEnabled) return templateServerName || null;

    const fd = new FormData();
    if (templateServerName) fd.append('template_name', templateServerName);
    fd.append('titre_document', brandingTitreDocument);
    fd.append('societe', brandingSociete);
    fd.append('rue', brandingRue);
    fd.append('numero', brandingNumero);
    fd.append('cp', brandingCp);
    fd.append('ville', brandingVille);
    fd.append('tel', brandingTel);
    fd.append('email', brandingEmail);
    if (brandingLogoHeader) fd.append('logo_header', brandingLogoHeader);
    if (brandingLogoFooter) fd.append('logo_footer', brandingLogoFooter);

    const { blob, filename } = await brandingAPI.applyBranding(fd);
    const docxName = filename || `template_brande_${Date.now()}.docx`;
    const file = new File([blob], docxName, {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    const uploadResp = await reportsAPI.uploadTemplate(file);
    const name = uploadResp.template_name;
    if (name) setTemplateServerName(name);
    return name || null;
  };

  // ── Localisation preview ──
  const getLocationDatePreview = () => {
    if (autoDate) {
      const today = new Date();
      return `${locationCity}, le ${today.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })}`;
    }
    return manualDate ? `${locationCity}, le ${manualDate}` : locationCity;
  };

  // ── Génération ──
  const templateReady = Boolean(templateServerName || templateLocalFile);

  const handleCreateReport = async () => {
    if (!selectedClient) {
      setError('Selectionnez un dossier client');
      return;
    }
    if (!templateReady) {
      setError('Selectionnez un modele de document (.docx)');
      return;
    }
    setLoading(true);
    setError(null);

    try {
      let effectiveTemplate = templateServerName || null;
      if (brandingEnabled) {
        try {
          effectiveTemplate = await applyBrandingAndUpload();
        } catch (err) {
          const detail = await extractDetailFromAxiosBlobError(err);
          setError(detail || "Erreur lors de l'application de la personnalisation");
          setLoading(false);
          return;
        }
      }

      const finalModel = useCustomModel ? llmCustom : llmModel;

      const response = await reportsAPI.createReport(
        selectedClient,
        null,
        'auto',
        {
          name,
          surname,
          civility,
          avs_number: avsNumber,
          titre_document: brandingTitreDocument,
          location_city: locationCity,
          location_date: getLocationDatePreview(),
          auto_location_date: autoDate,
          clients_root: clientsRoot,
          template_name: effectiveTemplate || undefined,
          output_dir: outputDir,
          llm: {
            provider: 'ollama',
            base_url: llmHost,
            model: finalModel,
            temperature,
            max_tokens: 4096,
            top_p: topP,
            timeout: 900.0,
          },
          llm_host: llmHost,
          llm_model: finalModel,
          topk: topK,
          temperature,
          top_p: topP,
          include_filters: includeFilters,
          exclude_filters: excludeFilters,
          force_reextract: forceReextract,
          enable_soffice: enableSoffice,
          export_pdf: autoPdf,
          report_type: selectedReportType || undefined,
        }
      );
      window.location.href = `/progress/${response.job_id}`;
    } catch (err) {
      const detail = err.response?.data?.detail;
      const status = err.response?.status;
      setError(detail || (status ? `Erreur HTTP ${status}` : 'Erreur lors de la creation du rapport'));
    } finally {
      setLoading(false);
    }
  };

  // ── File picker component ──
  const FilePicker = ({ id, accept, disabled, file, onFileSelected, buttonLabel, placeholder }) => (
    <div className="file-picker">
      <input
        id={id}
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={(e) => onFileSelected?.(e.target.files?.[0] || null)}
      />
      <label
        htmlFor={id}
        className={`btn-file${disabled ? ' disabled' : ''}`}
      >
        {buttonLabel}
      </label>
      <div className={`file-name${file ? ' has-file' : ''}`} title={file?.name || ''}>
        {file ? file.name : placeholder}
      </div>
    </div>
  );

  return (
    <div className="client-selection">
      <h1 className="page-title">Nouveau rapport</h1>

      <div className="form-grid">
        {/* ── COLONNE 1: Dossier + Modele doc + Type rapport ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Dossier client */}
          <div className="form-section">
            <h3>Dossier client</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Emplacement des dossiers</label>
                <input
                  type="text"
                  value={clientsRoot}
                  onChange={(e) => setClientsRoot(e.target.value)}
                  placeholder="./CLIENTS"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Client</label>
                <select
                  value={selectedClient}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedClient(val);
                    // Auto-remplir nom/prénom depuis le nom du dossier
                    // Mots MAJUSCULES = nom de famille, reste = prénom (1re lettre en majuscule)
                    if (val) {
                      const parts = val.trim().split(/\s+/);
                      const upper = parts.filter((w) => w === w.toUpperCase() && /[A-Z]/.test(w));
                      const rest = parts.filter((w) => w !== w.toUpperCase() || !/[A-Z]/.test(w));
                      const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
                      setSurname(upper.join(' '));
                      setName(rest.map(capitalize).join(' '));
                    }
                  }}
                  disabled={loading}
                >
                  <option value="">Selectionner un client</option>
                  {clients.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <span className="hint" style={{ marginTop: 6 }}>
                  Formats acceptes : PDF, DOCX, TXT, MSG, M4A, MP3, WAV
                </span>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Dossier de sortie</label>
                <input
                  type="text"
                  value={outputDir}
                  onChange={(e) => setOutputDir(e.target.value)}
                  placeholder="./out"
                />
              </div>
            </div>
          </div>

          {/* Modele de document */}
          <div className="form-section">
            <h3>Modele de document</h3>
            <div className="form-row">
              <div className="form-group">
                <FilePicker
                  id="template-docx"
                  accept=".docx"
                  disabled={loading || templateUploading}
                  file={templateLocalFile}
                  onFileSelected={handleTemplateFileSelected}
                  buttonLabel={templateUploading ? 'Envoi...' : 'Parcourir'}
                  placeholder="Aucun modele selectionne"
                />
                {templateServerName && (
                  <span className="hint" style={{ marginTop: 6 }}>
                    Pret : {templateServerName}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Type de rapport */}
          {reportTypes.length > 0 && (
            <div className="form-section">
              <h3>Type de rapport</h3>
              <div className="form-row">
                <div className="form-group">
                  <select
                    value={selectedReportType}
                    onChange={(e) => setSelectedReportType(e.target.value)}
                    disabled={loading}
                  >
                    {reportTypes.map((rt) => (
                      <option
                        key={rt.key}
                        value={rt.key}
                        disabled={rt.sections.length === 0}
                      >
                        {rt.label} {rt.sections.length === 0 ? '(bientot)' : `(${rt.sections.length} sections)`}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── COLONNE 2: Identite + Lieu et date ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div className="form-section">
            <h3>Identite du beneficiaire</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Prenom</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Prenom" />
              </div>
              <div className="form-group">
                <label>Nom</label>
                <input type="text" value={surname} onChange={(e) => setSurname(e.target.value)} placeholder="Nom" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Civilite</label>
                <select value={civility} onChange={(e) => setCivility(e.target.value)}>
                  <option value="Monsieur">Monsieur</option>
                  <option value="Madame">Madame</option>
                  <option value="Autre">Autre</option>
                </select>
              </div>
              <div className="form-group">
                <label>Numero AVS</label>
                <input type="text" value={avsNumber} onChange={(e) => setAvsNumber(e.target.value)} placeholder="756.XXXX.XXXX.XX" />
              </div>
            </div>
          </div>

          <div className="form-section">
            <h3>Lieu et date</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Ville</label>
                <input type="text" value={locationCity} onChange={(e) => setLocationCity(e.target.value)} placeholder="Geneve" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group checkbox-group">
                <label>
                  <input type="checkbox" checked={autoDate} onChange={(e) => setAutoDate(e.target.checked)} />
                  <span>Date du jour automatique</span>
                </label>
              </div>
            </div>
            {!autoDate && (
              <div className="form-row">
                <div className="form-group">
                  <label>Date</label>
                  <input type="text" value={manualDate} onChange={(e) => setManualDate(e.target.value)} placeholder="15 decembre 2024" />
                </div>
              </div>
            )}
            <div className="preview-box">
              <strong>Apercu :</strong> {getLocationDatePreview()}
            </div>
          </div>
        </div>

        {/* ── COLONNE 3: IA + Personnalisation ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div className="form-section">
            <h3>Modele d'intelligence artificielle</h3>
            <div className="form-row">
              <div className="form-group">
                <label>Adresse du serveur</label>
                <input
                  type="text"
                  value={llmHost}
                  onChange={(e) => setLlmHost(e.target.value)}
                  placeholder="http://localhost:11434"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <div className="label-with-button">
                  <label>
                    Modele
                    {modelsLoading && <span className="models-loading">(chargement...)</span>}
                  </label>
                  <button type="button" className="btn-icon" onClick={loadOllamaModels} disabled={modelsLoading} title="Actualiser la liste">
                    &#x21bb;
                  </button>
                  <button type="button" className="btn-icon" onClick={restartAllLlm} disabled={llmRestarting} title="Redemarrer le serveur IA">
                    &#x267b;
                  </button>
                </div>
                <select
                  value={useCustomModel ? 'custom' : llmModel}
                  onChange={(e) => {
                    if (e.target.value === 'custom') {
                      setUseCustomModel(true);
                    } else {
                      setUseCustomModel(false);
                      setLlmModel(e.target.value);
                    }
                  }}
                >
                  {availableModels.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.available ? '\u25cf ' : '\u25cb '}{m.name}
                    </option>
                  ))}
                  {availableModels.length === 0 && <option disabled>Aucun modele disponible</option>}
                  <option value="custom">Autre (saisie libre)</option>
                </select>

                {llmModelsError && (
                  <div className="llm-restart-message llm-restart-error">
                    {llmModelsError}
                  </div>
                )}
                {llmRestartMessage && (
                  <div className={`llm-restart-message llm-restart-${llmRestartMessage.type}`}>
                    {llmRestartMessage.text}
                  </div>
                )}
              </div>
            </div>

            {useCustomModel && (
              <div className="form-row">
                <div className="form-group">
                  <label>Nom du modele</label>
                  <input type="text" value={llmCustom} onChange={(e) => setLlmCustom(e.target.value)} placeholder="phi3:mini" />
                </div>
              </div>
            )}
          </div>

          {/* Personnalisation (branding) */}
          <div className="form-section">
            <h3>Personnalisation du document</h3>
            <div className="form-row">
              <div className="form-group checkbox-group">
                <label>
                  <input type="checkbox" checked={brandingEnabled} onChange={(e) => setBrandingEnabled(e.target.checked)} />
                  <span>Appliquer entete et pied de page</span>
                </label>
              </div>
            </div>

            {brandingEnabled && (
              <>
                <div className="form-row">
                  <div className="form-group">
                    <label>Titre du document</label>
                    <input type="text" value={brandingTitreDocument} onChange={(e) => setBrandingTitreDocument(e.target.value)} placeholder="ESSAI" />
                  </div>
                  <div className="form-group">
                    <label>Societe</label>
                    <input type="text" value={brandingSociete} onChange={(e) => setBrandingSociete(e.target.value)} placeholder="MALIK SAS" />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Rue</label>
                    <input type="text" value={brandingRue} onChange={(e) => setBrandingRue(e.target.value)} placeholder="Rue" />
                  </div>
                  <div className="form-group">
                    <label>Numero</label>
                    <input type="text" value={brandingNumero} onChange={(e) => setBrandingNumero(e.target.value)} placeholder="2" />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Code postal</label>
                    <input type="text" value={brandingCp} onChange={(e) => setBrandingCp(e.target.value)} placeholder="1200" />
                  </div>
                  <div className="form-group">
                    <label>Ville</label>
                    <input type="text" value={brandingVille} onChange={(e) => setBrandingVille(e.target.value)} placeholder="Geneve" />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Telephone</label>
                    <input type="text" value={brandingTel} onChange={(e) => setBrandingTel(e.target.value)} placeholder="+41..." />
                  </div>
                  <div className="form-group">
                    <label>Email</label>
                    <input type="text" value={brandingEmail} onChange={(e) => setBrandingEmail(e.target.value)} placeholder="contact@..." />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Logo entete</label>
                    <FilePicker
                      id="branding-logo-header"
                      accept="image/png,image/jpeg,image/tiff"
                      disabled={loading}
                      file={brandingLogoHeader}
                      onFileSelected={(file) => setBrandingLogoHeader(file)}
                      buttonLabel="Parcourir"
                      placeholder="Aucun fichier"
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Logo pied de page</label>
                    <FilePicker
                      id="branding-logo-footer"
                      accept="image/png,image/jpeg,image/tiff"
                      disabled={loading}
                      file={brandingLogoFooter}
                      onFileSelected={(file) => setBrandingLogoFooter(file)}
                      buttonLabel="Parcourir"
                      placeholder="Aucun fichier"
                    />
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Options avancees ── */}
      <div className="advanced-section">
        <button type="button" className="btn-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
          Reglages avances {showAdvanced ? '\u25BC' : '\u25B6'}
        </button>

        {showAdvanced && (
          <div className="advanced-content">
            <div className="form-row">
              <div className="form-group">
                <label>Nombre de passages ({topK})</label>
                <span className="hint">Combien d'extraits du dossier sont envoyes au modele pour chaque section.</span>
                <input type="range" min="3" max="20" value={topK} onChange={(e) => setTopK(parseInt(e.target.value))} />
              </div>
              <div className="form-group">
                <label>Creativite ({temperature})</label>
                <span className="hint">Plus la valeur est basse, plus le texte colle aux documents. Plus elle est haute, plus le texte est libre.</span>
                <input type="range" min="0" max="1" step="0.05" value={temperature} onChange={(e) => setTemperature(parseFloat(e.target.value))} />
              </div>
              <div className="form-group">
                <label>Diversite ({topP})</label>
                <span className="hint">Controle la variete des mots utilises par le modele.</span>
                <input type="range" min="0.1" max="1" step="0.05" value={topP} onChange={(e) => setTopP(parseFloat(e.target.value))} />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Inclure uniquement ces dossiers</label>
                <input type="text" value={includeFilters} onChange={(e) => setIncludeFilters(e.target.value)} placeholder="01 Dossier, 02 Tests" />
                <span className="hint">Separer par des virgules. Laissez vide pour tout inclure.</span>
              </div>
              <div className="form-group">
                <label>Exclure ces dossiers</label>
                <input type="text" value={excludeFilters} onChange={(e) => setExcludeFilters(e.target.value)} placeholder="archive, old" />
                <span className="hint">Separer par des virgules.</span>
              </div>
            </div>

            <div className="form-row checkbox-row">
              <div className="form-group checkbox-group">
                <label>
                  <input type="checkbox" checked={forceReextract} onChange={(e) => setForceReextract(e.target.checked)} />
                  <span>Relire tous les documents (ignorer le cache)</span>
                </label>
              </div>
              <div className="form-group checkbox-group">
                <label>
                  <input type="checkbox" checked={enableSoffice} onChange={(e) => setEnableSoffice(e.target.checked)} />
                  <span>Utiliser LibreOffice pour les anciens formats</span>
                </label>
              </div>
              <div className="form-group checkbox-group">
                <label>
                  <input type="checkbox" checked={autoPdf} onChange={(e) => setAutoPdf(e.target.checked)} />
                  <span>Creer aussi un PDF</span>
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      <button
        onClick={handleCreateReport}
        disabled={loading || !selectedClient || !templateReady}
        className="btn-primary btn-generate"
      >
        {loading ? 'Generation en cours...' : 'Generer le rapport'}
      </button>
    </div>
  );
}

export default ClientSelection;
