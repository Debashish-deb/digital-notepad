/**
 * Build a PDF embed URL with Chrome/Acrobat open parameters.
 * navpanes=0 hides the thumbnail/bookmark sidebar so the document uses full iframe width.
 */
export function pdfEmbedUrl(url, options = {}) {
  const { navpanes = false, view = 'FitH', toolbar = true } = options;
  if (!url || typeof url !== 'string') return url;
  const base = url.split('#')[0];
  const params = new URLSearchParams();
  params.set('navpanes', navpanes ? '1' : '0');
  if (view) params.set('view', view);
  params.set('toolbar', toolbar ? '1' : '0');
  return `${base}#${params.toString()}`;
}
