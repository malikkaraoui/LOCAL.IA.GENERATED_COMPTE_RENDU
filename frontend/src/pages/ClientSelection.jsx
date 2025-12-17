import { useState, useEffect } from 'react';
import { reportsAPI, healthAPI } from '../services/api';
import './ClientSelection.css';

/**
 * Page de configuration et génération de rapport.
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
  const [templatePath, setTemplatePath] = useState('./TemplateRapportStage.docx');
  const [templateName, setTemplateName] = useState('');
  const [templates, setTemplates] = useState([]);
  const [templateUploading, setTemplateUploading] = useState(false);
  const [outputDir, setOutputDir] = useState('./out');

  // LLM
  const [llmHost, setLlmHost] = useState('http://localhost:11434');
  const [llmModel, setLlmModel] = useState('mistral:latest');
  const [llmCustom, setLlmCustom] = useState('');
  const [useCustomModel, setUseCustomModel] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);

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

  // Fonction pour charger les modèles Ollama  
  const loadOllamaModels = async () => {
    setModelsLoading(true);
    try {
      const response = await healthAPI.getOllamaModels();
      setAvailableModels(response.models || []);
      
      if (response.models && response.models.length > 0 && !llmModel) {
        setLlmModel(response.models[0].name);
      }
    } catch (err) {
      console.error('Erreur lors du chargement des modèles:', err);
      setAvailableModels([
        { name: 'mistral:latest', available: false },
        { name: 'llama3.1:8b', available: false },
        { name: 'qwen3-vl:2b', available: false },
      ]);
    } finally {
      setModelsLoading(false);
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
        setTemplates(resp.templates || []);
      } catch (err) {
        console.warn('Impossible de charger la liste des templates:', err);
        setTemplates([]);
      }
    })();
  }, []);

  const handleTemplateFileSelected = async (file) => {
    if (!file) return;
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

  const handleCreateReport = async () => {
    if (!selectedClient) {
      setError('Veuillez sélectionner un client');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const finalModel = useCustomModel ? llmCustom : llmModel;
      
      const response = await reportsAPI.createReport(
        selectedClient,
        null, // source_file
        'auto', // extract_method
        {
          name,
          surname,
          civility,
          avs_number: avsNumber,
          location_city: locationCity,
          location_date: getLocationDatePreview(),
          auto_location_date: autoDate,
          clients_root: clientsRoot,
          // IMPORTANT: un navigateur ne peut pas transmettre un chemin local exploitable;
          // si un template est choisi via upload/liste, on utilise template_name.
          template_name: templateName || undefined,
          template_path: templateName ? undefined : templatePath,
          output_dir: outputDir,
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
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Template DOCX</label>
              <div className="template-picker">
                <div className="template-picker-row">
                  <input
                    type="file"
                    accept=".docx"
                    disabled={loading || templateUploading}
                    onChange={(e) => handleTemplateFileSelected(e.target.files?.[0])}
                  />
                  {templateUploading && (
                    <span className="template-uploading">Upload…</span>
                  )}
                </div>

                <div className="template-picker-row">
                  <select
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    disabled={loading}
                  >
                    <option value="">— Utiliser le template par défaut / chemin —</option>
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
                      placeholder="./TemplateRapportStage.docx"
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
        disabled={loading || !selectedClient}
        className="btn-primary btn-generate"
      >
        {loading ? '⏳ Génération en cours...' : '🚀 Générer le Rapport'}
      </button>
    </div>
  );
}

export default ClientSelection;
