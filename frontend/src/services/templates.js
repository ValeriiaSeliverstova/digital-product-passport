import { apiRequest } from './api.js'

/** Load templates and category names needed by the Template list screen. */
export async function getTemplateListData(accessToken) {
  const [templates, categories] = await Promise.all([
    apiRequest('/api/templates', { token: accessToken }),
    apiRequest('/api/categories'),
  ])

  return { templates, categories }
}
