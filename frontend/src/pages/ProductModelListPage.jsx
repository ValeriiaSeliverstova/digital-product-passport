import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { ApiError } from '../services/api.js'
import { getProductModels } from '../services/productModels.js'
import { getTemplateListData } from '../services/templates.js'
import styles from './ProductManagement.module.css'

function ProductModelListPage({
  accessToken,
  currentUser,
  notice,
  onCreate,
  onEdit,
  onLogout,
  onNavigate,
}) {
  const [models, setModels] = useState([])
  const [categories, setCategories] = useState([])
  const [templates, setTemplates] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let isCurrentRequest = true

    async function loadModels() {
      setLoadState('loading')
      try {
        const [modelData, templateData] = await Promise.all([
          getProductModels(accessToken),
          getTemplateListData(accessToken),
        ])
        if (isCurrentRequest) {
          setModels(modelData)
          setCategories(templateData.categories)
          setTemplates(templateData.templates)
          setLoadState('success')
        }
      } catch (error) {
        if (!isCurrentRequest) return
        if (error instanceof ApiError && error.status === 401) {
          onLogout()
          return
        }
        setLoadState('error')
      }
    }

    loadModels()
    return () => {
      isCurrentRequest = false
    }
  }, [accessToken, onLogout, reloadKey])

  const categoryNames = new Map(
    categories.map((category) => [category.id, category.name]),
  )
  const templateNames = new Map(
    templates.map((template) => [
      template.id,
      `${template.name} · v${template.version}`,
    ]),
  )

  return (
    <div className={styles.page}>
      <AppHeader
        currentSection="product-models"
        currentUser={currentUser}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />
      <main className={styles.main}>
        <header className={styles.pageHeading}>
          <div>
            <h1>Product models</h1>
            <p>Define product types that share one passport template.</p>
          </div>
          <button className={styles.primaryButton} type="button" onClick={onCreate}>
            Create product model
          </button>
        </header>

        {notice && <p className={styles.notice} role="status">{notice}</p>}

        {loadState === 'loading' && (
          <section className={styles.stateCard} aria-live="polite">
            <h2>Loading product models…</h2>
          </section>
        )}
        {loadState === 'error' && (
          <section className={styles.stateCard} role="alert">
            <h2>Product models could not be loaded</h2>
            <button
              className={styles.primaryButton}
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
            >
              Try again
            </button>
          </section>
        )}
        {loadState === 'success' && models.length === 0 && (
          <section className={styles.stateCard}>
            <h2>No product models yet</h2>
            <p>Create a model after activating its passport template.</p>
          </section>
        )}
        {loadState === 'success' && models.length > 0 && (
          <section className={styles.cardGrid} aria-label="Product models">
            {models.map((model) => (
              <article className={styles.card} key={model.id}>
                <div className={styles.cardHeading}>
                  <div>
                    <h2>{model.name}</h2>
                    <span className={styles.code}>{model.model_code}</span>
                  </div>
                  <StatusBadge status={model.status} />
                </div>
                {model.description && <p>{model.description}</p>}
                <dl className={styles.metadata}>
                  <div>
                    <dt>Category</dt>
                    <dd>{categoryNames.get(model.category_id) || 'Unavailable'}</dd>
                  </div>
                  <div>
                    <dt>Template</dt>
                    <dd>{templateNames.get(model.template_id) || 'Unavailable'}</dd>
                  </div>
                </dl>
                <button
                  className={styles.secondaryButton}
                  type="button"
                  onClick={() => onEdit(model.id)}
                >
                  View and edit
                </button>
              </article>
            ))}
          </section>
        )}
      </main>
    </div>
  )
}

export default ProductModelListPage
