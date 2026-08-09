import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { ApiError } from '../services/api.js'
import { getProductItems } from '../services/productItems.js'
import styles from './ProductManagement.module.css'

const dateFormatter = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' })

function ProductItemListPage({
  accessToken,
  currentUser,
  notice,
  onCreate,
  onEdit,
  onLogout,
  onNavigate,
}) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [page, setPage] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [manufacturedFrom, setManufacturedFrom] = useState('')
  const [manufacturedTo, setManufacturedTo] = useState('')
  const [loadState, setLoadState] = useState('loading')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let isCurrentRequest = true

    async function loadItems() {
      setLoadState('loading')
      try {
        const itemData = await getProductItems(accessToken, {
          search,
          status,
          manufacturedFrom,
          manufacturedTo,
          page,
          pageSize: 20,
        })
        if (isCurrentRequest) {
          setItems(itemData.items)
          setTotal(itemData.total)
          setTotalPages(itemData.total_pages)
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

    loadItems()
    return () => {
      isCurrentRequest = false
    }
  }, [
    accessToken,
    manufacturedFrom,
    manufacturedTo,
    onLogout,
    page,
    reloadKey,
    search,
    status,
  ])

  const hasFilters = Boolean(
    search || status || manufacturedFrom || manufacturedTo,
  )

  function applySearch(event) {
    event.preventDefault()
    setPage(1)
    setSearch(searchInput.trim())
  }

  function clearFilters() {
    setSearchInput('')
    setSearch('')
    setStatus('')
    setManufacturedFrom('')
    setManufacturedTo('')
    setPage(1)
  }

  return (
    <div className={styles.page}>
      <AppHeader
        currentSection="product-items"
        currentUser={currentUser}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />
      <main className={styles.main}>
        <header className={styles.pageHeading}>
          <div>
            <h1>Product items</h1>
            <p>Register and publish passports for physical products.</p>
            {loadState === 'success' && (
              <p className={styles.listCount}>
                {total} {total === 1 ? 'product item' : 'product items'}
              </p>
            )}
          </div>
          <button className={styles.primaryButton} type="button" onClick={onCreate}>
            Create product item
          </button>
        </header>

        {notice && <p className={styles.notice} role="status">{notice}</p>}
        <form className={styles.listFilters} onSubmit={applySearch}>
          <div className={styles.listSearchField}>
            <label htmlFor="item-search">Serial, model, or public ID</label>
            <div className={styles.listSearchControl}>
              <input
                id="item-search"
                type="search"
                maxLength="255"
                placeholder="Search product items"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
              <button className={styles.listFilterButton} type="submit">
                Search
              </button>
            </div>
          </div>
          <div className={styles.listFilterField}>
            <label htmlFor="item-status">Status</label>
            <select
              id="item-status"
              value={status}
              onChange={(event) => {
                setStatus(event.target.value)
                setPage(1)
              }}
            >
              <option value="">All statuses</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="retired">Retired</option>
            </select>
          </div>
          <div className={styles.listFilterField}>
            <label htmlFor="manufactured-from">Manufactured from</label>
            <input
              id="manufactured-from"
              type="date"
              value={manufacturedFrom}
              max={manufacturedTo || undefined}
              onChange={(event) => {
                setManufacturedFrom(event.target.value)
                setPage(1)
              }}
            />
          </div>
          <div className={styles.listFilterField}>
            <label htmlFor="manufactured-to">Manufactured to</label>
            <input
              id="manufactured-to"
              type="date"
              value={manufacturedTo}
              min={manufacturedFrom || undefined}
              onChange={(event) => {
                setManufacturedTo(event.target.value)
                setPage(1)
              }}
            />
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
            <h2>Loading product items…</h2>
          </section>
        )}
        {loadState === 'error' && (
          <section className={styles.stateCard} role="alert">
            <h2>Product items could not be loaded</h2>
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
            <h2>No product items yet</h2>
            <p>Create an item from an active product model.</p>
          </section>
        )}
        {loadState === 'success' && total === 0 && hasFilters && (
          <section className={styles.stateCard}>
            <h2>No matching product items</h2>
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
        {loadState === 'success' && items.length > 0 && (
          <>
            <div className={styles.itemTableWrapper}>
              <table className={styles.itemTable}>
                <thead>
                  <tr>
                    <th scope="col">Model</th>
                    <th scope="col">Serial number</th>
                    <th scope="col">Status</th>
                    <th scope="col">Manufactured</th>
                    <th scope="col">Public ID</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td className={styles.itemModelName}>{item.model_name}</td>
                      <td className={styles.code}>{item.serial_number}</td>
                      <td><StatusBadge status={item.status} /></td>
                      <td>
                        {item.manufacture_date
                          ? dateFormatter.format(
                              new Date(`${item.manufacture_date}T00:00:00`),
                            )
                          : 'Not provided'}
                      </td>
                      <td className={`${styles.code} ${styles.publicIdCell}`}>
                        {item.public_id}
                      </td>
                      <td>
                        <button
                          className={styles.tableActionButton}
                          type="button"
                          onClick={() => onEdit(item.id)}
                        >
                          View and edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <nav className={styles.listPagination} aria-label="Product item pages">
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

export default ProductItemListPage
