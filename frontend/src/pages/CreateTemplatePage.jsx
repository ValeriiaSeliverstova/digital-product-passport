import { useEffect, useState } from 'react'

import AppHeader from '../components/AppHeader.jsx'
import { ApiError } from '../services/api.js'
import { createTemplate, getCategories } from '../services/templates.js'
import styles from './CreateTemplatePage.module.css'

function CreateTemplatePage({
  accessToken,
  currentUser,
  onCancel,
  onCreated,
  onLogout,
}) {
  const [name, setName] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [version, setVersion] = useState('1')
  const [categories, setCategories] = useState([])
  const [categoryState, setCategoryState] = useState('loading')
  const [categoryReloadKey, setCategoryReloadKey] = useState(0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let isCurrentRequest = true

    async function loadCategories() {
      setCategoryState('loading')

      try {
        const categoryData = await getCategories()
        if (isCurrentRequest) {
          setCategories(categoryData)
          setCategoryState('success')
        }
      } catch {
        if (isCurrentRequest) {
          setCategoryState('error')
        }
      }
    }

    loadCategories()

    return () => {
      isCurrentRequest = false
    }
  }, [categoryReloadKey])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const template = await createTemplate(accessToken, {
        name,
        category_id: categoryId,
        version: Number(version),
      })
      onCreated(template)
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 401) {
        onLogout()
        return
      }

      if (submitError instanceof ApiError && submitError.status === 409) {
        setError('A template with this name and version already exists.')
      } else if (submitError instanceof ApiError && submitError.status === 404) {
        setError('The selected product category is no longer available.')
      } else if (submitError instanceof ApiError && submitError.status === 422) {
        setError('Check the template name, category, and version.')
      } else {
        setError('The template could not be created. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const formUnavailable =
    categoryState !== 'success' || categories.length === 0 || isSubmitting

  return (
    <div className={styles.page}>
      <AppHeader currentUser={currentUser} onLogout={onLogout} />

      <main className={styles.main}>
        <button className={styles.backButton} type="button" onClick={onCancel}>
          ← Back to templates
        </button>

        <div className={styles.heading}>
          <h1>Create template</h1>
          <p>New templates start as editable drafts.</p>
        </div>

        <section className={styles.card} aria-labelledby="template-form-title">
          <h2 id="template-form-title" className="visually-hidden">
            Template information
          </h2>

          <form className={styles.form} onSubmit={handleSubmit}>
            <div className={styles.field}>
              <label htmlFor="template-name">Template name</label>
              <input
                id="template-name"
                name="name"
                type="text"
                autoComplete="off"
                maxLength="255"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
              <p className={styles.helperText}>
                Use a clear name that identifies the passport.
              </p>
            </div>

            <div className={styles.field}>
              <label htmlFor="category">Product category</label>
              <select
                id="category"
                name="category_id"
                value={categoryId}
                onChange={(event) => setCategoryId(event.target.value)}
                disabled={categoryState !== 'success'}
                required
              >
                <option value="">
                  {categoryState === 'loading'
                    ? 'Loading categories…'
                    : 'Select a category'}
                </option>
                {categories.map((category) => (
                  <option value={category.id} key={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>

              {categoryState === 'error' && (
                <div className={styles.categoryError} role="alert">
                  <span>Categories could not be loaded.</span>
                  <button
                    className={styles.inlineButton}
                    type="button"
                    onClick={() => setCategoryReloadKey((key) => key + 1)}
                  >
                    Try again
                  </button>
                </div>
              )}

              {categoryState === 'success' && categories.length === 0 && (
                <p className={styles.errorText} role="alert">
                  No active product categories are available.
                </p>
              )}
            </div>

            <div className={styles.field}>
              <label htmlFor="version">Version</label>
              <input
                id="version"
                name="version"
                type="number"
                min="1"
                max="2147483647"
                step="1"
                value={version}
                onChange={(event) => setVersion(event.target.value)}
                required
              />
            </div>

            {error && (
              <p className={styles.formError} role="alert">
                {error}
              </p>
            )}

            <div className={styles.actions}>
              <button
                className={styles.cancelButton}
                type="button"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                className={styles.submitButton}
                type="submit"
                disabled={formUnavailable}
              >
                {isSubmitting ? 'Creating draft…' : 'Create draft'}
              </button>
            </div>
          </form>
        </section>

        <aside className={styles.information} aria-labelledby="next-step-title">
          <h2 id="next-step-title">What happens next?</h2>
          <p>Add and validate fields before activating the template.</p>
        </aside>
      </main>
    </div>
  )
}

export default CreateTemplatePage
