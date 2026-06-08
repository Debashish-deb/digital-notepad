/** Bundled biomedical model catalog for UI when Docker gateway is offline. */
export const BIOMEDICAL_SERVICE_LABELS = {
  embeddings: 'Biomedical Embeddings',
  biogpt: 'BioGPT',
  txgemma: 'TxGemma',
  geneformer: 'Geneformer',
  scgpt: 'scGPT',
  scprint: 'scPRINT',
};

export const FALLBACK_BIOMEDICAL_CATALOG = {
  source: 'bundled',
  services: {
    embeddings: {
      port: 8101,
      models: {
        pubmedbert: { task: 'embedding', label: 'PubMedBERT' },
        biobert: { task: 'embedding', label: 'BioBERT' },
        'medcpt-query': { task: 'embedding', label: 'MedCPT Query' },
        'medcpt-article': { task: 'embedding', label: 'MedCPT Article' },
      },
    },
    biogpt: {
      port: 8102,
      models: {
        biogpt: { task: 'text-generation', label: 'BioGPT' },
      },
    },
    txgemma: {
      port: 8103,
      models: {
        'txgemma-2b': { task: 'text-generation', label: 'TxGemma 2B' },
      },
    },
    geneformer: {
      port: 8110,
      models: {
        geneformer: { task: 'single-cell-embedding', label: 'Geneformer' },
      },
    },
    scgpt: {
      port: 8111,
      models: {
        'scgpt-human': { task: 'single-cell-embedding', label: 'scGPT Human' },
      },
    },
    scprint: {
      port: 8112,
      models: {
        scprint: { task: 'single-cell-embedding', label: 'scPRINT' },
      },
    },
  },
};

export function flattenBiomedicalCatalog(catalog = FALLBACK_BIOMEDICAL_CATALOG, status = null) {
  const services = catalog?.services || {};
  const health = status?.services || {};
  const rows = [];

  Object.entries(services).forEach(([serviceId, service]) => {
    const serviceHealth = health[serviceId] || {};
    const healthy = serviceHealth.healthy === true;

    Object.entries(service?.models || {}).forEach(([modelId, model]) => {
      rows.push({
        id: `${serviceId}:${modelId}`,
        serviceId,
        serviceLabel: BIOMEDICAL_SERVICE_LABELS[serviceId] || serviceId,
        modelId,
        label: model.label || modelId,
        task: model.task || 'unknown',
        port: service.port,
        healthy,
        offline: !healthy,
      });
    });
  });

  return rows;
}
