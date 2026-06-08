import { useMemo, useState } from 'react';
import { AlertTriangle, Loader2, Table2 } from 'lucide-react';

export default function SpreadsheetPreview({
  sheets = [],
  repairNotes = [],
  loading = false,
  error = null,
  fileUrl = null,
  labels = {},
}) {
  const {
    loading: loadingLabel = 'Loading spreadsheet…',
    repaired = 'Recovered from a damaged or non-standard file:',
    truncated = 'Showing a subset of rows/columns for performance.',
    empty = 'This spreadsheet has no visible cells.',
    failed = 'Could not render spreadsheet tables.',
    openOriginal = 'Open original file',
  } = labels;

  const [activeSheet, setActiveSheet] = useState(0);

  const safeSheets = useMemo(
    () => (Array.isArray(sheets) ? sheets.filter((s) => s.rows?.length) : []),
    [sheets]
  );

  const sheet = safeSheets[activeSheet] || safeSheets[0];
  const colCount = sheet?.rows?.reduce((m, row) => Math.max(m, row.length), 0) || 0;

  if (loading) {
    return (
      <div className="spreadsheet-preview spreadsheet-preview--loading">
        <Loader2 size={18} className="spin-inline" aria-hidden />
        <span>{loadingLabel}</span>
      </div>
    );
  }

  if (error && !safeSheets.length) {
    return (
      <div className="spreadsheet-preview spreadsheet-preview--error">
        <AlertTriangle size={18} aria-hidden />
        <p>{error || failed}</p>
        {repairNotes.length ? (
          <ul className="spreadsheet-preview-repair-notes">
            {repairNotes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        ) : null}
        {fileUrl ? (
          <a href={fileUrl} className="btn btn-secondary btn-sm" target="_blank" rel="noreferrer">
            {openOriginal}
          </a>
        ) : null}
      </div>
    );
  }

  if (!sheet) {
    return <p className="text-footnote muted spreadsheet-preview--empty">{empty}</p>;
  }

  return (
    <div className="spreadsheet-preview">
      {repairNotes.length ? (
        <div className="spreadsheet-preview-banner" role="status">
          <AlertTriangle size={14} aria-hidden />
          <span>
            {repaired} {repairNotes.join(' ')}
          </span>
        </div>
      ) : null}

      {safeSheets.length > 1 ? (
        <div className="spreadsheet-preview-tabs" role="tablist" aria-label="Spreadsheet sheets">
          {safeSheets.map((s, idx) => (
            <button
              key={s.name}
              type="button"
              role="tab"
              aria-selected={idx === activeSheet}
              className={`spreadsheet-preview-tab${idx === activeSheet ? ' active' : ''}`}
              onClick={() => setActiveSheet(idx)}
            >
              <Table2 size={13} aria-hidden />
              {s.name}
            </button>
          ))}
        </div>
      ) : (
        <div className="spreadsheet-preview-sheet-label">
          <Table2 size={14} aria-hidden />
          {sheet.name}
        </div>
      )}

      {sheet.truncated ? (
        <p className="text-caption muted spreadsheet-preview-truncated">{truncated}</p>
      ) : null}

      <div className="spreadsheet-preview-scroll">
        <table className="spreadsheet-preview-table">
          <tbody>
            {sheet.rows.map((row, rowIdx) => (
              <tr key={`r-${rowIdx}`}>
                <th className="spreadsheet-preview-row-head" scope="row">
                  {rowIdx + 1}
                </th>
                {Array.from({ length: colCount }).map((_, colIdx) => (
                  <td key={`c-${colIdx}`}>{row[colIdx] ?? ''}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
