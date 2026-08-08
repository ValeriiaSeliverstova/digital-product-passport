import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import TemplateFieldForm from '../components/TemplateFieldForm.jsx'
import { ApiError } from '../services/api.js'
import {
  createTemplateField,
  createTemplateVersion,
  deleteTemplateField,
  getTemplate,
  getTemplateListData,
  updateTemplate,
  updateTemplateField,
} from '../services/templates.js'
import styles from './EditTemplatePage.module.css'

const typeLabels = {
  text: 'Text',
  integer: 'Integer',
  decimal: 'Decimal number',
  boolean: 'Yes / No',
  date: 'Date',
}

function sortFields(fields) {
  return [...fields].sort(
    (first, second) =>
      first.display_order - second.display_order ||
      first.label.localeCompare(second.label),
  )
}

function validationSummary(field) {
  const rules = field.validation_rules || {}
  const parts = []

  if (rules.min_length !== undefined) {
    parts.push(`minimum length ${rules.min_length}`)
  }
  if (rules.max_length !== undefined) {
    parts.push(`maximum length ${rules.max_length}`)
  }
  if (rules.min !== undefined) {
    parts.push(`minimum ${rules.min}`)
  }
  if (rules.max !== undefined) {
    parts.push(`maximum ${rules.max}`)
  }
  if (rules.allowed_values) {
    parts.push(`allowed: ${rules.allowed_values.join(', ')}`)
  }

  return parts.length > 0 ? parts.join(' · ') : 'No additional validation'
}

