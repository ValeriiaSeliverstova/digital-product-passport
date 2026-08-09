import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { ApiError } from '../services/api.js'
import { getTemplateFamilyListData } from '../services/templates.js'
import styles from './TemplateListPage.module.css'

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
})

function TemplateListPage({
  accessToken,
  currentUser,
  notice,
  onCreateTemplate,
  onEditTemplate,
  onLogout,
  onNavigate,
}) {
  const [templateFamilies, setTemplateFamilies] = useState([])
  const [categories, setCategories] = useState([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [status, setStatus] = useState('')
  const [loadState, setLoadState] = useState('loading')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let isCurrentRequest = true

    async function loadTemplates() {
      setLoadState('loading')

      try {
        const data = await getTemplateFamilyListData(accessToken, {
          search,
          categoryId,
          status,
          page,
          pageSize: 20,
        })
        if (isCurrentRequest) {
          setTemplateFamilies(data.templatePage.items)
          setCategories(data.categories)
          setTotal(data.templatePage.total)
          setTotalPages(data.templatePage.total_pages)
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
  }, [accessToken, categoryId, onLogout, page, reloadKey, search, status])

  const categoryNames = new Map(
    categories.map((category) => [category.id, category.name]),
  )
  const hasFilters = Boolean(search || categoryId || status)

  function applySearch(event) {
    event.preventDefault()
    setPage(1)
    setSearch(searchInput.trim())
  }

  function clearFilters() {
    setSearchInput('')
    setSearch('')
    setCategoryId('')
    setStatus('')
    setPage(1)
  }

  return (
    <div className={styles.page}>
      <AppHeader
        currentSection="templates"
        currentUser={currentUser}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />

      <main className={styles.main}>
        <div className={styles.pageHeading}>
          <div>
            <h1>Templates</h1>
            {loadState === 'success' && (
              <p className={styles.count}>
                {total} {total === 1 ? 'template' : 'templates'}
              </p>
            )}
          </div>
          <button
            className={styles.primaryButton}
            type="button"
            onClick={onCreateTemplate}
          >
            Create template
          </button>
        </div>

        {notice && (
          <p className={styles.notice} role="status">
            {notice}
          </p>
        )}

        <form className={styles.filters} onSubmit={applySearch}>
          <div className={styles.searchField}>
            <label htmlFor="template-search">Template name</label>
            <div className={styles.searchControl}>
              <input
                id="template-search"
                type="search"
                maxLength="255"
                placeholder="Search by name"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
              <button className={styles.filterButton} type="submit">
                Search
              </button>
            </div>
          </div>
          <div className={styles.filterField}>
            <label htmlFor="template-category">Category</label>
            <select
              id="template-category"
              value={categoryId}
              onChange={(event) => {
                setCategoryId(event.target.value)
                setPage(1)
              }}
            >
              <option value="">All categories</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
          <div className={styles.filterField}>
            <label htmlFor="template-status">Status</label>
            <select
              id="template-status"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value)
                setPage(1)
              }}
            >
              <option value="">All statuses</option>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          {hasFilters && (
            <button
              className={styles.clearButton}
              type="button"
              onClick={clearFilters}
            >
              Clear filters
            </button>
          )}
        </form>

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

        {loadState === 'success' && total === 0 && !hasFilters && (
          <section className={styles.stateCard}>
            <h2>No templates yet</h2>
            <p>Create a draft to define your first passport structure.</p>
            <button
              className={styles.primaryButton}
              type="button"
              onClick={onCreateTemplate}
            >
              Create your first template
            </button>
          </section>
        )}

        {loadState === 'success' && total === 0 && hasFilters && (
          <section className={styles.stateCard}>
            <h2>No matching templates</h2>
            <p>Try changing or clearing the current filters.</p>
            <button
              className={styles.primaryButton}
              type="button"
              onClick={clearFilters}
            >
              Clear filters
            </button>
          </section>
        )}

        {loadState === 'success' && templateFamilies.length > 0 && (
          <>
          <section className={styles.templateGrid} aria-label="Passport templates">
            {templateFamilies.map((template) => (
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
                    <dt>Versions</dt>
                    <dd>
                      {template.version_count} · Latest v{template.version}
                    </dd>
                  </div>
                  <div>
                    <dt>Created</dt>
                    <dd>{dateFormatter.format(new Date(template.created_at))}</dd>
                  </div>
                </dl>
                <button
                  className={styles.editButton}
                  type="button"
                  onClick={() => onEditTemplate(template.id)}
                >
                  {template.status === 'draft' ? 'Edit template' : 'View template'}
                </button>
              </article>
            ))}
          </section>
          {totalPages > 1 && (
            <nav className={styles.pagination} aria-label="Template pages">
              <button
                className={styles.pageButton}
                type="button"
                onClick={() => setPage((current) => current - 1)}
                disabled={page === 1}
              >
                Previous
              </button>
              <span>Page {page} of {totalPages}</span>
              <button
                className={styles.pageButton}
                type="button"
                onClick={() => setPage((current) => current + 1)}
                disabled={page === totalPages}
              >
                Next
              </button>
            </nav>
          )}
          </>
        )}
      </main>
    </div>
  )
}

export default TemplateListPage
