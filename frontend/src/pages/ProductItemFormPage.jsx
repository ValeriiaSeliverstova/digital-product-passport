import { useEffect, useState } from 'react'

import AiDocumentUpload from '../components/AiDocumentUpload.jsx'
import AppHeader from '../components/AppHeader.jsx'
import NfcWriter from '../components/NfcWriter.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { ApiError } from '../services/api.js'
import {
  createLifecycleEvent,
  createProductItem,
  getLifecycleEvents,
  getProductItem,
  getProductItemQrCode,
  updateProductItem,
} from '../services/productItems.js'
import {
  getProductModel,
  getProductModels,
} from '../services/productModels.js'
import { getTemplate, getTemplateListData } from '../services/templates.js'
import styles from './ProductManagement.module.css'

const eventTypes = [
  'manufacturing',
  'installation',
  'inspection',
  'maintenance',
  'repair',
  'certification',
  'retirement',
]

const eventDateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function defaultEventTime() {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
}

function eventLabel(value) {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function convertFieldValue(field, value) {
  if (value === '') return undefined
  if (field.data_type === 'integer') return Number.parseInt(value, 10)
  if (field.data_type === 'decimal') return Number(value)
  if (field.data_type === 'boolean') return value === 'true'
  return value
}

function inputValue(field, value) {
  if (value === undefined || value === null) return ''
  if (field.data_type === 'boolean') return String(value)
  return value
}

function PassportFieldControl({ field, value, disabled, onChange }) {
  const rules = field.validation_rules || {}
  const controlProps = {
    id: `passport-${field.code}`,
    disabled,
    value: inputValue(field, value),
    onChange: (event) => onChange(convertFieldValue(field, event.target.value)),
  }

  let control
  if (field.data_type === 'boolean') {
    control = (
      <select {...controlProps}>
        <option value="">Not provided</option>
        <option value="true">Yes</option>
        <option value="false">No</option>
      </select>
    )
  } else if (field.data_type === 'date') {
    control = <input {...controlProps} type="date" min={rules.min} max={rules.max} />
  } else if (['integer', 'decimal'].includes(field.data_type)) {
    control = (
      <input
        {...controlProps}
        type="number"
        step={field.data_type === 'integer' ? '1' : 'any'}
        min={rules.min}
        max={rules.max}
      />
    )
  } else if (rules.allowed_values) {
    control = (
      <select {...controlProps}>
        <option value="">Not provided</option>
        {rules.allowed_values.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    )
  } else {
    control = (
      <input
        {...controlProps}
        type="text"
        minLength={rules.min_length}
        maxLength={rules.max_length || 10000}
      />
    )
  }

  return (
    <div className={styles.passportField}>
      <label htmlFor={`passport-${field.code}`}>{field.label}</label>
      {control}
      <p className={styles.fieldFlags}>
        {field.is_required ? 'Required to publish' : 'Optional'} ·{' '}
        {field.access_level === 'public' ? 'Public' : 'Manufacturer only'}
      </p>
    </div>
  )
}

function ProductItemFormPage({
  accessToken,
  currentUser,
  initialNotice = '',
  itemId,
  onBack,
  onCreated,
  onLogout,
  onNavigate,
}) {
  const isEditing = Boolean(itemId)
  const isOrganizationAdmin = currentUser.role.name === 'manufacturer_user'
  const [item, setItem] = useState(null)
  const [models, setModels] = useState([])
  const [selectedModelId, setSelectedModelId] = useState('')
  const [template, setTemplate] = useState(null)
  const [serialNumber, setSerialNumber] = useState('')
  const [manufactureDate, setManufactureDate] = useState('')
  const [passportData, setPassportData] = useState({})
  const [loadState, setLoadState] = useState('loading')
  const [isSaving, setIsSaving] = useState(false)
  const [qrCodeUrl, setQrCodeUrl] = useState('')
  const [isGeneratingQrCode, setIsGeneratingQrCode] = useState(false)
  const [notice, setNotice] = useState(initialNotice)
  const [error, setError] = useState('')
  const [lifecycleEvents, setLifecycleEvents] = useState([])
  const [eventType, setEventType] = useState('maintenance')
  const [eventTime, setEventTime] = useState(defaultEventTime)
  const [eventDescription, setEventDescription] = useState('')
  const [eventProvider, setEventProvider] = useState('')
  const [eventAccessLevel, setEventAccessLevel] = useState('public')
  const [isSavingEvent, setIsSavingEvent] = useState(false)
  const [isRetirementConfirmationOpen, setIsRetirementConfirmationOpen] = useState(false)

  useEffect(() => {
    let isCurrentRequest = true

    async function loadForm() {
      setLoadState('loading')
      try {
        if (isEditing) {
          const itemData = await getProductItem(accessToken, itemId)
          const model = await getProductModel(accessToken, itemData.model_id)
          const templateData = await getTemplate(accessToken, model.template_id)
          if (!isCurrentRequest) return
          setItem(itemData)
          setModels([model])
          setSelectedModelId(model.id)
          setTemplate(templateData)
          setSerialNumber(itemData.serial_number)
          setManufactureDate(itemData.manufacture_date || '')
          setPassportData(itemData.passport_data)
          if (itemData.status !== 'draft') {
            setLifecycleEvents(await getLifecycleEvents(accessToken, itemId))
          }
        } else {
          const [modelData, templateData] = await Promise.all([
            getProductModels(accessToken),
            getTemplateListData(accessToken),
          ])
          if (!isCurrentRequest) return
          const activeTemplateIds = new Set(
            templateData.templates
              .filter((templateItem) => templateItem.status === 'active')
              .map((templateItem) => templateItem.id),
          )
          setModels(
            modelData.filter(
              (model) =>
                model.status === 'active' &&
                activeTemplateIds.has(model.template_id),
            ),
          )
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
  }, [accessToken, isEditing, itemId, onLogout])

  useEffect(
    () => () => {
      if (qrCodeUrl) URL.revokeObjectURL(qrCodeUrl)
    },
    [qrCodeUrl],
  )

  async function handleModelChange(modelId) {
    setSelectedModelId(modelId)
    setTemplate(null)
    setPassportData({})
    setError('')
    if (!modelId) return

    const model = models.find((candidate) => candidate.id === modelId)
    try {
      setTemplate(await getTemplate(accessToken, model.template_id))
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 401) {
        onLogout()
        return
      }
      setError('The selected model template could not be loaded.')
    }
  }

  function updatePassportValue(field, value) {
    setPassportData((current) => {
      const next = { ...current }
      if (value === undefined) delete next[field.code]
      else next[field.code] = value
      return next
    })
  }

  function applyAiSuggestions(suggestions) {
    if (suggestions.serialNumber !== undefined) {
      setSerialNumber(String(suggestions.serialNumber))
    }
    if (suggestions.manufactureDate !== undefined) {
      setManufactureDate(String(suggestions.manufactureDate))
    }
    setPassportData((current) => ({
      ...current,
      ...suggestions.passportData,
    }))
    setError('')
    setNotice('Selected AI suggestions were applied. Review them before saving.')
  }

  async function saveItem(targetStatus) {
    setIsSaving(true)
    setError('')
    setNotice('')
    try {
      if (!isEditing) {
        const created = await createProductItem(accessToken, {
          model_id: selectedModelId,
          serial_number: serialNumber,
          manufacture_date: manufactureDate || null,
          passport_data: passportData,
        })
        setNotice('Product item was created as a draft.')
        onCreated(created)
        return
      }

      const updateData = {
        serial_number: serialNumber,
        manufacture_date: manufactureDate || null,
        passport_data: passportData,
      }
      if (targetStatus === 'published') updateData.status = 'published'

      const updated = await updateProductItem(accessToken, itemId, updateData)
      setItem(updated)
      setNotice(
        updated.status === 'published'
          ? 'Product passport was published.'
          : 'Draft changes were saved.',
      )
    } catch (saveError) {
      if (saveError instanceof ApiError && saveError.status === 401) {
        onLogout()
        return
      }
      setError(
        saveError instanceof ApiError
          ? saveError.message
          : 'The product item could not be saved.',
      )
    } finally {
      setIsSaving(false)
    }
  }

  async function retireItem() {
    setIsSaving(true)
    setError('')
    setNotice('')
    try {
      const updated = await updateProductItem(accessToken, itemId, {
        status: 'retired',
      })
      setItem(updated)
      setIsRetirementConfirmationOpen(false)
      setNotice('Product item was retired.')
    } catch (retireError) {
      if (retireError instanceof ApiError && retireError.status === 401) {
        onLogout()
        return
      }
      setError(
        retireError instanceof ApiError
          ? retireError.message
          : 'The product item could not be retired.',
      )
    } finally {
      setIsSaving(false)
    }
  }

  async function generateQrCode() {
    setIsGeneratingQrCode(true)
    setError('')
    try {
      const qrCode = await getProductItemQrCode(accessToken, itemId)
      setQrCodeUrl(URL.createObjectURL(qrCode))
    } catch (qrError) {
      if (qrError instanceof ApiError && qrError.status === 401) {
        onLogout()
        return
      }
      setError('The QR code could not be generated. Please try again.')
    } finally {
      setIsGeneratingQrCode(false)
    }
  }

  async function addLifecycleEvent(event) {
    event.preventDefault()
    setIsSavingEvent(true)
    setError('')
    setNotice('')
    try {
      const created = await createLifecycleEvent(accessToken, itemId, {
        event_type: eventType,
        occurred_at: new Date(eventTime).toISOString(),
        description: eventDescription || null,
        service_provider: eventProvider || null,
        access_level: eventAccessLevel,
        event_data: {},
      })
      setLifecycleEvents((current) =>
        [...current, created].sort(
          (first, second) =>
            new Date(second.occurred_at) - new Date(first.occurred_at),
        ),
      )
      setEventDescription('')
      setEventProvider('')
      setEventTime(defaultEventTime())
      setNotice('Lifecycle event was added.')
    } catch (eventError) {
      if (eventError instanceof ApiError && eventError.status === 401) {
        onLogout()
        return
      }
      setError(
        eventError instanceof ApiError
          ? eventError.message
          : 'The lifecycle event could not be added.',
      )
    } finally {
      setIsSavingEvent(false)
    }
  }

  const selectedModel = models.find((model) => model.id === selectedModelId)
  const isDraft = !isEditing || item?.status === 'draft'

  return (
    <div className={styles.page}>
      <AppHeader
        currentSection="product-items"
        currentUser={currentUser}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />
      <main className={styles.main}>
        <button className={styles.backButton} type="button" onClick={onBack}>
          ← Back to product items
        </button>
        <header className={styles.pageHeading}>
          <div>
            <h1>{isEditing ? 'Product item' : 'Create product item'}</h1>
            <p>Passport values follow the selected model template.</p>
          </div>
          {item && <StatusBadge status={item.status} />}
        </header>

        {notice && <p className={styles.notice} role="status">{notice}</p>}
        {error && <p className={styles.error} role="alert">{error}</p>}
        {loadState === 'loading' && (
          <section className={styles.stateCard}><h2>Loading form…</h2></section>
        )}
        {loadState === 'error' && (
          <section className={styles.stateCard} role="alert">
            <h2>Product item form could not be loaded</h2>
          </section>
        )}
        {loadState === 'success' && (
          <>
            <section className={styles.sectionCard}>
              <div className={styles.sectionHeading}>
                <div>
                  <h2>Product identity</h2>
                  <p>Information that identifies this physical product.</p>
                </div>
              </div>
              <div className={styles.fieldGrid}>
                <div className={styles.field}>
                  <label htmlFor="item-model">Product model</label>
                  {isEditing ? (
                    <p className={styles.readonlyValue}>{selectedModel?.name}</p>
                  ) : (
                    <select
                      id="item-model"
                      value={selectedModelId}
                      onChange={(event) => handleModelChange(event.target.value)}
                      required
                    >
                      <option value="">Select a model</option>
                      {models.map((model) => (
                        <option key={model.id} value={model.id}>
                          {model.name} · {model.model_code}
                        </option>
                      ))}
                    </select>
                  )}
                  {!isEditing && models.length === 0 && (
                    <p className={styles.helperText}>
                      Create an active Product Model with an Active template first.
                    </p>
                  )}
                </div>
                <div className={styles.field}>
                  <label htmlFor="item-serial">Serial number</label>
                  <input
                    id="item-serial"
                    maxLength="100"
                    value={serialNumber}
                    onChange={(event) => setSerialNumber(event.target.value)}
                    disabled={!isDraft}
                    required
                  />
                </div>
                <div className={styles.field}>
                  <label htmlFor="item-date">Manufacture date (optional)</label>
                  <input
                    id="item-date"
                    type="date"
                    value={manufactureDate}
                    onChange={(event) => setManufactureDate(event.target.value)}
                    disabled={!isDraft}
                  />
                </div>
              </div>
            </section>

            {template && isDraft && (
              <AiDocumentUpload
                key={selectedModelId}
                accessToken={accessToken}
                productModelId={selectedModelId}
                onApply={applyAiSuggestions}
                onUnauthorized={onLogout}
              />
            )}

            {template && (
              <section className={styles.sectionCard}>
                <div className={styles.sectionHeading}>
                  <div>
                    <h2>Passport information</h2>
                    <p>{template.name} · Version {template.version}</p>
                  </div>
                </div>
                <div className={styles.passportFields}>
                  {template.fields.map((field) => (
                    <PassportFieldControl
                      key={field.id}
                      field={field}
                      value={passportData[field.code]}
                      disabled={!isDraft}
                      onChange={(value) => updatePassportValue(field, value)}
                    />
                  ))}
                </div>
              </section>
            )}

            {item && item.status !== 'draft' && (
              <section className={styles.sectionCard}>
                <div className={styles.sectionHeading}>
                  <div>
                    <h2>Lifecycle history</h2>
                    <p>Record maintenance and other events for this product.</p>
                  </div>
                </div>

                <form className={styles.eventForm} onSubmit={addLifecycleEvent}>
                  <div className={styles.field}>
                    <label htmlFor="event-type">Event type</label>
                    <select
                      id="event-type"
                      value={eventType}
                      onChange={(event) => setEventType(event.target.value)}
                    >
                      {eventTypes.map((type) => (
                        <option key={type} value={type}>{eventLabel(type)}</option>
                      ))}
                    </select>
                  </div>
                  <div className={styles.field}>
                    <label htmlFor="event-time">Date and time</label>
                    <input
                      id="event-time"
                      type="datetime-local"
                      value={eventTime}
                      onChange={(event) => setEventTime(event.target.value)}
                      required
                    />
                  </div>
                  <div className={styles.field}>
                    <label htmlFor="event-provider">Service provider (optional)</label>
                    <input
                      id="event-provider"
                      maxLength="255"
                      value={eventProvider}
                      onChange={(event) => setEventProvider(event.target.value)}
                    />
                  </div>
                  <div className={styles.field}>
                    <label htmlFor="event-access">Visibility</label>
                    <select
                      id="event-access"
                      value={eventAccessLevel}
                      onChange={(event) => setEventAccessLevel(event.target.value)}
                    >
                      <option value="public">Public passport</option>
                      <option value="manufacturer">Manufacturer only</option>
                    </select>
                  </div>
                  <div className={`${styles.field} ${styles.eventDescription}`}>
                    <label htmlFor="event-description">Description (optional)</label>
                    <textarea
                      id="event-description"
                      maxLength="2000"
                      rows="3"
                      value={eventDescription}
                      onChange={(event) => setEventDescription(event.target.value)}
                    />
                  </div>
                  <div className={`${styles.actions} ${styles.eventActions}`}>
                    <button
                      className={styles.primaryButton}
                      type="submit"
                      disabled={isSavingEvent || !eventTime}
                    >
                      {isSavingEvent ? 'Adding…' : 'Add lifecycle event'}
                    </button>
                  </div>
                </form>

                {lifecycleEvents.length > 0 ? (
                  <ol className={styles.eventList}>
                    {lifecycleEvents.map((event) => (
                      <li key={event.id} className={styles.eventItem}>
                        <div className={styles.eventItemHeading}>
                          <h3>{eventLabel(event.event_type)}</h3>
                          <span className={styles.visibilityLabel}>
                            {event.access_level === 'public'
                              ? 'Public'
                              : 'Manufacturer only'}
                          </span>
                        </div>
                        <time dateTime={event.occurred_at}>
                          {eventDateFormatter.format(new Date(event.occurred_at))}
                        </time>
                        {event.description && <p>{event.description}</p>}
                        {event.service_provider && (
                          <p className={styles.helperText}>
                            Service provider: {event.service_provider}
                          </p>
                        )}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className={styles.emptyText}>No lifecycle events yet.</p>
                )}
              </section>
            )}

            {item?.status === 'published' && (
              <section className={styles.sectionCard}>
                <h2>Public passport</h2>
                <p className={styles.publicLink}>
                  <a href={`/passport/${item.public_id}`} target="_blank" rel="noreferrer">
                    Open public passport
                  </a>
                </p>
              </section>
            )}

            {item?.status === 'published' && (
              <NfcWriter
                passportUrl={`${window.location.origin}/passport/${item.public_id}`}
              />
            )}

            {item?.status === 'published' && (
              <section className={`${styles.sectionCard} ${styles.qrCard}`}>
                <div className={styles.sectionHeading}>
                  <div>
                    <h2>Printable QR code</h2>
                    <p className={styles.qrExplanation}>
                      Generate it again whenever another product label is needed.
                    </p>
                  </div>
                  <button
                    className={styles.secondaryButton}
                    type="button"
                    onClick={generateQrCode}
                    disabled={isGeneratingQrCode}
                  >
                    {isGeneratingQrCode
                      ? 'Generating…'
                      : qrCodeUrl
                        ? 'Generate again'
                        : 'Generate QR code'}
                  </button>
                </div>

                {qrCodeUrl && (
                  <>
                    <div className={styles.qrPreview}>
                      <img
                        className={styles.qrImage}
                        src={qrCodeUrl}
                        alt={`QR code for product ${item.serial_number}`}
                      />
                      <div>
                        <h3>{selectedModel?.name}</h3>
                        <p className={styles.code}>{item.serial_number}</p>
                        <p className={styles.qrUrl}>
                          {window.location.origin}/passport/{item.public_id}
                        </p>
                      </div>
                    </div>
                    <div className={`${styles.actions} ${styles.qrActions}`}>
                      <a
                        className={styles.secondaryButton}
                        href={qrCodeUrl}
                        download={`passport-${item.public_id}.svg`}
                      >
                        Download SVG
                      </a>
                      <button
                        className={styles.primaryButton}
                        type="button"
                        onClick={() => window.print()}
                      >
                        Print QR code
                      </button>
                    </div>
                  </>
                )}
              </section>
            )}

            {item?.status === 'published' && isRetirementConfirmationOpen && (
              <div className={styles.retirementConfirmation} role="alert">
                <div>
                  <h2>Retire this product?</h2>
                  <p>
                    The product passport will be marked as retired. This action
                    cannot be reversed from the application.
                  </p>
                </div>
                <div className={styles.confirmationActions}>
                  <button
                    className={styles.textButton}
                    type="button"
                    onClick={() => setIsRetirementConfirmationOpen(false)}
                    disabled={isSaving}
                  >
                    Cancel
                  </button>
                  <button
                    className={styles.dangerButton}
                    type="button"
                    onClick={retireItem}
                    disabled={isSaving}
                  >
                    {isSaving ? 'Retiring…' : 'Yes, retire product'}
                  </button>
                </div>
              </div>
            )}

            <div className={styles.actions}>
              <button className={styles.secondaryButton} type="button" onClick={onBack}>
                Back
              </button>
              {isDraft && (
                <>
                  <button
                    className={styles.secondaryButton}
                    type="button"
                    onClick={() => saveItem('draft')}
                    disabled={isSaving || !selectedModelId || !template || !serialNumber}
                  >
                    {isSaving ? 'Saving…' : isEditing ? 'Save draft' : 'Create draft'}
                  </button>
                  {isEditing && (
                    <button
                      className={styles.primaryButton}
                      type="button"
                      onClick={() => saveItem('published')}
                      disabled={isSaving}
                    >
                      Publish passport
                    </button>
                  )}
                </>
              )}
              {item?.status === 'published' &&
                isOrganizationAdmin &&
                !isRetirementConfirmationOpen && (
                <button
                  className={styles.dangerButton}
                  type="button"
                  onClick={() => setIsRetirementConfirmationOpen(true)}
                  disabled={isSaving}
                >
                  Retire product
                </button>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  )
}

export default ProductItemFormPage
