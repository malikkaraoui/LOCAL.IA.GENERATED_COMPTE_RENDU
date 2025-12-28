import { useMemo, useState, useEffect, useRef } from "react";
import { trainingAPI, reportsAPI } from "../services/api";

const DEFAULT_CONFIG = {
  batch_name: "BATCH_20",
  source_root: "/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20",
  sandbox_root: "/Users/malik/Documents/SCRIPT.IA_DATA/training_sandbox/BATCH_20",
  copy_mode: true,
  allowed_ext: [".pdf", ".docx", ".txt", ".msg"],
  folders: {
    personal: "01 Dossier personnel",
    tests: "03 Tests et bilans",
    stages: "04 Stages",
    ai: "05 Mesures AI",
    final: "06 Rapport final",
  },
  preprompt_system: `Objectif: apprendre des patterns de rédaction par section (placeholders).
Interdits: ne jamais mémoriser ni réutiliser des phrases issues du dataset; ne jamais produire de contenu nominatif.
Sorties attendues: stats + ruleset (longueur, ton, structure, sources autorisées, interdits, NOT_FOUND).`,
};

function joinExt(exts) {
  return exts.join(",");
}
function splitExt(s) {
  return s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) => (x.startsWith(".") ? x : `.${x}`));
}

export default function Training() {
  const [activeTab, setActiveTab] = useState("dataset"); // "dataset" | "test"
  const [cfg, setCfg] = useState(DEFAULT_CONFIG);
  const [extInput, setExtInput] = useState(joinExt(DEFAULT_CONFIG.allowed_ext));
  const [status, setStatus] = useState("idle"); // idle | queued | running | done | error
  const [logs, setLogs] = useState("");
  const [progress, setProgress] = useState(0);
  const pollingIntervalRef = useRef(null);
  
  // Test Client states
  const [clientSearch, setClientSearch] = useState("");
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [profile, setProfile] = useState("STANDARD");
  const [testRunning, setTestRunning] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const payload = useMemo(() => {
    return {
      ...cfg,
      allowed_ext: splitExt(extInput),
    };
  }, [cfg, extInput]);

  const onChange = (key) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setCfg((prev) => ({ ...prev, [key]: value }));
  };

  const onFolderChange = (folderKey) => (e) => {
    const value = e.target.value;
    setCfg((prev) => ({
      ...prev,
      folders: { ...prev.folders, [folderKey]: value },
    }));
  };

  const appendLog = (line) => {
    setLogs((prev) => (prev ? `${prev}\n${line}` : line));
  };

  // Polling du status
  const pollStatus = async (jobId) => {
    try {
      const statusData = await trainingAPI.getStatus(jobId);
      const newStatus = statusData.status;
      const message = statusData.message || "";
      const prog = statusData.progress || 0;

      setStatus(newStatus);
      setProgress(prog);
      appendLog(`📊 [${newStatus.toUpperCase()}] ${message} (${prog}%)`);

      // Arrêter le polling si terminé
      if (newStatus === "done" || newStatus === "error") {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || String(err);
      appendLog(`❌ Erreur polling: ${errorMsg}`);
    }
  };

  // Cleanup du polling au unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const startTraining = async () => {
    setStatus("queued");
    setLogs("");
    setProgress(0);
    appendLog("▶️ Démarrage de l'analyse...");

    try {
      // Appel API pour démarrer
      const data = await trainingAPI.start(payload);
      const jobId = data.job_id;
      
      appendLog(`✅ Job créé: ${jobId}`);
      appendLog(`📊 Statut initial: ${data.status}`);

      // Démarrer le polling toutes les 1 seconde
      pollingIntervalRef.current = setInterval(() => {
        pollStatus(jobId);
      }, 1000);

      // Premier poll immédiat
      await pollStatus(jobId);
      
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || String(err);
      appendLog(`❌ Erreur: ${errorMsg}`);
      setStatus("error");
    }
  };

  // Load clients list for Test tab
  useEffect(() => {
    if (activeTab === "test") {
      loadClients();
    }
  }, [activeTab]);

  const loadClients = async () => {
    try {
      const data = await reportsAPI.listClients();
      setClients(data.clients || []);
    } catch (err) {
      console.error("Error loading clients:", err);
    }
  };

  const runTest = async () => {
    if (!selectedClient) return;
    
    setTestRunning(true);
    setTestResult(null);
    
    try {
      const result = await reportsAPI.testClient({
        client_name: selectedClient,
        profile: profile,
      });
      setTestResult(result);
    } catch (err) {
      setTestResult({
        success: false,
        error: err.response?.data?.detail || err.message
      });
    } finally {
      setTestRunning(false);
    }
  };

  const filteredClients = useMemo(() => {
    if (!clientSearch) return clients;
    return clients.filter(c => 
      c.toLowerCase().includes(clientSearch.toLowerCase())
    );
  }, [clients, clientSearch]);

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h2 className="text-2xl font-semibold mb-2 text-white">🎓 Training & Test UI</h2>
      <p className="text-white/70 text-sm mb-6">
        Nouvelle page complète avec 2 onglets (Entraîner Dataset / Test Client)
      </p>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-white/20">
        <button
          onClick={() => setActiveTab("dataset")}
          className={`px-6 py-3 font-medium transition-all ${
            activeTab === "dataset"
              ? "text-emerald-400 border-b-2 border-emerald-400"
              : "text-white/60 hover:text-white/90"
          }`}
        >
          📊 Entraîner Dataset
        </button>
        <button
          onClick={() => setActiveTab("test")}
          className={`px-6 py-3 font-medium transition-all ${
            activeTab === "test"
              ? "text-emerald-400 border-b-2 border-emerald-400"
              : "text-white/60 hover:text-white/90"
          }`}
        >
          🧪 Test Client
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-white/20">
        <button
          onClick={() => setActiveTab("dataset")}
          className={`px-6 py-3 font-medium transition-all ${
            activeTab === "dataset"
              ? "text-emerald-400 border-b-2 border-emerald-400"
              : "text-white/60 hover:text-white/90"
          }`}
        >
          📊 Entraîner Dataset
        </button>
        <button
          onClick={() => setActiveTab("test")}
          className={`px-6 py-3 font-medium transition-all ${
            activeTab === "test"
              ? "text-emerald-400 border-b-2 border-emerald-400"
              : "text-white/60 hover:text-white/90"
          }`}
        >
          🧪 Test Client
        </button>
      </div>

      {/* Tab Content: Dataset */}
      {activeTab === "dataset" && (
        <>
          {/* Bloc A */}
          <div className="bg-white/10 border border-white/20 rounded-2xl p-6 mb-5">
            <h3 className="text-lg font-semibold text-white mb-5">1) Dataset & chemins</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Batch name
                </label>
                <input 
                  type="text"
                  value={cfg.batch_name} 
                  onChange={onChange("batch_name")}
                  className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Source root (dataset)
                </label>
                <input 
                  type="text"
                  value={cfg.source_root} 
                  onChange={onChange("source_root")}
                  className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Sandbox root (copie de travail)
                </label>
                <input 
                  type="text"
                  value={cfg.sandbox_root} 
                  onChange={onChange("sandbox_root")}
                  className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                />
              </div>

              <div className="flex items-center pt-8">
                <label className="flex items-center gap-3 cursor-pointer select-none text-white/90">
                  <input 
                    type="checkbox" 
                    checked={cfg.copy_mode} 
                    onChange={onChange("copy_mode")}
                    className="w-5 h-5 rounded border-white/30 text-emerald-500 focus:ring-2 focus:ring-emerald-500/50 cursor-pointer"
                  />
                  <span className="text-sm font-medium">Copy mode (safe)</span>
                </label>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Extensions (csv)
                </label>
                <input 
                  type="text"
                  value={extInput} 
                  onChange={(e) => setExtInput(e.target.value)}
                  className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                />
              </div>
            </div>
          </div>

          {/* Bloc B */}
          <div className="bg-white/10 border border-white/20 rounded-2xl p-6 mb-5">
            <h3 className="text-lg font-semibold text-white mb-5">2) Mapping dossiers</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Dossier personnel
                </label>
                <input 
                  type="text"
                  value={cfg.folders.personal} 
                  onChange={onFolderChange("personal")}
                  className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Tests et bilans
                </label>
                <input 
                  type="text"
                  value={cfg.folders.tests} 
                  onChange={onFolderChange("tests")}
                  className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Stages
                </label>
                <input 
                  type="text"
                  value={cfg.folders.stages} 
                  onChange={onFolderChange("stages")}
                  className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Mesures AI
                </label>
                <input 
                  type="text"
                  value={cfg.folders.ai} 
                  onChange={onFolderChange("ai")}
                  className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                />
              </div>
              
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-white/90 mb-2">
                  Rapport final (gold)
                </label>
                <input 
                  type="text"
                  value={cfg.folders.final} 
                  onChange={onFolderChange("final")}
                  className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
                />
              </div>
            </div>
          </div>

          {/* Bloc C */}
          <div className="bg-white/10 border border-white/20 rounded-2xl p-6 mb-5">
            <h3 className="text-lg font-semibold text-white mb-5">3) Pré-prompt (au-dessus du prompt)</h3>
            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">
                System / coaching prompt
              </label>
              <textarea
                rows={8}
                value={cfg.preprompt_system}
                onChange={onChange("preprompt_system")}
                className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 font-mono text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all resize-y"
              />
            </div>
          </div>

          {/* Bloc D */}
          <div className="bg-white/10 border border-white/20 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-white mb-5">4) Lancer</h3>
            
            <div className="flex items-center gap-4 mb-5">
              <button
                onClick={startTraining}
                disabled={status === "queued" || status === "running"}
                className="px-7 py-3 bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white font-semibold rounded-lg shadow-lg shadow-emerald-500/30 hover:shadow-xl hover:shadow-emerald-500/40 transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:bg-gray-600"
              >
                {status === "queued" ? "⏳ En file..." : status === "running" ? "⚙️ Analyse en cours..." : "🚀 Lancer analyse"}
              </button>
              <div className="flex flex-col gap-1">
                <span className="text-white/70 text-sm">
                  Status: <span className="font-medium text-white">{status}</span>
                </span>
                {(status === "queued" || status === "running") && (
                  <div className="flex items-center gap-2">
                    <div className="w-32 h-2 bg-white/20 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <span className="text-xs text-white/70">{progress}%</span>
                  </div>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">
                Logs
              </label>
              <textarea
                rows={12}
                value={logs}
                readOnly
                className="w-full px-4 py-3 bg-gray-900/80 border border-white/20 rounded-lg text-emerald-400 font-mono text-xs leading-relaxed focus:outline-none resize-y"
              />
            </div>
          </div>
        </>
      )}

      {/* Tab Content: Test Client */}
      {activeTab === "test" && (
        <>
          <div className="bg-white/10 border border-white/20 rounded-2xl p-6 mb-5">
            <h3 className="text-lg font-semibold text-white mb-5">🔍 Rechercher un client</h3>
            
            <div className="mb-4">
              <input
                type="text"
                placeholder="Rechercher un client..."
                value={clientSearch}
                onChange={(e) => setClientSearch(e.target.value)}
                className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
              />
            </div>

            <div className="max-h-64 overflow-y-auto bg-white/5 border border-white/10 rounded-lg">
              {filteredClients.map((client, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedClient(client)}
                  className={`w-full text-left px-4 py-2 hover:bg-white/10 transition-colors ${
                    selectedClient === client ? "bg-emerald-500/20 text-emerald-300" : "text-white/80"
                  }`}
                >
                  {client}
                </button>
              ))}
            </div>

            {selectedClient && (
              <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300">
                ✓ Client sélectionné : <strong>{selectedClient}</strong>
              </div>
            )}
          </div>

          <div className="bg-white/10 border border-white/20 rounded-2xl p-6 mb-5">
            <h3 className="text-lg font-semibold text-white mb-5">⚙️ Paramètres</h3>
            
            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">
                Profil de validation
              </label>
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value)}
                className="w-full px-4 py-3 bg-white/15 border border-white/30 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
              >
                <option value="STRICT">STRICT</option>
                <option value="STANDARD">STANDARD</option>
                <option value="DRAFT">DRAFT</option>
              </select>
            </div>
          </div>

          <div className="bg-white/10 border border-white/20 rounded-2xl p-6 mb-5">
            <h3 className="text-lg font-semibold text-white mb-5">🚀 Lancer le test</h3>
            
            <button
              onClick={runTest}
              disabled={!selectedClient || testRunning}
              className="px-7 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white font-semibold rounded-lg shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40 transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            >
              {testRunning ? "⏳ Test en cours..." : "🧪 Lancer pipeline complet"}
            </button>
          </div>

          {testResult && (
            <div className="bg-white/10 border border-white/20 rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-white mb-5">📊 Résultats</h3>
              
              {testResult.error ? (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300">
                  ❌ {testResult.error}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className={`p-4 rounded-lg ${
                    testResult.status === "GO" ? "bg-green-500/10 border border-green-500/30 text-green-300" :
                    testResult.status === "DRAFT" ? "bg-yellow-500/10 border border-yellow-500/30 text-yellow-300" :
                    "bg-red-500/10 border border-red-500/30 text-red-300"
                  }`}>
                    <div className="font-semibold text-lg mb-2">
                      Status: {testResult.status}
                    </div>
                    <div className="text-sm">
                      Score: {testResult.score || "N/A"}
                    </div>
                  </div>

                  {testResult.reasons && (
                    <div className="p-4 bg-white/5 rounded-lg">
                      <div className="font-medium text-white mb-2">Raisons:</div>
                      <ul className="list-disc list-inside text-white/70 text-sm space-y-1">
                        {testResult.reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {testResult.actions && (
                    <div className="p-4 bg-white/5 rounded-lg">
                      <div className="font-medium text-white mb-2">Actions recommandées:</div>
                      <ul className="list-disc list-inside text-white/70 text-sm space-y-1">
                        {testResult.actions.map((a, i) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
