import { useState, useEffect } from 'react';
import { reportsAPI, healthAPI, brandingAPI } from '../services/api';
import './ClientSelection.css';

/**
 * Page de configuration et génération de rapport.
 */
function ClientSelection() {
  const DEFAULT_TEMPLATE = 'TEMPLATE_SIMPLE_BASE1.docx';
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
  const [templatePath, setTemplatePath] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [templates, setTemplates] = useState([]);
  const [templateUploading, setTemplateUploading] = useState(false);
  const [templateLocalFile, setTemplateLocalFile] = useState(null);
  const [outputDir, setOutputDir] = useState('./out');

  const templateSelectionOk = Boolean((templateName && templateName.trim()) || (templatePath && templatePath.trim()));
  const templateNameAvailable = Boolean(templateName && templates.includes(templateName));

  // LLM
  const [llmHost, setLlmHost] = useState('http://localhost:11434');
  const [llmModel, setLlmModel] = useState('llama3.1:8b');
  const [llmCustom, setLlmCustom] = useState('');
  const [useCustomModel, setUseCustomModel] = useState(false);
  const [maxChars, setMaxChars] = useState(500);
  const [availableModels, setAvailableModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [llmRestarting, setLlmRestarting] = useState(false);
  const [llmRestartMessage, setLlmRestartMessage] = useState(null);
  const [llmModelsError, setLlmModelsError] = useState(null);

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

  // Branding (entête/pied) – appliqué AVANT la génération du rapport
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

  // Fonction pour charger les modèles Ollama  
  const loadOllamaModels = async () => {
    setModelsLoading(true);
    setLlmModelsError(null);
    try {
      const response = await healthAPI.getOllamaModels(llmHost);
      setAvailableModels(response.models || []);
      
      if (response.models && response.models.length > 0 && !llmModel) {
        setLlmModel(response.models[0].name);
      }
    } catch (err) {
      console.error('Erreur lors du chargement des modèles:', err);
      const detail = err?.response?.data?.detail || err?.message;
      setLlmModelsError(detail || "Erreur lors du chargement des modèles");
      setAvailableModels([
        { name: 'qwen3-next:latest', available: false },
        { name: 'mistral:latest', available: false },
        { name: 'llama3.1:8b', available: false },
        { name: 'qwen3-vl:2b', available: false },
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
      const unloadedCount = Array.isArray(resp?.unloaded) ? resp.unloaded.length : 0;
      const runningCount = Array.isArray(resp?.running_models) ? resp.running_models.length : 0;
      const errCount = Array.isArray(resp?.errors) ? resp.errors.length : 0;

      const msg =
        runningCount === 0
          ? '✅ Aucun modèle actif à redémarrer (Ollama répond bien)'
          : `✅ Restart demandé : ${unloadedCount}/${runningCount} modèle(s) déchargé(s)` + (errCount ? ` (⚠️ ${errCount} erreur(s))` : '');

      setLlmRestartMessage({ type: errCount ? 'warning' : 'success', text: msg });
      // Rafraîchir la liste des modèles (et l'état)
      await loadOllamaModels();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setLlmRestartMessage({
        type: 'error',
        text: detail || '❌ Impossible de redémarrer les LLM (Ollama)'
      });
    } finally {
      setLlmRestarting(false);
    }
  };

  // Charger les modèles au démarrage
  useEffect(() => {
    loadOllamaModels();

    // Charger la liste des clients depuis le backend
    (async () => {
      try {
        const resp = await reportsAPI.listClients();
        setClients(resp.clients || []);
      } catch (err) {
        console.error('Erreur lors du chargement des clients:', err);
        // Fallback (évite un écran vide si le backend est temporairement down)
        setClients(['KARAOUI Malik']);
      }
    })();

    // Charger la liste des templates disponibles
    (async () => {
      try {
        const resp = await reportsAPI.listTemplates();
        const list = Array.isArray(resp.templates) ? resp.templates : [];
        const uniq = Array.from(new Set(list.filter(Boolean)));
        setTemplates(uniq);
        if (!templateName) {
          // Sélectionner le premier template réellement disponible côté serveur.
          setTemplateName(uniq[0] || '');
        }
      } catch (err) {
        console.warn('Impossible de charger la liste des templates:', err);
        setTemplates([]);
        if (!templateName) setTemplateName('');
      }
    })();
  }, []);

  const handleTemplateFileSelected = async (file) => {
    if (!file) return;
    setTemplateLocalFile(file);
    if (!file.name?.toLowerCase().endsWith('.docx')) {
      setError('Le template doit être un fichier .docx');
      return;
    }
    setTemplateUploading(true);
    setError(null);
    try {
      const resp = await reportsAPI.uploadTemplate(file);
      const uploadedName = resp.template_name;
      setTemplateName(uploadedName);
      // En mode upload, on n'utilise pas template_path
      if (uploadedName && !templates.includes(uploadedName)) {
        setTemplates((prev) => [uploadedName, ...prev]);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || 'Erreur lors de l’upload du template');
    } finally {
      setTemplateUploading(false);
    }
  };

  const FilePicker = ({
    id,
    accept,
    disabled,
    file,
    onFileSelected,
    buttonLabel,
    placeholder,
  }) => {
    return (
      <div className="flex w-full min-w-0 items-center gap-3">
        <input
          id={id}
          type="file"
          accept={accept}
          className="sr-only"
          disabled={disabled}
          onChange={(e) => onFileSelected?.(e.target.files?.[0] || null)}
        />
        <label
          htmlFor={id}
          className={
            "inline-flex shrink-0 items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-sm " +
            "hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2 " +
            (disabled ? "opacity-50 cursor-not-allowed hover:bg-indigo-600" : "cursor-pointer")
          }
        >
          {buttonLabel}
        </label>
        <div
          className={
            "min-w-0 flex-1 truncate rounded-md border px-3 py-2 text-sm " +
            (file ? "border-slate-200 bg-slate-50 text-slate-900" : "border-slate-200 bg-white text-slate-500")
          }
          title={file?.name || ''}
        >
          {file ? file.name : placeholder}
        </div>
      </div>
    );
  };

  const getLocationDatePreview = () => {
    if (autoDate) {
      const today = new Date();
      return `${locationCity}, le ${today.toLocaleDateString('fr-FR', { 
        day: 'numeric', 
        month: 'long', 
        year: 'numeric' 
      })}`;
    }
    return manualDate ? `${locationCity}, le ${manualDate}` : locationCity;
  };

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
      } catch {
        return null;
      }
    }

    return err?.response?.data?.detail || null;
  };

  const applyBrandingAndUploadTemplateIfNeeded = async () => {
    if (!brandingEnabled) {
      return templateName || null;
    }

    // Construire FormData pour /api/branding/apply
    const fd = new FormData();

    // Template: idéalement template_name (upload/liste). template_path reste un fallback dev.
    // Si le template sélectionné n'existe pas dans la liste serveur, on évite d'envoyer template_name.
    if (templateName && templateNameAvailable) {
      fd.append('template_name', templateName);
    } else if (templatePath) {
      fd.append('template_path', templatePath);
    }

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

    // Appeler l'API branding (retourne un DOCX)
    const { blob, filename } = await brandingAPI.applyBranding(fd);
    const docxName = filename || `template_brande_${Date.now()}.docx`;
    const file = new File([blob], docxName, {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });

    // Uploader le template brandé côté serveur puis l'utiliser pour le rapport
    const uploadResp = await reportsAPI.uploadTemplate(file);
    const newTemplateName = uploadResp.template_name;
    if (newTemplateName) {
      setTemplateName(newTemplateName);
      if (!templates.includes(newTemplateName)) {
        setTemplates((prev) => [newTemplateName, ...prev]);
      }
    }
    return newTemplateName || null;
  };

  const handleCreateReport = async () => {
    if (!selectedClient) {
      setError('Veuillez sélectionner un client');
      return;
    }

    // Empêche un call backend inutile si aucun template n'est prêt.
    if (!templateSelectionOk) {
      setError('Veuillez sélectionner ou uploader un template DOCX avant de générer un rapport.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1) Branding (optionnel) avant génération: produit un template brandé et le sélectionne
      let effectiveTemplateName = templateName || null;
      if (effectiveTemplateName && !templateNameAvailable) {
        // Sécurité: si un nom est saisi mais pas réellement disponible côté serveur, on force le fallback path.
        effectiveTemplateName = null;
      }
      if (brandingEnabled) {
        try {
          effectiveTemplateName = await applyBrandingAndUploadTemplateIfNeeded();
        } catch (err) {
          const detail = await extractDetailFromAxiosBlobError(err);
          setError(detail || 'Erreur lors de l\'application du branding');
          setLoading(false);
          return;
        }
      }

      const finalModel = useCustomModel ? llmCustom : llmModel;
      
      // Calculer le multiplicateur basé sur la longueur max choisie (base = 500)
      const maxCharsMultiplier = maxChars / 500;
      
      const response = await reportsAPI.createReport(
        selectedClient,
        null, // source_file
        'auto', // extract_method
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
          // IMPORTANT: un navigateur ne peut pas transmettre un chemin local exploitable;
          // si un template est choisi via upload/liste, on utilise template_name.
          template_name: effectiveTemplateName || undefined,
          template_path: effectiveTemplateName ? undefined : templatePath,
          output_dir: outputDir,
          // ✅ Objet LLM unifié (rétrocompatibilité maintenue via champs legacy)
          llm: {
            provider: 'ollama',
            base_url: llmHost,
            model: finalModel,
            temperature,
            max_tokens: 4096,
            top_p: topP,
            timeout: 900.0
          },
          // Legacy params (pour rétrocompatibilité si llm n'est pas traité)
          llm_host: llmHost,
          llm_model: finalModel,
          topk: topK,
          temperature,
          top_p: topP,
          max_chars_multiplier: maxCharsMultiplier,
          include_filters: includeFilters,
          exclude_filters: excludeFilters,
          force_reextract: forceReextract,
          enable_soffice: enableSoffice,
          export_pdf: autoPdf,
        }
      );
      
      window.location.href = `/progress/${response.job_id}`;
    } catch (err) {
      const detail = err.response?.data?.detail;
      const status = err.response?.status;
      setError(detail || (status ? `Erreur HTTP ${status} lors de la création du rapport` : 'Erreur lors de la création du rapport'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="client-selection">
      <h1>🤖 Génération de Rapport</h1>
      
      <div className="form-grid">
        {/* Section Client */}
        <div className="form-section">
          <h3>📁 Client et Chemins</h3>
          
          <div className="form-row">
            <div className="form-group">
              <label>Dossier clients</label>
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
              <label>Client *</label>
              <select
                value={selectedClient}
                onChange={(e) => setSelectedClient(e.target.value)}
                disabled={loading}
              >
                <option value="">-- Sélectionner --</option>
                {clients.map((client) => (
                  <option key={client} value={client}>{client}</option>
                ))}
              </select>
              <small className="hint" style={{ marginTop: '8px', display: 'block', opacity: 0.8 }}>
                📄 Formats RAG supportés: PDF, DOCX, TXT, <strong>MSG (Outlook)</strong>, M4A, MP3, WAV
              </small>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Template DOCX</label>
              <div className="template-picker">
                {templates.length === 0 && !templateLocalFile && (
                  <div className="hint" style={{ marginBottom: '8px', padding: '8px 10px', border: '1px solid #e5e7eb', borderRadius: 8, background: '#fff7ed' }}>
                    ⚠️ Aucun template DOCX n’est disponible côté serveur. Uploade un <strong>.docx</strong> via “Parcourir…”.
                  </div>
                )}

                <div className="template-picker-row">
                  <FilePicker
                    id="template-docx"
                    accept=".docx"
                    disabled={loading || templateUploading}
                    file={templateLocalFile}
                    onFileSelected={(file) => handleTemplateFileSelected(file)}
                    buttonLabel={templateUploading ? 'Upload…' : 'Parcourir…'}
                    placeholder="Aucun template sélectionné"
                  />
                  {templateName && (
                    <small className="hint">Template côté serveur: <strong>{templateName}</strong></small>
                  )}
                </div>

                <div className="template-picker-row">
                  <select
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    disabled={loading}
                  >
                    <option value="">— Sélectionner un template —</option>
                    {templates.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                {!templateName && (
                  <div className="template-picker-row">
                    <input
                      type="text"
                      value={templatePath}
                      onChange={(e) => setTemplatePath(e.target.value)}
                      placeholder="(optionnel) chemin côté serveur, ex: ./uploaded_templates/mon_template.docx"
                    />
                    <small className="hint">
                      Mode avancé: chemin côté serveur (dev local). Sinon utilise “Parcourir…” au-dessus.
                    </small>
                  </div>
                )}

                {templateName && (
                  <small className="hint">Template sélectionné: <strong>{templateName}</strong></small>
                )}
              </div>
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

        {/* Section Branding */}
        <div className="form-section">
          <h3>🎨 Branding DOCX (avant génération)</h3>

          <div className="form-row">
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={brandingEnabled}
                  onChange={(e) => setBrandingEnabled(e.target.checked)}
                />
                <span>Appliquer l’entête/pied de page (logos + champs)</span>
              </label>
            </div>
          </div>

          {brandingEnabled && (
            <>
              <div className="form-row">
                <div className="form-group">
                  <label>Titre document (TITRE_DOCUMENT)</label>
                  <input
                    type="text"
                    value={brandingTitreDocument}
                    onChange={(e) => setBrandingTitreDocument(e.target.value)}
                    placeholder="ESSAI"
                  />
                </div>
                <div className="form-group">
                  <label>Société (SOCIETE)</label>
                  <input
                    type="text"
                    value={brandingSociete}
                    onChange={(e) => setBrandingSociete(e.target.value)}
                    placeholder="MALIK SAS"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Rue</label>
                  <input
                    type="text"
                    value={brandingRue}
                    onChange={(e) => setBrandingRue(e.target.value)}
                    placeholder="Joseph DessaiX"
                  />
                </div>
                <div className="form-group">
                  <label>Numéro</label>
                  <input
                    type="text"
                    value={brandingNumero}
                    onChange={(e) => setBrandingNumero(e.target.value)}
                    placeholder="2"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>CP</label>
                  <input
                    type="text"
                    value={brandingCp}
                    onChange={(e) => setBrandingCp(e.target.value)}
                    placeholder="74000"
                  />
                </div>
                <div className="form-group">
                  <label>Ville</label>
                  <input
                    type="text"
                    value={brandingVille}
                    onChange={(e) => setBrandingVille(e.target.value)}
                    placeholder="ANNECY"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Téléphone</label>
                  <input
                    type="text"
                    value={brandingTel}
                    onChange={(e) => setBrandingTel(e.target.value)}
                    placeholder="+33..."
                  />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input
                    type="text"
                    value={brandingEmail}
                    onChange={(e) => setBrandingEmail(e.target.value)}
                    placeholder="contact@..."
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Logo entête (PNG/JPG/TIFF)</label>
                  <FilePicker
                    id="branding-logo-header"
                    accept="image/png,image/jpeg,image/tiff"
                    disabled={loading}
                    file={brandingLogoHeader}
                    onFileSelected={(file) => setBrandingLogoHeader(file)}
                    buttonLabel="Parcourir…"
                    placeholder="Aucun logo sélectionné"
                  />
                </div>
                <div className="form-group">
                  <label>Logo pied de page (PNG/JPG/TIFF)</label>
                  <FilePicker
                    id="branding-logo-footer"
                    accept="image/png,image/jpeg,image/tiff"
                    disabled={loading}
                    file={brandingLogoFooter}
                    onFileSelected={(file) => setBrandingLogoFooter(file)}
                    buttonLabel="Parcourir…"
                    placeholder="Aucun logo sélectionné"
                  />
                </div>
              </div>

              {!templateName && (
                <div className="preview-box">
                  <strong>Note :</strong> Pour un branding fiable en mode navigateur, sélectionne un template via “Parcourir…” ou la liste.
                </div>
              )}
            </>
          )}
        </div>

        {/* Section Identité */}
        <div className="form-section">
          <h3>👤 Identité</h3>
          
          <div className="form-row">
            <div className="form-group">
              <label>Prénom</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Prénom"
              />
            </div>
            <div className="form-group">
              <label>Nom</label>
              <input
                type="text"
                value={surname}
                onChange={(e) => setSurname(e.target.value)}
                placeholder="Nom"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Civilité</label>
              <select
                value={civility}
                onChange={(e) => setCivility(e.target.value)}
              >
                <option value="Monsieur">Monsieur</option>
                <option value="Madame">Madame</option>
                <option value="Autre">Autre</option>
              </select>
            </div>
            <div className="form-group">
              <label>Numéro AVS</label>
              <input
                type="text"
                value={avsNumber}
                onChange={(e) => setAvsNumber(e.target.value)}
                placeholder="756.XXXX.XXXX.XX"
              />
            </div>
          </div>
        </div>

        {/* Section Localisation */}
        <div className="form-section">
          <h3>📍 Localisation et Date</h3>
          
          <div className="form-row">
            <div className="form-group">
              <label>Ville</label>
              <input
                type="text"
                value={locationCity}
                onChange={(e) => setLocationCity(e.target.value)}
                placeholder="Genève"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={autoDate}
                  onChange={(e) => setAutoDate(e.target.checked)}
                />
                <span>Date automatique (aujourd'hui)</span>
              </label>
            </div>
          </div>

          {!autoDate && (
            <div className="form-row">
              <div className="form-group">
                <label>Date manuelle</label>
                <input
                  type="text"
                  value={manualDate}
                  onChange={(e) => setManualDate(e.target.value)}
                  placeholder="15 décembre 2024"
                />
              </div>
            </div>
          )}

          <div className="preview-box">
            <strong>Prévisualisation :</strong> {getLocationDatePreview()}
          </div>
        </div>

        {/* Section LLM */}
        <div className="form-section">
          <h3>🧠 Configuration LLM</h3>
          
          <div className="form-row">
            <div className="form-group">
              <label>Serveur Ollama</label>
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
                  Modèle LLM
                  {modelsLoading && <span className="models-loading"> (Chargement...)</span>}
                </label>
                <button 
                  type="button" 
                  className="btn-refresh-models"
                  onClick={loadOllamaModels}
                  disabled={modelsLoading}
                  title="Rafraîchir la liste des modèles"
                >
                  🔄
                </button>
                <button
                  type="button"
                  className="btn-restart-llm"
                  onClick={restartAllLlm}
                  disabled={llmRestarting}
                  title="Restart all LLM (unload des modèles actifs)"
                >
                  ♻️
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
                {availableModels.map((model) => (
                  <option key={model.name} value={model.name}>
                    {model.available ? '🟢 ' : '🔴 '}{model.name}
                  </option>
                ))}
                {availableModels.length === 0 && (
                  <option disabled>Aucun modèle disponible</option>
                )}
                <option value="custom">✏️ Autre (personnalisé)</option>
              </select>

              {llmModelsError && (
                <div className="llm-restart-message llm-restart-error">
                  ❌ {llmModelsError}
                  <div style={{ marginTop: 4, opacity: 0.9 }}>
                    Astuce: si tu es sur <code>http://127.0.0.1:5174</code>, l'API doit autoriser cette origine (CORS).
                  </div>
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
                <label>Modèle personnalisé</label>
                <input
                  type="text"
                  value={llmCustom}
                  onChange={(e) => setLlmCustom(e.target.value)}
                  placeholder="phi3:mini"
                />
              </div>
            </div>
          )}

          <div className="form-row">
            <div className="form-group">
              <label>
                📏 Longueur max paragraphe
                <span style={{ marginLeft: 8, fontSize: '0.85em', opacity: 0.7 }}>
                  (évite les "..." de troncature)
                </span>
              </label>
              <select
                value={maxChars}
                onChange={(e) => setMaxChars(Number(e.target.value))}
                title="Longueur maximale des paragraphes générés par le LLM"
              >
                <option value={500}>500 caractères (défaut)</option>
                <option value={1000}>1000 caractères (2x plus long)</option>
                <option value={2000}>2000 caractères (4x plus long)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Options avancées */}
      <div className="advanced-section">
        <button
          type="button"
          className="btn-toggle"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          ⚙️ Options avancées {showAdvanced ? '▼' : '▶'}
        </button>

        {showAdvanced && (
          <div className="advanced-content">
            <div className="form-row">
              <div className="form-group">
                <label>Top-K passages ({topK})</label>
                <input
                  type="range"
                  min="3"
                  max="20"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                />
              </div>
              <div className="form-group">
                <label>Temperature ({temperature})</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                />
              </div>
              <div className="form-group">
                <label>Top-p ({topP})</label>
                <input
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.05"
                  value={topP}
                  onChange={(e) => setTopP(parseFloat(e.target.value))}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Inclure chemins (séparés par ,)</label>
                <input
                  type="text"
                  value={includeFilters}
                  onChange={(e) => setIncludeFilters(e.target.value)}
                  placeholder="01 Dossier, 02 Tests"
                />
              </div>
              <div className="form-group">
                <label>Exclure chemins (séparés par ,)</label>
                <input
                  type="text"
                  value={excludeFilters}
                  onChange={(e) => setExcludeFilters(e.target.value)}
                  placeholder="archive, old"
                />
              </div>
            </div>

            <div className="form-row checkbox-row">
              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={forceReextract}
                    onChange={(e) => setForceReextract(e.target.checked)}
                  />
                  <span>Forcer extraction</span>
                </label>
              </div>
              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={enableSoffice}
                    onChange={(e) => setEnableSoffice(e.target.checked)}
                  />
                  <span>LibreOffice</span>
                </label>
              </div>
              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={autoPdf}
                    onChange={(e) => setAutoPdf(e.target.checked)}
                  />
                  <span>PDF automatique</span>
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      <button
        onClick={handleCreateReport}
        disabled={loading || !selectedClient || !templateSelectionOk}
        className="btn-primary btn-generate"
      >
        {loading ? '⏳ Génération en cours...' : '🚀 Générer le Rapport'}
      </button>
    </div>
  );
}

export default ClientSelection;
