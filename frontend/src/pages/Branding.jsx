import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { brandingAPI, reportsAPI } from '../services/api';
import './Branding.css';

function Branding() {
  const [templates, setTemplates] = useState([]);
  const [templateName, setTemplateName] = useState('');

  const [titreDocument, setTitreDocument] = useState('');
  const [societe, setSociete] = useState('');
  const [rue, setRue] = useState('');
  const [numero, setNumero] = useState('');
  const [cp, setCp] = useState('');
  const [ville, setVille] = useState('');
  const [tel, setTel] = useState('');
  const [email, setEmail] = useState('');

  const [logoHeader, setLogoHeader] = useState(null);
  const [logoFooter, setLogoFooter] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const resp = await reportsAPI.listTemplates();
        setTemplates(resp.templates || []);
      } catch (err) {
        console.warn('Branding: impossible de charger la liste des templates', err);
        setTemplates([]);
      }
    })();
  }, []);

  const extractDetailFromAxiosBlobError = async (err) => {
    const data = err?.response?.data;
    const ct = err?.response?.headers?.['content-type'] || err?.response?.headers?.['Content-Type'];

    // Quand axios est en responseType=blob, data est un Blob même si le backend renvoie du JSON.
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

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const fd = new FormData();
      if (templateName) fd.append('template_name', templateName);
      fd.append('titre_document', titreDocument);
      fd.append('societe', societe);
      fd.append('rue', rue);
      fd.append('numero', numero);
      fd.append('cp', cp);
      fd.append('ville', ville);
      fd.append('tel', tel);
      fd.append('email', email);

      if (logoHeader) fd.append('logo_header', logoHeader);
      if (logoFooter) fd.append('logo_footer', logoFooter);

      const { blob, filename } = await brandingAPI.applyBranding(fd);

      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename || 'branding.docx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setSuccessMsg('DOCX généré. Téléchargement lancé.');
    } catch (err) {
      const detail = await extractDetailFromAxiosBlobError(err);
      setError(detail || 'Erreur lors de l\'application du branding');
    } finally {
      setLoading(false);
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
      <div className="flex items-center gap-3">
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
            "inline-flex items-center rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white shadow-sm " +
            "hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 " +
            (disabled ? "opacity-50 cursor-not-allowed hover:bg-slate-900" : "cursor-pointer")
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

  return (
    <div className="branding-page">
      <div className="branding-header">
        <h2>Branding DOCX (entête + pied de page)</h2>
        <p className="branding-subtitle">
          Renseigne les champs et charge tes logos. Le backend génère un nouveau DOCX sans modifier le template original.
        </p>
        <p className="branding-backlink">
          <Link to="/">← Retour</Link>
        </p>
      </div>

      <form className="branding-form" onSubmit={onSubmit}>
        <div className="card">
          <h3>Template de base</h3>
          <div className="grid">
            <div className="field">
              <label>Template DOCX côté serveur</label>
              <select value={templateName} onChange={(e) => setTemplateName(e.target.value)}>
                <option value="">— Par défaut (TEMPLATE_SIMPLE_BASE ou TEMPLATE_PATH) —</option>
                {templates.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <p className="small-note">
                Astuce: tu peux uploader un template via la page Rapports (Parcourir…).
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Champs</h3>
          <div className="grid">
            <div className="field">
              <label>Titre document</label>
              <input value={titreDocument} onChange={(e) => setTitreDocument(e.target.value)} placeholder="TITRE_DOCUMENT" />
            </div>
            <div className="field">
              <label>Société</label>
              <input value={societe} onChange={(e) => setSociete(e.target.value)} placeholder="SOCIETE" />
            </div>
            <div className="field">
              <label>Rue</label>
              <input value={rue} onChange={(e) => setRue(e.target.value)} placeholder="RUE" />
            </div>
            <div className="field">
              <label>Numéro</label>
              <input value={numero} onChange={(e) => setNumero(e.target.value)} placeholder="NUMERO" />
            </div>
            <div className="field">
              <label>CP</label>
              <input value={cp} onChange={(e) => setCp(e.target.value)} placeholder="CP" />
            </div>
            <div className="field">
              <label>Ville</label>
              <input value={ville} onChange={(e) => setVille(e.target.value)} placeholder="VILLE" />
            </div>
            <div className="field">
              <label>Téléphone</label>
              <input value={tel} onChange={(e) => setTel(e.target.value)} placeholder="TEL" />
            </div>
            <div className="field">
              <label>Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="EMAIL" />
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Logos (optionnels)</h3>
          <div className="grid">
            <div className="field">
              <label>Logo entête (PNG/JPG/TIFF)</label>
              <FilePicker
                id="branding-page-logo-header"
                accept="image/png,image/jpeg,image/tiff"
                disabled={loading}
                file={logoHeader}
                onFileSelected={(file) => setLogoHeader(file)}
                buttonLabel="Parcourir…"
                placeholder="Aucun logo sélectionné"
              />
            </div>
            <div className="field">
              <label>Logo pied de page (PNG/JPG/TIFF)</label>
              <FilePicker
                id="branding-page-logo-footer"
                accept="image/png,image/jpeg,image/tiff"
                disabled={loading}
                file={logoFooter}
                onFileSelected={(file) => setLogoFooter(file)}
                buttonLabel="Parcourir…"
                placeholder="Aucun logo sélectionné"
              />
            </div>
          </div>
        </div>

        {error && <div className="alert alert-error">{String(error)}</div>}
        {successMsg && <div className="alert alert-success">{successMsg}</div>}

        <button className="btn" type="submit" disabled={loading}>
          {loading ? 'Génération…' : 'Générer le DOCX'}
        </button>

        <p className="hint">
          Note: le template utilisé côté serveur est <code>uploaded_templates/TEMPLATE_SIMPLE_BASE.docx</code>.
        </p>
      </form>
    </div>
  );
}

export default Branding;
