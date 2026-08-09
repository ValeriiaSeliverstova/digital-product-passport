import { useEffect, useId, useRef, useState } from 'react'

import { ApiError } from '../services/api.js'
import { extractProductData } from '../services/productModels.js'
import styles from './AiDocumentUpload.module.css'

const MAX_FILE_SIZE = 10 * 1024 * 1024
const ACCEPTED_FILES = '.pdf,image/jpeg,image/png,image/webp,image/heic,image/heif'

function formatFileSize(size) {
  if (size < 1024 * 1024) return `${Math.ceil(size / 1024)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

const SERIAL_NUMBER_KEY = 'identity:serial_number'
const MANUFACTURE_DATE_KEY = 'identity:manufacture_date'

function displayValue(value) {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

function suggestionRows(extraction) {
  if (!extraction) return []

  const rows = []
  if (extraction.identity.serial_number) {
    rows.push({
      key: SERIAL_NUMBER_KEY,
      label: 'Serial number',
      ...extraction.identity.serial_number,
    })
  }
  if (extraction.identity.manufacture_date) {
    rows.push({
      key: MANUFACTURE_DATE_KEY,
      label: 'Manufacture date',
      ...extraction.identity.manufacture_date,
    })
  }
  extraction.fields.forEach((field) => {
    rows.push({
      key: `field:${field.field_code}`,
      label: field.field_label,
      ...field,
    })
  })
  return rows
}

/** Uploads one source and lets the manufacturer review Gemini suggestions. */
function AiDocumentUpload({
  accessToken,
  productModelId,
  onApply,
  onUnauthorized,
}) {
  const uploadInputId = useId()
  const cameraInputId = useId()
  const uploadInputRef = useRef(null)
  const cameraInputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [error, setError] = useState('')
  const [extraction, setExtraction] = useState(null)
  const [selectedSuggestions, setSelectedSuggestions] = useState(new Set())
  const [isExtracting, setIsExtracting] = useState(false)
  const [applyNotice, setApplyNotice] = useState('')

  useEffect(() => {
    if (!selectedFile?.type.startsWith('image/')) {
      setPreviewUrl('')
      return undefined
    }

    const nextPreviewUrl = URL.createObjectURL(selectedFile)
    setPreviewUrl(nextPreviewUrl)
    return () => URL.revokeObjectURL(nextPreviewUrl)
  }, [selectedFile])

  function selectFile(file) {
    setError('')
    setExtraction(null)
    setSelectedSuggestions(new Set())
    setApplyNotice('')
    if (!file) return

    if (file.type !== 'application/pdf' && !file.type.startsWith('image/')) {
      setSelectedFile(null)
      setError('Choose a PDF or image file.')
      return
    }
    if (file.size > MAX_FILE_SIZE) {
      setSelectedFile(null)
      setError('The source file must not exceed 10 MB.')
      return
    }

    setSelectedFile(file)
  }

  function clearSelection() {
    setSelectedFile(null)
    setExtraction(null)
    setSelectedSuggestions(new Set())
    setApplyNotice('')
    setError('')
    if (uploadInputRef.current) uploadInputRef.current.value = ''
    if (cameraInputRef.current) cameraInputRef.current.value = ''
  }

  async function extractSuggestions() {
    if (!selectedFile) return

    setIsExtracting(true)
    setError('')
    setExtraction(null)
    setApplyNotice('')
    try {
      const result = await extractProductData(
        accessToken,
        productModelId,
        selectedFile,
      )
      const rows = suggestionRows(result)
      setExtraction(result)
      setSelectedSuggestions(new Set(rows.map((row) => row.key)))
    } catch (extractionError) {
      if (extractionError instanceof ApiError && extractionError.status === 401) {
        onUnauthorized()
        return
      }
      setError(
        extractionError instanceof ApiError
          ? extractionError.message
          : 'The document could not be analyzed. Please try again.',
      )
    } finally {
      setIsExtracting(false)
    }
  }

  function toggleSuggestion(key) {
    setApplyNotice('')
    setSelectedSuggestions((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  function applySuggestions() {
    const passportData = {}
    extraction.fields.forEach((field) => {
      if (selectedSuggestions.has(`field:${field.field_code}`)) {
        passportData[field.field_code] = field.value
      }
    })

    onApply({
      serialNumber: selectedSuggestions.has(SERIAL_NUMBER_KEY)
        ? extraction.identity.serial_number?.value
        : undefined,
      manufactureDate: selectedSuggestions.has(MANUFACTURE_DATE_KEY)
        ? extraction.identity.manufacture_date?.value
        : undefined,
      passportData,
    })
    setApplyNotice('Selected suggestions were copied to the form below.')
  }

  const rows = suggestionRows(extraction)

  return (
    <section className={styles.card} aria-labelledby="ai-import-heading">
      <div className={styles.heading}>
        <div>
          <h2 id="ai-import-heading">Fill from document with AI</h2>
          <p>
            Add a specification, manual, label image, or product photo. You will
            review all suggested values before saving them.
          </p>
        </div>
        <span className={styles.badge}>Gemini</span>
      </div>

      <div className={styles.choices}>
        <label className={styles.primaryChoice} htmlFor={uploadInputId}>
          Upload document or image
          <input
            ref={uploadInputRef}
            id={uploadInputId}
            type="file"
            accept={ACCEPTED_FILES}
            onChange={(event) => selectFile(event.target.files?.[0])}
          />
        </label>
        <label className={styles.secondaryChoice} htmlFor={cameraInputId}>
          Take a photo
          <input
            ref={cameraInputRef}
            id={cameraInputId}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(event) => selectFile(event.target.files?.[0])}
          />
        </label>
      </div>

      <p className={styles.helperText}>PDF, JPEG, PNG, WebP or HEIC · maximum 10 MB</p>
      {error && <p className={styles.error} role="alert">{error}</p>}

      {selectedFile && (
        <>
          <div className={styles.selection}>
            {previewUrl ? (
              <img
                className={styles.preview}
                src={previewUrl}
                alt="Selected source preview"
              />
            ) : (
              <div className={styles.documentIcon} aria-hidden="true">PDF</div>
            )}
            <div className={styles.fileDetails}>
              <strong>{selectedFile.name}</strong>
              <span>{formatFileSize(selectedFile.size)}</span>
            </div>
            <button
              className={styles.removeButton}
              type="button"
              onClick={clearSelection}
              disabled={isExtracting}
            >
              Remove
            </button>
          </div>
          <button
            className={styles.extractButton}
            type="button"
            onClick={extractSuggestions}
            disabled={isExtracting}
          >
            {isExtracting
              ? 'Extracting information…'
              : extraction
                ? 'Extract again'
                : 'Extract information'}
          </button>
        </>
      )}

      {extraction && (
        <div className={styles.review}>
          <div className={styles.reviewHeading}>
            <div>
              <h3>Review AI suggestions</h3>
              <p>Select the values you want to copy into the draft.</p>
            </div>
            <span>{rows.length} suggested</span>
          </div>

          {rows.length > 0 ? (
            <ul className={styles.suggestionList}>
              {rows.map((row) => (
                <li key={row.key} className={styles.suggestionItem}>
                  <label>
                    <input
                      type="checkbox"
                      checked={selectedSuggestions.has(row.key)}
                      onChange={() => toggleSuggestion(row.key)}
                    />
                    <span className={styles.suggestionContent}>
                      <span className={styles.suggestionHeading}>
                        <strong>{row.label}</strong>
                        <span className={`${styles.confidence} ${styles[row.confidence]}`}>
                          {row.confidence} confidence
                        </span>
                      </span>
                      <span className={styles.suggestionValue}>
                        {displayValue(row.value)}
                      </span>
                      {row.source && (
                        <span className={styles.suggestionSource}>
                          Source: {row.source}
                        </span>
                      )}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.noSuggestions}>
              No supported values were found in this source.
            </p>
          )}

          {extraction.missing_required_fields.length > 0 && (
            <p className={styles.warning}>
              Still missing required fields:{' '}
              {extraction.missing_required_fields.join(', ')}
            </p>
          )}
          {extraction.warnings.length > 0 && (
            <div className={styles.warning}>
              <strong>Extraction notes</strong>
              <ul>
                {extraction.warnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          {rows.length > 0 && (
            <>
              <button
                className={styles.applyButton}
                type="button"
                onClick={applySuggestions}
                disabled={selectedSuggestions.size === 0}
              >
                Apply selected suggestions
              </button>
              {applyNotice && (
                <p className={styles.success} role="status">{applyNotice}</p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}

export default AiDocumentUpload
