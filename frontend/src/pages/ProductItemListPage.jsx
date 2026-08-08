import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { ApiError } from '../services/api.js'
import { getProductItems } from '../services/productItems.js'
import { getProductModels } from '../services/productModels.js'
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
  const [models, setModels] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let isCurrentRequest = true

    async function loadItems() {
      setLoadState('loading')
      try {
        const [itemData, modelData] = await Promise.all([
          getProductItems(accessToken),
          getProductModels(accessToken),
        ])
        if (isCurrentRequest) {
          setItems(itemData)
          setModels(modelData)
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
  }, [accessToken, onLogout, reloadKey])

  const modelNames = new Map(models.map((model) => [model.id, model.name]))

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
          </div>
          <button className={styles.primaryButton} type="button" onClick={onCreate}>
            Create product item
          </button>
        </header>

        {notice && <p className={styles.notice} role="status">{notice}</p>}
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
        {loadState === 'success' && items.length === 0 && (
          <section className={styles.stateCard}>
            <h2>No product items yet</h2>
            <p>Create an item from an active product model.</p>
          </section>
        )}
        {loadState === 'success' && items.length > 0 && (
          <section className={styles.cardGrid} aria-label="Product items">
            {items.map((item) => (
              <article className={styles.card} key={item.id}>
                <div className={styles.cardHeading}>
                  <div>
                    <h2>{modelNames.get(item.model_id) || 'Product item'}</h2>
                    <span className={styles.code}>{item.serial_number}</span>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
                <dl className={styles.metadata}>
                  <div>
                    <dt>Manufactured</dt>
                    <dd>
                      {item.manufacture_date
                        ? dateFormatter.format(
                            new Date(`${item.manufacture_date}T00:00:00`),
                          )
                        : 'Not provided'}
                    </dd>
                  </div>
                  <div>
                    <dt>Public ID</dt>
                    <dd className={styles.code}>{item.public_id}</dd>
                  </div>
                </dl>
                <button
                  className={styles.secondaryButton}
                  type="button"
                  onClick={() => onEdit(item.id)}
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

export default ProductItemListPage
