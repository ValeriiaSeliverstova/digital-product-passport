import { useEffect, useState } from 'react'

import { ApiError, apiUrl } from '../services/api.js'
import {
  getPublicPassport,
  submitSupportTicket,
} from '../services/passports.js'
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

function supportEmailUrl(passport) {
  const subject = `Support request: ${passport.model_name} ${passport.serial_number}`
  return `mailto:${passport.support_email}?subject=${encodeURIComponent(subject)}`
}

function supportPhoneUrl(phone) {
  return `tel:${phone.replace(/[^+\d]/g, '')}`
}

function SupportIcon({ type }) {
  const paths = {
    email: (
      <>
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <path d="m3 7 9 6 9-6" />
      </>
    ),
    phone: (
      <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.2-1.2a2 2 0 0 1 2.1-.5c1 .3 1.9.6 2.9.7a2 2 0 0 1 1.7 2Z" />
    ),
    website: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />
      </>
    ),
    ticket: (
      <>
        <path d="M4 4h16v16H4z" />
        <path d="M8 9h8M8 13h5" />
      </>
    ),
  }

  return (
    <svg
      className={styles.supportIcon}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {paths[type]}
    </svg>
  )
}

function PublicPassportPage({ publicId }) {
  const [passport, setPassport] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [reloadKey, setReloadKey] = useState(0)
  const [showTicketForm, setShowTicketForm] = useState(false)
  const [ticketForm, setTicketForm] = useState({
    requester_name: '',
    requester_email: '',
    subject: '',
    message: '',
  })
  const [ticketState, setTicketState] = useState('idle')
  const [ticketError, setTicketError] = useState('')
  const [createdTicket, setCreatedTicket] = useState(null)

  function updateTicketField(field, value) {
    setTicketForm((current) => ({ ...current, [field]: value }))
  }

  async function handleTicketSubmit(event) {
    event.preventDefault()
    setTicketState('submitting')
    setTicketError('')

    try {
      const result = await submitSupportTicket(publicId, ticketForm)
      setCreatedTicket(result)
      setTicketState('success')
    } catch (error) {
      setTicketState('error')
      setTicketError(
        error instanceof ApiError
          ? error.message
          : 'The support ticket could not be submitted. Please try again.',
      )
    }
  }

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
              {passport.model_image_path && (
                <img
                  className={styles.productImage}
                  src={apiUrl(passport.model_image_path)}
                  alt={`${passport.model_name} product model`}
                />
              )}

              <dl className={styles.summary}>
                <div>
                  <dt>Manufacturer</dt>
                  <dd className={styles.manufacturerName}>
                    {passport.manufacturer_logo_path && (
                      <img
                        className={styles.manufacturerLogo}
                        src={apiUrl(passport.manufacturer_logo_path)}
                        alt=""
                      />
                    )}
                    <span>{passport.manufacturer_name}</span>
                  </dd>
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

            {(passport.support_ticket_enabled ||
              passport.support_email ||
              passport.support_phone ||
              passport.support_website) && (
              <section className={styles.detailsCard}>
                <div className={styles.sectionHeading}>
                  <div>
                    <h2>Contact support</h2>
                    <p>
                      Contact {passport.manufacturer_name} for product support
                      or service assistance.
                    </p>
                  </div>
                </div>
                <div className={styles.supportLinks}>
                  {passport.support_email && (
                    <a
                      className={styles.supportLink}
                      href={supportEmailUrl(passport)}
                    >
                      <SupportIcon type="email" />
                      <span className={styles.supportText}>
                        <strong>Email support</strong>
                        <span>{passport.support_email}</span>
                      </span>
                    </a>
                  )}
                  {passport.support_phone && (
                    <a
                      className={styles.supportLink}
                      href={supportPhoneUrl(passport.support_phone)}
                    >
                      <SupportIcon type="phone" />
                      <span className={styles.supportText}>
                        <strong>Call support</strong>
                        <span>{passport.support_phone}</span>
                      </span>
                    </a>
                  )}
                  {passport.support_website && (
                    <a
                      className={styles.supportLink}
                      href={passport.support_website}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <SupportIcon type="website" />
                      <span className={styles.supportText}>
                        <strong>Support website</strong>
                        <span>{passport.support_website}</span>
                      </span>
                    </a>
                  )}
                  {passport.support_ticket_enabled && (
                    <button
                      className={styles.supportLink}
                      type="button"
                      onClick={() => setShowTicketForm((visible) => !visible)}
                      aria-expanded={showTicketForm}
                      aria-controls="support-ticket-form"
                    >
                      <SupportIcon type="ticket" />
                      <span className={styles.supportText}>
                        <strong>Submit a ticket</strong>
                        <span>Send product details with your request</span>
                      </span>
                    </button>
                  )}
                </div>

                {showTicketForm && (
                  <form
                    className={styles.ticketForm}
                    id="support-ticket-form"
                    onSubmit={handleTicketSubmit}
                  >
                    {ticketState === 'success' ? (
                      <div className={styles.ticketSuccess} role="status">
                        <strong>Support ticket #{createdTicket.ticket_id} was submitted.</strong>
                        <span>{passport.manufacturer_name} can now review your request.</span>
                        {createdTicket.ticket_url && (
                          <a
                            href={createdTicket.ticket_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            View ticket in Azure DevOps
                          </a>
                        )}
                      </div>
                    ) : (
                      <>
                        <div className={styles.ticketField}>
                          <label htmlFor="support-requester-name">Your name</label>
                          <input
                            id="support-requester-name"
                            autoComplete="name"
                            maxLength={100}
                            value={ticketForm.requester_name}
                            onChange={(event) =>
                              updateTicketField('requester_name', event.target.value)
                            }
                            required
                          />
                        </div>
                        <div className={styles.ticketField}>
                          <label htmlFor="support-requester-email">Your email</label>
                          <input
                            id="support-requester-email"
                            type="email"
                            autoComplete="email"
                            maxLength={320}
                            value={ticketForm.requester_email}
                            onChange={(event) =>
                              updateTicketField('requester_email', event.target.value)
                            }
                            required
                          />
                        </div>
                        <div className={`${styles.ticketField} ${styles.ticketFullWidth}`}>
                          <label htmlFor="support-subject">Subject</label>
                          <input
                            id="support-subject"
                            maxLength={160}
                            value={ticketForm.subject}
                            onChange={(event) =>
                              updateTicketField('subject', event.target.value)
                            }
                            required
                          />
                        </div>
                        <div className={`${styles.ticketField} ${styles.ticketFullWidth}`}>
                          <label htmlFor="support-message">How can we help?</label>
                          <textarea
                            id="support-message"
                            minLength={10}
                            maxLength={5000}
                            rows={6}
                            value={ticketForm.message}
                            onChange={(event) =>
                              updateTicketField('message', event.target.value)
                            }
                            required
                          />
                        </div>
                        <p className={`${styles.ticketHint} ${styles.ticketFullWidth}`}>
                          The product model, serial number, and passport link will be
                          included automatically.
                        </p>
                        {ticketError && (
                          <p
                            className={`${styles.ticketError} ${styles.ticketFullWidth}`}
                            role="alert"
                          >
                            {ticketError}
                          </p>
                        )}
                        <button
                          className={`${styles.ticketSubmit} ${styles.ticketFullWidth}`}
                          type="submit"
                          disabled={ticketState === 'submitting'}
                        >
                          {ticketState === 'submitting'
                            ? 'Submitting…'
                            : 'Submit support ticket'}
                        </button>
                      </>
                    )}
                  </form>
                )}
              </section>
            )}

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
