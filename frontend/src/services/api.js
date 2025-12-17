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
  getOllamaModels: async () => {
    const response = await apiClient.get('/ollama/models');
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
  deleteReport: async (jobId) => {
    const response = await apiClient.delete(`/reports/${jobId}`);
    return response.data;
  },
};

export default apiClient;
