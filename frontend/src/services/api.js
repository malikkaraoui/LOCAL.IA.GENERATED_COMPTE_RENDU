/**
 * Service API pour communiquer avec le backend FastAPI.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * API Santé
 */
export const healthAPI = {
  checkHealth: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },
  
  checkOllama: async () => {
    const response = await apiClient.get('/health/ollama');
    return response.data;
  },
  
  /**
   * Récupérer la liste des modèles Ollama disponibles
   */
  getOllamaModels: async (host) => {
    const response = await apiClient.get('/ollama/models', {
      params: host ? { host } : undefined,
    });
    return response.data;
  },

  /**
   * Restart soft des LLM (unload des modèles actifs via keep_alive=0)
   */
  restartOllama: async (host) => {
    const response = await apiClient.post('/ollama/restart', { host });
    return response.data;
  },
};

/**
 * API Rapports
 */
export const reportsAPI = {
  /**
   * Liste des clients disponibles
   */
  listClients: async () => {
    const response = await apiClient.get('/clients');
    return response.data;
  },

  /**
   * Liste des templates DOCX disponibles côté serveur
   */
  listTemplates: async () => {
    const response = await apiClient.get('/templates');
    return response.data;
  },

  /**
   * Upload d'un template DOCX via le navigateur
   */
  uploadTemplate: async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/templates/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Créer un nouveau rapport
   */
  createReport: async (clientName, sourceFile = null, extractMethod = 'auto', additionalParams = {}) => {
    const response = await apiClient.post('/reports', {
      client_name: clientName,
      source_file: sourceFile,
      extract_method: extractMethod,
      ...additionalParams,
    });
    return response.data;
  },
  
  /**
   * Récupérer le statut d'un rapport
   */
  getReportStatus: async (jobId) => {
    const response = await apiClient.get(`/reports/${jobId}`);
    return response.data;
  },
  
  /**
   * Stream SSE pour suivre la progression
   */
  streamReportProgress: (jobId, onMessage, onError) => {
    const eventSource = new EventSource(`${API_BASE_URL}/reports/${jobId}/stream`);
    
    eventSource.addEventListener('status', (event) => {
      const data = JSON.parse(event.data);
      onMessage({ type: 'status', data });
    });
    
    eventSource.addEventListener('log', (event) => {
      const data = JSON.parse(event.data);
      onMessage({ type: 'log', data });
    });

    eventSource.addEventListener('progress', (event) => {
      const data = JSON.parse(event.data);
      onMessage({ type: 'progress', data });
    });
    
    eventSource.addEventListener('complete', (event) => {
      const data = JSON.parse(event.data);
      onMessage({ type: 'complete', data });
      eventSource.close();
    });
    
    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      onError(error);
      eventSource.close();
    };
    
    return eventSource;
  },
  
  /**
   * Télécharger le rapport généré
   */
  downloadReport: async (jobId) => {
    const response = await apiClient.get(`/reports/${jobId}/download`, {
      responseType: 'blob',
    });
    
    // Créer un lien de téléchargement
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `rapport_${jobId}.docx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  
  /**
   * Supprimer un rapport
   */
  deleteReport: async (jobId, options = {}) => {
    const params = options?.force ? { force: true } : undefined;
    const response = await apiClient.delete(`/reports/${jobId}`, { params });
    return response.data;
  },
};

/**
 * API Admin (local dev) — gestion des workers
 */
export const adminAPI = {
  /**
   * (Re)démarrer les workers RQ.
   * - kill=true: coupe les workers existants avant de relancer
   * - count: nombre de workers à lancer
   */
  restartWorkers: async ({ count = 1, kill = true } = {}) => {
    const response = await apiClient.post('/admin/workers/restart', null, {
      params: { count, kill },
    });
    return response.data;
  },
};

/**
 * API RAG Audio (local)
 */
export const ragAudioAPI = {
  /**
   * Enqueue l'ingestion (transcription) des audios déjà présents sur disque
   * dans CLIENTS/<source_id>/... (scan côté serveur).
   */
  ingestLocal: async ({ sourceId, maxFiles = 25, skipAlreadyIngested = true } = {}) => {
    const response = await apiClient.post('/rag/audio/ingest-local', null, {
      params: {
        source_id: sourceId,
        max_files: maxFiles,
        skip_already_ingested: skipAlreadyIngested,
      },
    });
    return response.data;
  },

  /**
   * Statut d'ingestion: nb de transcriptions .txt/.json
   */
  status: async ({ sourceId } = {}) => {
    const response = await apiClient.get('/rag/audio/status', {
      params: { source_id: sourceId },
    });
    return response.data;
  },
};

/**
 * API Branding (header/footer DOCX)
 */
export const brandingAPI = {
  /**
   * Appliquer le branding et télécharger le DOCX résultat.
   * Retour: { blob, filename }
   */
  applyBranding: async (formData) => {
    const response = await apiClient.post('/branding/apply', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob',
    });

    // Essayer de récupérer le nom de fichier depuis Content-Disposition
    const cd = response.headers?.['content-disposition'] || response.headers?.['Content-Disposition'];
    let filename = 'branding.docx';
    if (cd) {
      const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(cd);
      const raw = match?.[1] || match?.[2];
      if (raw) {
        try {
          filename = decodeURIComponent(raw);
        } catch {
          filename = raw;
        }
      }
    }

    return { blob: response.data, filename };
  },
};

/**
 * API Training (analyse de patterns)
 */
export const trainingAPI = {
  /**
   * Démarrer une analyse d'entraînement
   */
  start: async (payload) => {
    const response = await apiClient.post('/training/start', payload);
    return response.data;
  },

  /**
   * Récupérer le statut d'un job d'entraînement
   */
  getStatus: async (jobId) => {
    const response = await apiClient.get(`/training/${jobId}/status`);
    return response.data;
  },
};

export default apiClient;
