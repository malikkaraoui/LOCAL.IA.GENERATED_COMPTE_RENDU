import { useMemo, useState } from "react";
import { trainingAPI } from "../services/api";

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
  const [cfg, setCfg] = useState(DEFAULT_CONFIG);
  const [extInput, setExtInput] = useState(joinExt(DEFAULT_CONFIG.allowed_ext));
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [logs, setLogs] = useState("");

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

  const startTraining = async () => {
    setStatus("running");
    setLogs("");
    appendLog("▶️ Démarrage…");

    try {
      // Appel API réel
      const data = await trainingAPI.start(payload);
      appendLog(`✅ Job créé: ${data.job_id}`);
      appendLog(`📊 Statut: ${data.status}`);
      
      // Récupérer le statut détaillé
      const statusData = await trainingAPI.getStatus(data.job_id);
      appendLog(`💬 Message: ${statusData.message || 'N/A'}`);
      
      setStatus("done");
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || String(err);
      appendLog(`❌ Erreur: ${errorMsg}`);
      setStatus("error");
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h2 className="text-2xl font-semibold mb-2 text-white">🧪 Entraînement (analyse & règles)</h2>
      <p className="text-white/70 text-sm mb-6">
        Cette page prépare les paramètres d'analyse pour produire un <b>ruleset</b> (pas de fine-tune).
      </p>

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
            disabled={status === "running"}
            className="px-7 py-3 bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white font-semibold rounded-lg shadow-lg shadow-emerald-500/30 hover:shadow-xl hover:shadow-emerald-500/40 transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:bg-gray-600"
          >
            {status === "running" ? "Analyse en cours…" : "Lancer analyse"}
          </button>
          <span className="text-white/70 text-sm">Status: <span className="font-medium text-white">{status}</span></span>
        </div>

        <div>
          <label className="block text-sm font-medium text-white/90 mb-2">
            Logs
          </label>
          <textarea
            rows={8}
            value={logs}
            readOnly
            className="w-full px-4 py-3 bg-gray-900/80 border border-white/20 rounded-lg text-emerald-400 font-mono text-xs leading-relaxed focus:outline-none resize-y"
          />
        </div>
      </div>
    </div>
  );
}
