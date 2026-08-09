import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { ApiError } from '../services/api.js'
import {
  getProductModelPage,
  productModelImageUrl,
} from '../services/productModels.js'
import { getCategories } from '../services/templates.js'
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

    async function loadModels() {
      setLoadState('loading')
      try {
        const [modelPage, categoryData] = await Promise.all([
          getProductModelPage(accessToken, {
            search,
            categoryId,
            status,
            page,
            pageSize: 20,
          }),
          getCategories(),
        ])
        if (isCurrentRequest) {
          setModels(modelPage.items)
          setTotal(modelPage.total)
          setTotalPages(modelPage.total_pages)
          setCategories(categoryData)
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
  }, [accessToken, categoryId, onLogout, page, reloadKey, search, status])

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
            {loadState === 'success' && (
              <p className={styles.listCount}>
                {total} {total === 1 ? 'product model' : 'product models'}
              </p>
            )}
          </div>
          <button className={styles.primaryButton} type="button" onClick={onCreate}>
            Create product model
          </button>
        </header>

        {notice && <p className={styles.notice} role="status">{notice}</p>}

        <form
          className={`${styles.listFilters} ${styles.modelListFilters}`}
          onSubmit={applySearch}
        >
          <div className={styles.listSearchField}>
            <label htmlFor="model-search">Model name or code</label>
            <div className={styles.listSearchControl}>
              <input
                id="model-search"
                type="search"
                maxLength="255"
                placeholder="Search product models"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
              <button className={styles.listFilterButton} type="submit">
                Search
              </button>
            </div>
          </div>
          <div className={styles.listFilterField}>
            <label htmlFor="model-category">Category</label>
            <select
              id="model-category"
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
          <div className={styles.listFilterField}>
            <label htmlFor="model-status">Status</label>
            <select
              id="model-status"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value)
                setPage(1)
              }}
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          {hasFilters && (
            <button
              className={styles.listClearButton}
              type="button"
              onClick={clearFilters}
            >
              Clear filters
            </button>
          )}
        </form>

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
        {loadState === 'success' && total === 0 && !hasFilters && (
          <section className={styles.stateCard}>
            <h2>No product models yet</h2>
            <p>Create a model after activating its passport template.</p>
          </section>
        )}
        {loadState === 'success' && total === 0 && hasFilters && (
          <section className={styles.stateCard}>
            <h2>No matching product models</h2>
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
        {loadState === 'success' && models.length > 0 && (
          <>
            <section className={styles.cardGrid} aria-label="Product models">
              {models.map((model) => (
                <article className={styles.card} key={model.id}>
                  {model.has_image && (
                    <img
                      className={styles.modelCardImage}
                      src={productModelImageUrl(model)}
                      alt={`${model.name} product model`}
                    />
                  )}
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
                      <dd>{model.category_name}</dd>
                    </div>
                    <div>
                      <dt>Template</dt>
                      <dd>{model.template_name} · v{model.template_version}</dd>
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
            {totalPages > 1 && (
              <nav className={styles.listPagination} aria-label="Product model pages">
                <button
                  className={styles.listPageButton}
                  type="button"
                  onClick={() => setPage((current) => current - 1)}
                  disabled={page === 1}
                >
                  Previous
                </button>
                <span>Page {page} of {totalPages}</span>
                <button
                  className={styles.listPageButton}
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

export default ProductModelListPage
