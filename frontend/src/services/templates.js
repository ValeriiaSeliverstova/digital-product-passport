import { apiRequest } from './api.js'

/** Load active product categories for template forms and readable list labels. */
export function getCategories() {
  return apiRequest('/api/categories')
}

/** Load templates and category names needed by the Template list screen. */
export async function getTemplateListData(accessToken) {
  const [templates, categories] = await Promise.all([
    apiRequest('/api/templates', { token: accessToken }),
    getCategories(),
  ])

  return { templates, categories }
}

/** Load one filtered page of template families for the list screen. */
export async function getTemplateFamilyListData(accessToken, filters) {
  const query = new URLSearchParams({
    page: String(filters.page),
    page_size: String(filters.pageSize),
  })
  if (filters.search) query.set('search', filters.search)
  if (filters.categoryId) query.set('category_id', filters.categoryId)
  if (filters.status) query.set('status', filters.status)

  const [templatePage, categories] = await Promise.all([
    apiRequest(`/api/templates/families?${query}`, { token: accessToken }),
    getCategories(),
  ])
  return { templatePage, categories }
}

/** Create a new draft template owned by the authenticated organization. */
export function createTemplate(accessToken, templateData) {
  return apiRequest('/api/templates', {
    method: 'POST',
    token: accessToken,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(templateData),
  })
}

/** Load one owned template together with its ordered field definitions. */
export function getTemplate(accessToken, templateId) {
  return apiRequest(`/api/templates/${templateId}`, { token: accessToken })
}

/** Update the shared family name or this version's lifecycle status. */
export function updateTemplate(accessToken, templateId, templateData) {
  return apiRequest(`/api/templates/${templateId}`, {
    method: 'PUT',
    token: accessToken,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(templateData),
  })
}

/** Copy a completed template and its fields into the next editable version. */
export function createTemplateVersion(accessToken, templateId) {
  return apiRequest(`/api/templates/${templateId}/versions`, {
    method: 'POST',
    token: accessToken,
  })
}

/** Add one field using the backend's batch endpoint. */
export async function createTemplateField(accessToken, templateId, fieldData) {
  const fields = await apiRequest(`/api/templates/${templateId}/fields`, {
    method: 'POST',
    token: accessToken,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify([fieldData]),
  })

  return fields[0]
}

/** Replace the complete definition of an existing template field. */
export function updateTemplateField(
  accessToken,
  templateId,
  fieldId,
  fieldData,
) {
  return apiRequest(`/api/templates/${templateId}/fields/${fieldId}`, {
    method: 'PUT',
    token: accessToken,
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(fieldData),
  })
}

/** Permanently remove one field from a draft template. */
export function deleteTemplateField(accessToken, templateId, fieldId) {
  return apiRequest(`/api/templates/${templateId}/fields/${fieldId}`, {
    method: 'DELETE',
    token: accessToken,
  })
}
