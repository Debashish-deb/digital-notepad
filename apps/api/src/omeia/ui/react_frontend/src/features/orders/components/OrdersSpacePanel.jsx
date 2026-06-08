/**
 * Shared shell for Orders module pages — matches catalog document browser chrome.
 */
export default function OrdersSpacePanel({
  icon: Icon,
  title,
  description,
  message,
  hint = null,
  children = null,
}) {
  return (
    <section className="panel workspace-section data-pad data-pad--compact data-pad--embedded catalog-space-browser orders-space-panel lab-documents-browser--catalog">
      <div className="lab-docs-catalog-shell orders-space-panel-inner">
        {children || (
          <div className="orders-space-empty">
            {Icon ? (
              <span className="orders-space-empty-icon" aria-hidden>
                <Icon size={26} strokeWidth={1.6} />
              </span>
            ) : null}
            <h3 className="orders-space-empty-title">{title}</h3>
            {description ? <p className="orders-space-empty-lead">{description}</p> : null}
            {message ? <p className="orders-space-empty-message">{message}</p> : null}
            {hint ? <p className="orders-space-empty-hint">{hint}</p> : null}
          </div>
        )}
      </div>
    </section>
  );
}
