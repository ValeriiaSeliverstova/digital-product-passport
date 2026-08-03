import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { ApiError } from '../services/api.js'
import { getTemplateListData } from '../services/templates.js'
import styles from './TemplateListPage.module.css'

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
})

function TemplateListPage({ accessToken, currentUser, onLogout }) {
  const [templates, setTemplates] = useState([])
  const [categories, setCategories] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let isCurrentRequest = true

    async function loadTemplates() {
      setLoadState('loading')

      try {
        const data = await getTemplateListData(accessToken)
        if (isCurrentRequest) {
          setTemplates(data.templates)
          setCategories(data.categories)
          setLoadState('success')
        }
      } catch (error) {
        if (!isCurrentRequest) {
          return
        }

        if (error instanceof ApiError && error.status === 401) {
          onLogout()
          return
        }

        setLoadState('error')
      }
    }

    loadTemplates()

    return () => {
      isCurrentRequest = false
    }
  }, [accessToken, onLogout, reloadKey])

  const categoryNames = new Map(
    categories.map((category) => [category.id, category.name]),
  )

  return (
    <div className={styles.page}>
      <AppHeader currentUser={currentUser} onLogout={onLogout} />

      <main className={styles.main}>
        <div className={styles.pageHeading}>
          <div>
            <h1>Templates</h1>
            {loadState === 'success' && (
              <p className={styles.count}>
                {templates.length}{' '}
                {templates.length === 1 ? 'template' : 'templates'}
              </p>
            )}
          </div>
        </div>

        {loadState === 'loading' && (
          <section className={styles.stateCard} aria-live="polite">
            <h2>Loading templates…</h2>
            <p>Please wait while your organization's templates are loaded.</p>
          </section>
        )}

        {loadState === 'error' && (
          <section className={styles.stateCard} role="alert">
            <h2>Templates could not be loaded</h2>
            <p>Check your connection and try again.</p>
            <button
              className={styles.primaryButton}
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
            >
              Try again
            </button>
          </section>
        )}

        {loadState === 'success' && templates.length === 0 && (
          <section className={styles.stateCard}>
            <h2>No templates yet</h2>
            <p>Template creation will be available in the next step.</p>
          </section>
        )}

        {loadState === 'success' && templates.length > 0 && (
          <section className={styles.templateGrid} aria-label="Passport templates">
            {templates.map((template) => (
              <article className={styles.templateCard} key={template.id}>
                <div className={styles.cardHeading}>
                  <h2>{template.name}</h2>
                  <StatusBadge status={template.status} />
                </div>

                <dl className={styles.metadata}>
                  <div>
                    <dt>Category</dt>
                    <dd>
                      {categoryNames.get(template.category_id) ||
                        'Category unavailable'}
                    </dd>
                  </div>
                  <div>
                    <dt>Version</dt>
                    <dd>{template.version}</dd>
                  </div>
                  <div>
                    <dt>Created</dt>
                    <dd>{dateFormatter.format(new Date(template.created_at))}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </section>
        )}
      </main>
    </div>
  )
}

export default TemplateListPage
