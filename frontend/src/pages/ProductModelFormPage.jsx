import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import { ApiError } from '../services/api.js'
import {
  createProductModel,
  getProductModel,
  updateProductModel,
} from '../services/productModels.js'
import { getTemplateListData } from '../services/templates.js'
import styles from './ProductManagement.module.css'

function ProductModelFormPage({
  accessToken,
  currentUser,
  modelId,
  onBack,
  onLogout,
  onNavigate,
  onSaved,
}) {
  const isEditing = Boolean(modelId)
  const [categories, setCategories] = useState([])
  const [templates, setTemplates] = useState([])
  const [categoryId, setCategoryId] = useState('')
  const [templateId, setTemplateId] = useState('')
  const [modelCode, setModelCode] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState('active')
  const [loadState, setLoadState] = useState('loading')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrentRequest = true

    async function loadForm() {
      setLoadState('loading')
      try {
        const [templateData, model] = await Promise.all([
          getTemplateListData(accessToken),
          isEditing ? getProductModel(accessToken, modelId) : null,
        ])
        if (!isCurrentRequest) return

        setCategories(templateData.categories)
        setTemplates(templateData.templates)
        if (model) {
          setCategoryId(model.category_id)
          setTemplateId(model.template_id)
          setModelCode(model.model_code)
          setName(model.name)
          setDescription(model.description || '')
          setStatus(model.status)
        }
        setLoadState('success')
      } catch (loadError) {
        if (!isCurrentRequest) return
        if (loadError instanceof ApiError && loadError.status === 401) {
          onLogout()
          return
        }
        setLoadState('error')
      }
    }

    loadForm()
    return () => {
      isCurrentRequest = false
    }
  }, [accessToken, isEditing, modelId, onLogout])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSaving(true)

    try {
      const savedModel = isEditing
        ? await updateProductModel(accessToken, modelId, {
            name,
            description: description || null,
            status,
          })
        : await createProductModel(accessToken, {
            category_id: categoryId,
            template_id: templateId,
            model_code: modelCode,
            name,
            description: description || null,
          })
      onSaved(savedModel)
    } catch (saveError) {
      if (saveError instanceof ApiError && saveError.status === 401) {
        onLogout()
        return
      }
      setError(
        saveError instanceof ApiError
          ? saveError.message
          : 'The product model could not be saved.',
      )
    } finally {
      setIsSaving(false)
    }
  }

  const activeTemplates = templates.filter(
    (template) =>
      template.status === 'active' && template.category_id === categoryId,
  )
  const categoryName =
    categories.find((category) => category.id === categoryId)?.name ||
    'Unavailable'
  const templateName = (() => {
    const template = templates.find((item) => item.id === templateId)
    return template ? `${template.name} · v${template.version}` : 'Unavailable'
  })()

  return (
    <div className={styles.page}>
      <AppHeader
        currentSection="product-models"
        currentUser={currentUser}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />
      <main className={styles.main}>
        <button className={styles.backButton} type="button" onClick={onBack}>
          ← Back to product models
        </button>
        <header className={styles.pageHeading}>
          <div>
            <h1>{isEditing ? 'Edit product model' : 'Create product model'}</h1>
            <p>General information shared by physical product items.</p>
          </div>
        </header>

        {loadState === 'loading' && (
          <section className={styles.stateCard}><h2>Loading form…</h2></section>
        )}
        {loadState === 'error' && (
          <section className={styles.stateCard} role="alert">
            <h2>Product model form could not be loaded</h2>
          </section>
        )}
        {loadState === 'success' && (
          <section className={styles.formCard}>
            <form className={styles.form} onSubmit={handleSubmit}>
              {isEditing ? (
                <div className={styles.fieldGrid}>
                  <div className={styles.field}>
                    <span className={styles.readonlyLabel}>Model code</span>
                    <p className={`${styles.readonlyValue} ${styles.code}`}>
                      {modelCode}
                    </p>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.readonlyLabel}>Category</span>
                    <p className={styles.readonlyValue}>{categoryName}</p>
                  </div>
                  <div className={styles.field}>
                    <span className={styles.readonlyLabel}>Template</span>
                    <p className={styles.readonlyValue}>{templateName}</p>
                  </div>
                </div>
              ) : (
                <div className={styles.fieldGrid}>
                  <div className={styles.field}>
                    <label htmlFor="model-category">Product category</label>
                    <select
                      id="model-category"
                      value={categoryId}
                      onChange={(event) => {
                        setCategoryId(event.target.value)
                        setTemplateId('')
                      }}
                      required
                    >
                      <option value="">Select a category</option>
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className={styles.field}>
                    <label htmlFor="model-template">Active template</label>
                    <select
                      id="model-template"
                      value={templateId}
                      onChange={(event) => setTemplateId(event.target.value)}
                      disabled={!categoryId}
                      required
                    >
                      <option value="">Select a template</option>
                      {activeTemplates.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.name} · v{template.version}
                        </option>
                      ))}
                    </select>
                    {categoryId && activeTemplates.length === 0 && (
                      <p className={styles.helperText}>
                        Activate a template for this category first.
                      </p>
                    )}
                  </div>
                  <div className={styles.field}>
                    <label htmlFor="model-code">Model code</label>
                    <input
                      id="model-code"
                      maxLength="100"
                      value={modelCode}
                      onChange={(event) => setModelCode(event.target.value)}
                      required
                    />
                  </div>
                </div>
              )}

              <div className={styles.field}>
                <label htmlFor="model-name">Model name</label>
                <input
                  id="model-name"
                  maxLength="255"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  required
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="model-description">Description (optional)</label>
                <textarea
                  id="model-description"
                  maxLength="2000"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </div>
              {isEditing && (
                <div className={styles.field}>
                  <label htmlFor="model-status">Status</label>
                  <select
                    id="model-status"
                    value={status}
                    onChange={(event) => setStatus(event.target.value)}
                  >
                    <option value="active">Active</option>
                    <option value="archived">Archived</option>
                  </select>
                </div>
              )}

              {error && <p className={styles.error} role="alert">{error}</p>}
              <div className={styles.actions}>
                <button
                  className={styles.secondaryButton}
                  type="button"
                  onClick={onBack}
                  disabled={isSaving}
                >
                  Cancel
                </button>
                <button
                  className={styles.primaryButton}
                  type="submit"
                  disabled={isSaving}
                >
                  {isSaving ? 'Saving…' : isEditing ? 'Save changes' : 'Create model'}
                </button>
              </div>
            </form>
          </section>
        )}
      </main>
    </div>
  )
}

export default ProductModelFormPage
