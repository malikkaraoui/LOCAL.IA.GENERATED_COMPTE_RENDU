import React, { useState } from 'react';
import { FileBrowser } from '@/components/FileBrowser';
import { useFileBrowser } from '@/hooks/useFileBrowser';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FolderOpen, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface ScanResult {
  success: boolean;
  scan_result: any;
  detected_folders: any;
  gold_candidates: any[];
  files_by_type: Record<string, number>;
  identity_candidates: any;
  exploitable_summary: any;
}

export function TrainingPage() {
  // File browsers
  const datasetBrowser = useFileBrowser();
  const sandboxBrowser = useFileBrowser('./sandbox');

  // State
  const [datasetPath, setDatasetPath] = useState<string>('');
  const [sandboxPath, setSandboxPath] = useState<string>('./sandbox');
  const [batchName, setBatchName] = useState<string>('BATCH_TEST');
  
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Quand un dataset est sélectionné via le browser
  React.useEffect(() => {
    if (datasetBrowser.selectedPath) {
      setDatasetPath(datasetBrowser.selectedPath);
    }
  }, [datasetBrowser.selectedPath]);

  React.useEffect(() => {
    if (sandboxBrowser.selectedPath) {
      setSandboxPath(sandboxBrowser.selectedPath);
    }
  }, [sandboxBrowser.selectedPath]);

  // Scanner un batch
  const handleScanBatch = async () => {
    if (!datasetPath) {
      setError('Veuillez sélectionner un dataset');
      return;
    }

    setScanning(true);
    setError(null);
    setScanResult(null);

    try {
      const response = await axios.post(`${API_BASE}/api/training/scan-batch`, {
        dataset_root: datasetPath,
        batch_name: batchName,
      });

      console.log('Scan batch result:', response.data);
      // Vous pouvez traiter les résultats ici
      
    } catch (err: any) {
      console.error('Scan batch error:', err);
      setError(err.response?.data?.detail || 'Erreur lors du scan');
    } finally {
      setScanning(false);
    }
  };

  // Analyser un client spécifique
  const handleAnalyzeClient = async (clientPath: string) => {
    setScanning(true);
    setError(null);

    try {
      const response = await axios.post<ScanResult>(
        `${API_BASE}/api/training/analyze-client`,
        { client_folder_path: clientPath }
      );

      setScanResult(response.data);
    } catch (err: any) {
      console.error('Analyze client error:', err);
      setError(err.response?.data?.detail || 'Erreur lors de l\'analyse');
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">🎓 Entraînement Pipeline</h1>
        <p className="text-muted-foreground">
          Préparez et analysez les dossiers clients pour le pipeline RH-Pro
        </p>
      </div>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>
            Sélectionnez les dossiers pour le traitement
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Dataset Root */}
          <div className="space-y-2">
            <Label htmlFor="dataset">Dataset Root</Label>
            <div className="flex gap-2">
              <Input
                id="dataset"
                value={datasetPath}
                onChange={(e) => setDatasetPath(e.target.value)}
                placeholder="/path/to/dataset"
                className="flex-1"
              />
              <Button
                variant="outline"
                onClick={datasetBrowser.openBrowser}
              >
                <FolderOpen className="h-4 w-4 mr-2" />
                Browse
              </Button>
            </div>
          </div>

          {/* Sandbox Root */}
          <div className="space-y-2">
            <Label htmlFor="sandbox">Sandbox Root</Label>
            <div className="flex gap-2">
              <Input
                id="sandbox"
                value={sandboxPath}
                onChange={(e) => setSandboxPath(e.target.value)}
                placeholder="./sandbox"
                className="flex-1"
              />
              <Button
                variant="outline"
                onClick={sandboxBrowser.openBrowser}
              >
                <FolderOpen className="h-4 w-4 mr-2" />
                Browse
              </Button>
            </div>
          </div>

          {/* Batch Name */}
          <div className="space-y-2">
            <Label htmlFor="batch">Nom du Batch</Label>
            <Input
              id="batch"
              value={batchName}
              onChange={(e) => setBatchName(e.target.value)}
              placeholder="BATCH_TEST"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              onClick={handleScanBatch}
              disabled={!datasetPath || scanning}
            >
              {scanning ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Scan en cours...
                </>
              ) : (
                'Scanner le Batch'
              )}
            </Button>
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-destructive/10 text-destructive rounded-md">
              <AlertCircle className="h-4 w-4" />
              <p className="text-sm">{error}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Résultats */}
      {scanResult && (
        <Card>
          <CardHeader>
            <CardTitle>Résultats de l'Analyse</CardTitle>
            <CardDescription>
              {scanResult.exploitable_summary.can_process ? (
                <span className="flex items-center gap-2 text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                  Client prêt pour le pipeline
                </span>
              ) : (
                <span className="flex items-center gap-2 text-orange-600">
                  <AlertCircle className="h-4 w-4" />
                  Client non prêt
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Identity */}
            {scanResult.identity_candidates && (
              <div>
                <h3 className="font-semibold mb-2">Identité Détectée</h3>
                <div className="bg-muted p-3 rounded-md space-y-1">
                  <p className="text-sm">
                    <span className="font-medium">Nom:</span>{' '}
                    {scanResult.identity_candidates.nom || '-'}
                  </p>
                  <p className="text-sm">
                    <span className="font-medium">Prénom:</span>{' '}
                    {scanResult.identity_candidates.prenom || '-'}
                  </p>
                  {scanResult.identity_candidates.avs_candidates && (
                    <p className="text-sm">
                      <span className="font-medium">AVS:</span>{' '}
                      {scanResult.identity_candidates.avs_candidates.join(', ')}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* GOLD */}
            {scanResult.gold_candidates.length > 0 && (
              <div>
                <h3 className="font-semibold mb-2">Document GOLD</h3>
                <div className="bg-muted p-3 rounded-md">
                  <p className="text-sm font-mono break-all">
                    {scanResult.gold_candidates[0].path}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Score: {scanResult.gold_candidates[0].score.toFixed(2)} •{' '}
                    Stratégie: {scanResult.gold_candidates[0].strategy}
                  </p>
                </div>
              </div>
            )}

            {/* Sources RAG */}
            <div>
              <h3 className="font-semibold mb-2">
                Sources RAG ({scanResult.exploitable_summary.rag_sources_count})
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(scanResult.files_by_type).map(([ext, count]) => (
                  <div key={ext} className="bg-muted p-2 rounded-md text-sm">
                    <span className="font-medium">{ext}</span>: {count} fichier(s)
                  </div>
                ))}
              </div>
            </div>

            {/* Quality */}
            <div>
              <h3 className="font-semibold mb-2">Qualité Attendue</h3>
              <div className="flex items-center gap-2">
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    scanResult.exploitable_summary.expected_quality === 'high'
                      ? 'bg-green-100 text-green-700'
                      : scanResult.exploitable_summary.expected_quality === 'medium'
                      ? 'bg-orange-100 text-orange-700'
                      : 'bg-red-100 text-red-700'
                  }`}
                >
                  {scanResult.exploitable_summary.expected_quality.toUpperCase()}
                </span>
                <span className="text-sm text-muted-foreground">
                  {scanResult.exploitable_summary.total_data_mb.toFixed(1)} MB
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* File Browsers */}
      <FileBrowser
        open={datasetBrowser.isOpen}
        onOpenChange={datasetBrowser.closeBrowser}
        onSelect={datasetBrowser.handleSelect}
        title="Sélectionner le Dataset"
        description="Choisissez le dossier contenant les dossiers clients"
        initialPath="/"
      />

      <FileBrowser
        open={sandboxBrowser.isOpen}
        onOpenChange={sandboxBrowser.closeBrowser}
        onSelect={sandboxBrowser.handleSelect}
        title="Sélectionner la Sandbox"
        description="Choisissez le dossier où créer la structure normalisée"
        initialPath="/"
      />
    </div>
  );
}

export default TrainingPage;
