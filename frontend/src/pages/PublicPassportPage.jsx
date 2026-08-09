import { useEffect, useState } from 'react'

import { ApiError } from '../services/api.js'
import { getPublicPassport } from '../services/passports.js'
import styles from './PublicPassportPage.module.css'

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'long',
})

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'long',
  timeStyle: 'short',
})

const numberFormatter = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 10,
})

function formatDate(value) {
  if (!value) {
    return 'Not provided'
  }

  // Adding a local time prevents YYYY-MM-DD values shifting by one day.
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date)
}

function formatFieldValue(field) {
  if (field.data_type === 'boolean') {
    return field.value ? 'Yes' : 'No'
  }

  if (field.data_type === 'date') {
    return formatDate(field.value)
  }

  if (['integer', 'decimal'].includes(field.data_type)) {
    return numberFormatter.format(field.value)
  }

  return String(field.value)
}

function formatEventDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : dateTimeFormatter.format(date)
}

function formatEventType(value) {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function PublicPassportPage({ publicId }) {
  const [passport, setPassport] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let isCurrentRequest = true

    async function loadPassport() {
      setLoadState('loading')

      try {
        const result = await getPublicPassport(publicId)
        if (isCurrentRequest) {
          setPassport(result)
          setLoadState('success')
        }
      } catch (error) {
        if (!isCurrentRequest) {
          return
        }

        if (error instanceof ApiError && [404, 422].includes(error.status)) {
          setLoadState('not-found')
        } else {
          setLoadState('error')
        }
      }
    }

    loadPassport()

    return () => {
      isCurrentRequest = false
    }
  }, [publicId, reloadKey])

  return (
    <div className={styles.page}>
      <a className={styles.skipLink} href="#passport-content">
        Skip to passport content
      </a>

      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">
            DPP
          </span>
          <span>Digital Product Passport</span>
        </div>
      </header>

      <main className={styles.main} id="passport-content">
        {loadState === 'loading' && (
          <section className={styles.stateCard} aria-live="polite">
            <h1>Loading product passport…</h1>
            <p>Please wait while the published product data is loaded.</p>
          </section>
        )}

        {loadState === 'not-found' && (
          <section className={styles.stateCard}>
            <h1>Passport not found</h1>
            <p>
              This passport does not exist or is not currently published.
              Check that the scanned link is complete.
            </p>
          </section>
        )}

        {loadState === 'error' && (
          <section className={styles.stateCard} role="alert">
            <h1>Passport could not be loaded</h1>
            <p>Check your connection and try again.</p>
            <button
              className={styles.retryButton}
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
            >
              Try again
            </button>
          </section>
        )}

        {loadState === 'success' && passport && (
          <>
            <section className={styles.identityCard}>
              <p className={styles.status}>Published passport</p>
              <p className={styles.category}>{passport.category_name}</p>
              <h1>{passport.model_name}</h1>
              {passport.model_description && (
                <p className={styles.description}>
                  {passport.model_description}
                </p>
              )}

              <dl className={styles.summary}>
                <div>
                  <dt>Manufacturer</dt>
                  <dd>{passport.manufacturer_name}</dd>
                </div>
                <div>
                  <dt>Model code</dt>
                  <dd className={styles.code}>{passport.model_code}</dd>
                </div>
                <div>
                  <dt>Serial number</dt>
                  <dd className={styles.code}>{passport.serial_number}</dd>
                </div>
                <div>
                  <dt>Manufactured</dt>
                  <dd>{formatDate(passport.manufacture_date)}</dd>
                </div>
              </dl>
            </section>

            <section className={styles.detailsCard}>
              <div className={styles.sectionHeading}>
                <div>
                  <h2>Product information</h2>
                  <p>Public data defined by the product passport template.</p>
                </div>
                <span className={styles.templateVersion}>
                  {passport.template_name} · v{passport.template_version}
                </span>
              </div>

              {passport.fields.length > 0 ? (
                <dl className={styles.fieldList}>
                  {passport.fields.map((field) => (
                    <div className={styles.field} key={field.code}>
                      <dt>{field.label}</dt>
                      <dd>{formatFieldValue(field)}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className={styles.emptyFields}>
                  No additional public product information is available.
                </p>
              )}
            </section>

            <section className={styles.detailsCard}>
              <div className={styles.sectionHeading}>
                <div>
                  <h2>Product history</h2>
                  <p>Public maintenance and lifecycle information.</p>
                </div>
              </div>

              {passport.lifecycle_events.length > 0 ? (
                <ol className={styles.timeline}>
                  {passport.lifecycle_events.map((event) => (
                    <li className={styles.timelineEvent} key={event.id}>
                      <div className={styles.eventHeading}>
                        <h3>{formatEventType(event.event_type)}</h3>
                        <time dateTime={event.occurred_at}>
                          {formatEventDate(event.occurred_at)}
                        </time>
                      </div>
                      {event.description && <p>{event.description}</p>}
                      {event.service_provider && (
                        <p className={styles.serviceProvider}>
                          Service provider: {event.service_provider}
                        </p>
                      )}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className={styles.emptyFields}>
                  No public lifecycle events are available yet.
                </p>
              )}
            </section>

            <p className={styles.publicId}>
              Public passport ID: <span>{passport.public_id}</span>
            </p>
          </>
        )}
      </main>

      <footer className={styles.footer}>
        Product information provided by the manufacturer.
      </footer>
    </div>
  )
}

export default PublicPassportPage
