import { FileText, Loader2, RefreshCw } from 'lucide-react';

export default function ProjectReadmeSetupPanel({
  ensuring = false,
  error = null,
  onCreateReadme,
  workspaceTab = 'overview',
}) {
  const tabHint =
    workspaceTab === 'overview'
      ? 'Overview'
      : `${workspaceTab.charAt(0).toUpperCase()}${workspaceTab.slice(1)}`;

  return (
    <section className="panel workspace-section project-readme-setup">
      <div className="project-readme-setup__icon" aria-hidden="true">
        <FileText size={28} />
      </div>
      <h3 className="text-title-3">No README yet</h3>
      <p className="text-body-secondary">
        Every project needs a <strong>README.md</strong> at the project root — editable like other
        markdown files in the Data Pad. We create a starter template automatically when you open any
        workspace tab.
      </p>
      {ensuring ? (
        <p className="text-footnote muted project-readme-setup__status">
          <Loader2 size={14} className="spin-inline" aria-hidden="true" />
          Creating README.md from {tabHint}…
        </p>
      ) : null}
      {error ? (
        <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>
          {error}
        </p>
      ) : null}
      {!ensuring ? (
        <button type="button" className="btn btn-primary btn-sm" onClick={onCreateReadme}>
          <RefreshCw size={14} aria-hidden="true" />
          Create sample README
        </button>
      ) : null}
    </section>
  );
}