function EditTemplatePage({
  accessToken,
  currentUser,
  templateId,
  onBack,
  onLogout,
  onNavigate,
  onSelectVersion,
}) {
  const [template, setTemplate] = useState(null)
  const [versions, setVersions] = useState([])
  const [categoryName, setCategoryName] = useState('')
  const [loadState, setLoadState] = useState('loading')
  const [reloadKey, setReloadKey] = useState(0)
  const [name, setName] = useState('')
  const [isSavingName, setIsSavingName] = useState(false)
  const [fieldFormMode, setFieldFormMode] = useState(null)
  const [isSavingField, setIsSavingField] = useState(false)
  const [deletingFieldId, setDeletingFieldId] = useState(null)
  const [isDeletingField, setIsDeletingField] = useState(false)
  const [pendingStatus, setPendingStatus] = useState(null)
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false)
  const [isCreatingVersion, setIsCreatingVersion] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrentRequest = true

    async function loadPage() {
      setLoadState('loading')
      setError('')

      try {
        const [templateData, listData] = await Promise.all([
          getTemplate(accessToken, templateId),
          getTemplateListData(accessToken),
        ])

        if (isCurrentRequest) {
          setTemplate({
            ...templateData,
            fields: sortFields(templateData.fields),
          })
          setName(templateData.name)
          setFieldFormMode(null)
          setDeletingFieldId(null)
          setPendingStatus(null)
          setVersions(
            listData.templates
              .filter(
                (item) =>
                  item.template_family_id === templateData.template_family_id,
              )
              .sort((first, second) => second.version - first.version),
          )
          setCategoryName(
            listData.categories.find(
              (category) => category.id === templateData.category_id,
            )?.name || 'Category unavailable',
          )
          setLoadState('success')
        }
      } catch (loadError) {
        if (!isCurrentRequest) {
          return
        }
        if (loadError instanceof ApiError && loadError.status === 401) {
          onLogout()
          return
        }
        setLoadState('error')
      }
    }

    loadPage()

    return () => {
      isCurrentRequest = false
    }
  }, [accessToken, onLogout, reloadKey, templateId])

  function showApiError(apiError, fallbackMessage) {
    if (apiError instanceof ApiError && apiError.status === 401) {
      onLogout()
      return
    }
    if (apiError instanceof ApiError && apiError.status === 409) {
      setError(apiError.message)
      return
    }
    if (apiError instanceof ApiError && apiError.status === 422) {
      setError('Check the entered values and try again.')
      return
    }
    setError(fallbackMessage)
  }

  async function handleNameSave(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setIsSavingName(true)

    try {
      const updatedTemplate = await updateTemplate(accessToken, templateId, {
        name,
      })
      setTemplate((current) => ({ ...current, name: updatedTemplate.name }))
      setVersions((current) =>
        current.map((version) => ({
          ...version,
          name: updatedTemplate.name,
        })),
      )
      setNotice('Template name was saved.')
    } catch (saveError) {
      showApiError(saveError, 'The template name could not be saved.')
    } finally {
      setIsSavingName(false)
    }
  }

  async function handleFieldSave(fieldData) {
    setError('')
    setNotice('')
    setIsSavingField(true)

    try {
      let savedField
      if (fieldFormMode === 'new') {
        savedField = await createTemplateField(
          accessToken,
          templateId,
          fieldData,
        )
        setTemplate((current) => ({
          ...current,
          fields: sortFields([...current.fields, savedField]),
        }))
        setNotice('Field was added to the draft.')
      } else {
        savedField = await updateTemplateField(
          accessToken,
          templateId,
          fieldFormMode,
          fieldData,
        )
        setTemplate((current) => ({
          ...current,
          fields: sortFields(
            current.fields.map((field) =>
              field.id === savedField.id ? savedField : field,
            ),
          ),
        }))
        setNotice('Field changes were saved.')
      }
      setFieldFormMode(null)
    } catch (saveError) {
      showApiError(saveError, 'The field could not be saved.')
    } finally {
      setIsSavingField(false)
    }
  }

  async function handleFieldDelete(fieldId) {
    setError('')
    setNotice('')
    setIsDeletingField(true)

    try {
      await deleteTemplateField(accessToken, templateId, fieldId)
      setTemplate((current) => ({
        ...current,
        fields: current.fields.filter((field) => field.id !== fieldId),
      }))
      setDeletingFieldId(null)
      setNotice('Field was deleted.')
    } catch (deleteError) {
      showApiError(deleteError, 'The field could not be deleted.')
    } finally {
      setIsDeletingField(false)
    }
  }

  async function handleStatusUpdate() {
    if (!pendingStatus) {
      return
    }

    setError('')
    setNotice('')
    setIsUpdatingStatus(true)

    try {
      const updatedTemplate = await updateTemplate(accessToken, templateId, {
        status: pendingStatus,
      })
      // The update response contains metadata only, so preserve loaded fields.
      setTemplate((current) => ({ ...current, ...updatedTemplate }))
      setVersions((current) =>
        current.map((version) =>
          version.id === updatedTemplate.id ? updatedTemplate : version,
        ),
      )
      setPendingStatus(null)
      setFieldFormMode(null)
      setNotice(
        updatedTemplate.status === 'active'
          ? 'Template is now active and its fields are read-only.'
          : 'Template was archived.',
      )
    } catch (statusError) {
      showApiError(statusError, 'The template status could not be changed.')
    } finally {
      setIsUpdatingStatus(false)
    }
  }

  async function handleCreateVersion() {
    setError('')
    setNotice('')
    setIsCreatingVersion(true)

    try {
      const newVersion = await createTemplateVersion(accessToken, templateId)
      setNotice(
        `Version ${newVersion.version} was created as an editable draft.`,
      )
      onSelectVersion(newVersion.id)
    } catch (versionError) {
      showApiError(versionError, 'A new template version could not be created.')
    } finally {
      setIsCreatingVersion(false)
    }
  }

  const editedField =
    fieldFormMode && fieldFormMode !== 'new'
      ? template?.fields.find((field) => field.id === fieldFormMode)
      : null
  const draftVersion = versions.find((version) => version.status === 'draft')
  const latestVersion = versions[0]
  const canCreateVersion =
    template?.status !== 'draft' &&
    !draftVersion &&
    template?.id === latestVersion?.id
  const hasAnotherDraft = draftVersion && draftVersion.id !== template?.id
  const isOlderVersion =
    !draftVersion && template?.id !== latestVersion?.id

  return (
    <div className={styles.page}>
      <AppHeader
        currentSection="templates"
        currentUser={currentUser}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />

      <main className={styles.main}>
        <button className={styles.backButton} type="button" onClick={onBack}>
          ← Back to templates
        </button>

        {loadState === 'loading' && (
          <section className={styles.stateCard} aria-live="polite">
            <h1>Loading template…</h1>
          </section>
        )}

        {loadState === 'error' && (
          <section className={styles.stateCard} role="alert">
            <h1>Template could not be loaded</h1>
            <p>It may be unavailable, or the connection may have failed.</p>
            <button
              className={styles.primaryButton}
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
            >
              Try again
            </button>
          </section>
        )}

        {loadState === 'success' && template && (
          <>
            <header className={styles.heading}>
              <div>
                <div className={styles.titleRow}>
                  <h1>{template.name}</h1>
                  <StatusBadge status={template.status} />
                </div>
                <p>
                  {categoryName} · Version {template.version}
                </p>
              </div>
            </header>

            {notice && (
              <p className={styles.notice} role="status">
                {notice}
              </p>
            )}
            {error && (
              <p className={styles.error} role="alert">
                {error}
              </p>
            )}

            <section className={styles.card} aria-labelledby="versions-title">
              <div className={styles.sectionHeading}>
                <div>
                  <h2 id="versions-title">Version history</h2>
                  <p>Open a version to view its exact fields and status.</p>
                </div>

                {canCreateVersion && (
                  <button
                    className={styles.primaryButton}
                    type="button"
                    onClick={handleCreateVersion}
                    disabled={isCreatingVersion}
                  >
                    {isCreatingVersion ? 'Creating…' : 'Create new version'}
                  </button>
                )}

                {template.status === 'draft' && (
                  <button
                    className={styles.secondaryButton}
                    type="button"
                    disabled
                  >
                    Create new version
                  </button>
                )}

                {hasAnotherDraft && (
                  <button
                    className={styles.secondaryButton}
                    type="button"
                    onClick={() => onSelectVersion(draftVersion.id)}
                  >
                    Open draft version {draftVersion.version}
                  </button>
                )}

                {isOlderVersion && (
                  <button
                    className={styles.secondaryButton}
                    type="button"
                    onClick={() => onSelectVersion(latestVersion.id)}
                  >
                    Open latest version {latestVersion.version}
                  </button>
                )}
              </div>

              {template.status === 'draft' && (
                <p className={styles.statusHint}>
                  Activate this draft before creating the next version.
                </p>
              )}

              {hasAnotherDraft && (
                <p className={styles.statusHint}>
                  Version {draftVersion.version} is already an editable draft.
                </p>
              )}

              {isOlderVersion && (
                <p className={styles.statusHint}>
                  New versions must be copied from the latest version.
                </p>
              )}

              <div className={styles.versionList}>
                {versions.map((version) => (
                  <button
                    className={styles.versionButton}
                    type="button"
                    key={version.id}
                    onClick={() => onSelectVersion(version.id)}
                    disabled={version.id === template.id}
                    aria-current={version.id === template.id ? 'page' : undefined}
                  >
                    <span>Version {version.version}</span>
                    <StatusBadge status={version.status} />
                  </button>
                ))}
              </div>
            </section>

            <section className={styles.card} aria-labelledby="details-title">
              <div className={styles.sectionHeading}>
                <div>
                  <h2 id="details-title">Template details</h2>
                  <p>
                    The family name applies to every version. Category and
                    version numbers cannot change after creation.
                  </p>
                </div>
              </div>

              <form className={styles.nameForm} onSubmit={handleNameSave}>
                <div className={styles.nameField}>
                  <label htmlFor="template-name">Template family name</label>
                  <input
                    id="template-name"
                    maxLength="255"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    required
                  />
                </div>
                <button
                  className={styles.secondaryButton}
                  type="submit"
                  disabled={isSavingName || name.trim() === template.name}
                >
                  {isSavingName ? 'Saving…' : 'Save name'}
                </button>
              </form>
            </section>

            <section className={styles.card} aria-labelledby="lifecycle-title">
              <div className={styles.sectionHeading}>
                <div>
                  <h2 id="lifecycle-title">Template status</h2>
                  {template.status === 'draft' && (
                    <p>
                      Activate the template when its fields are complete. Active
                      fields cannot be edited.
                    </p>
                  )}
                  {template.status === 'active' && (
                    <p>
                      This template is available for use. Archive it when it
                      should no longer be used for new passports.
                    </p>
                  )}
                  {template.status === 'archived' && (
                    <p>This template is retained as a read-only record.</p>
                  )}
                </div>

                {template.status === 'draft' && pendingStatus === null && (
                  <button
                    className={styles.primaryButton}
                    type="button"
                    onClick={() => setPendingStatus('active')}
                    disabled={template.fields.length === 0 || fieldFormMode !== null}
                  >
                    Activate template
                  </button>
                )}

                {template.status === 'active' && pendingStatus === null && (
                  <button
                    className={styles.archiveButton}
                    type="button"
                    onClick={() => setPendingStatus('archived')}
                  >
                    Archive template
                  </button>
                )}
              </div>

              {template.status === 'draft' && template.fields.length === 0 && (
                <p className={styles.statusHint}>
                  Add at least one field before activation.
                </p>
              )}

              {template.status === 'draft' && fieldFormMode !== null && (
                <p className={styles.statusHint}>
                  Finish or cancel the open field form before activation.
                </p>
              )}

              {pendingStatus && (
                <div className={styles.statusConfirmation} role="alert">
                  <div>
                    <h3>
                      {pendingStatus === 'active'
                        ? 'Activate this template?'
                        : 'Archive this template?'}
                    </h3>
                    <p>
                      {pendingStatus === 'active'
                        ? 'Its field structure will become read-only. Future changes should use a new template version.'
                        : 'It will no longer be available for creating new passports.'}
                    </p>
                  </div>
                  <div className={styles.confirmationActions}>
                    <button
                      className={styles.textButton}
                      type="button"
                      onClick={() => setPendingStatus(null)}
                      disabled={isUpdatingStatus}
                    >
                      Cancel
                    </button>
                    <button
                      className={
                        pendingStatus === 'active'
                          ? styles.primaryButton
                          : styles.confirmDeleteButton
                      }
                      type="button"
                      onClick={handleStatusUpdate}
                      disabled={isUpdatingStatus}
                    >
                      {isUpdatingStatus
                        ? 'Updating…'
                        : pendingStatus === 'active'
                          ? 'Activate template'
                          : 'Archive template'}
                    </button>
                  </div>
                </div>
              )}
            </section>

            <section className={styles.fieldsSection} aria-labelledby="fields-title">
              <div className={styles.sectionHeading}>
                <div>
                  <h2 id="fields-title">Template fields</h2>
                  <p>
                    {template.fields.length}{' '}
                    {template.fields.length === 1 ? 'field' : 'fields'} in this
                    template
                  </p>
                </div>
                {template.status === 'draft' && fieldFormMode === null && (
                  <button
                    className={styles.primaryButton}
                    type="button"
                    onClick={() => {
                      setError('')
                      setNotice('')
                      setDeletingFieldId(null)
                      setFieldFormMode('new')
                    }}
                  >
                    Add field
                  </button>
                )}
              </div>

              {fieldFormMode && (
                <div className={styles.fieldFormCard}>
                  <h3>{fieldFormMode === 'new' ? 'Add field' : 'Edit field'}</h3>
                  <TemplateFieldForm
                    key={fieldFormMode}
                    initialField={editedField}
                    isSaving={isSavingField}
                    onSave={handleFieldSave}
                    onCancel={() => {
                      setFieldFormMode(null)
                      setError('')
                    }}
                  />
                </div>
              )}

              {template.fields.length === 0 && !fieldFormMode && (
                <div className={styles.emptyState}>
                  <h3>No fields yet</h3>
                  <p>Add at least one field before activating this template.</p>
                </div>
              )}

              <div className={styles.fieldList}>
                {template.fields.map((field) => (
                  <article className={styles.fieldCard} key={field.id}>
                    <div className={styles.fieldHeading}>
                      <div>
                        <h3>{field.label}</h3>
                        <code>{field.code}</code>
                      </div>
                      {template.status === 'draft' && (
                        <div className={styles.fieldActions}>
                          <button
                            className={styles.textButton}
                            type="button"
                            onClick={() => {
                              setError('')
                              setNotice('')
                              setDeletingFieldId(null)
                              setFieldFormMode(field.id)
                            }}
                            disabled={fieldFormMode !== null}
                          >
                            Edit
                          </button>
                          <button
                            className={styles.deleteButton}
                            type="button"
                            onClick={() => setDeletingFieldId(field.id)}
                            disabled={fieldFormMode !== null}
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </div>

                    <dl className={styles.fieldMetadata}>
                      <div>
                        <dt>Type</dt>
                        <dd>{typeLabels[field.data_type]}</dd>
                      </div>
                      <div>
                        <dt>Access</dt>
                        <dd>
                          {field.access_level === 'public'
                            ? 'Public'
                            : 'Manufacturer only'}
                        </dd>
                      </div>
                      <div>
                        <dt>Required</dt>
                        <dd>{field.is_required ? 'Yes' : 'No'}</dd>
                      </div>
                      <div>
                        <dt>Order</dt>
                        <dd>{field.display_order}</dd>
                      </div>
                    </dl>
                    <p className={styles.rulesSummary}>
                      {validationSummary(field)}
                    </p>

                    {deletingFieldId === field.id && (
                      <div className={styles.deleteConfirmation} role="alert">
                        <p>
                          Delete “{field.label}”? This action cannot be undone.
                        </p>
                        <div>
                          <button
                            className={styles.textButton}
                            type="button"
                            onClick={() => setDeletingFieldId(null)}
                            disabled={isDeletingField}
                          >
                            Keep field
                          </button>
                          <button
                            className={styles.confirmDeleteButton}
                            type="button"
                            onClick={() => handleFieldDelete(field.id)}
                            disabled={isDeletingField}
                          >
                            {isDeletingField ? 'Deleting…' : 'Delete field'}
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

export default EditTemplatePage
