import { apiFetch } from '@/services/client.js';

export async function fetchLearningStatus() {
  return apiFetch('/api/learning/status');
}

export async function sendLearningFeedback({
  response_id,
  feedback_type,
  rating = null,
  comment = '',
} = {}) {
  return apiFetch('/api/learning/feedback', {
    method: 'POST',
    body: {
      response_id,
      feedback_type,
      rating,
      comment,
    },
  });
}

export async function saveToKnowledgeBase({ response_id, comment = '' } = {}) {
  return sendLearningFeedback({
    response_id,
    feedback_type: 'save_to_knowledge_base',
    comment,
  });
}
