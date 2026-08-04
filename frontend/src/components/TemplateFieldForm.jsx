import { useState } from 'react'

import styles from './TemplateFieldForm.module.css'

const emptyField = {
  code: '',
  label: '',
  data_type: 'text',
  is_required: false,
  display_order: 0,
  access_level: 'public',
  validation_rules: {},
}

function initialFormValues(field) {
  const source = field || emptyField
  const rules = source.validation_rules || {}

  return {
    code: source.code,
    label: source.label,
    dataType: source.data_type,
    isRequired: source.is_required,
    displayOrder: String(source.display_order),
    accessLevel: source.access_level,
    minimum: rules.min === undefined ? '' : String(rules.min),
    maximum: rules.max === undefined ? '' : String(rules.max),
    minimumLength:
      rules.min_length === undefined ? '' : String(rules.min_length),
    maximumLength:
      rules.max_length === undefined ? '' : String(rules.max_length),
    allowedValues: Array.isArray(rules.allowed_values)
      ? rules.allowed_values.join('\n')
      : '',
  }
}

/**
 * Collect one complete field definition. The backend uses PUT for field edits,
 * so this form always submits every property instead of only changed values.
 */
function TemplateFieldForm({ initialField, isSaving, onSave, onCancel }) {
  const [values, setValues] = useState(() => initialFormValues(initialField))

  function updateValue(name, value) {
    setValues((current) => ({ ...current, [name]: value }))
  }

  function buildValidationRules() {
    if (values.dataType === 'text') {
      const rules = {}
      if (values.minimumLength !== '') {
        rules.min_length = Number(values.minimumLength)
      }
      if (values.maximumLength !== '') {
        rules.max_length = Number(values.maximumLength)
      }

      const allowedValues = values.allowedValues
        .split('\n')
        .map((value) => value.trim())
        .filter(Boolean)
      if (allowedValues.length > 0) {
        rules.allowed_values = allowedValues
      }
      return rules
    }

    if (['integer', 'decimal'].includes(values.dataType)) {
      const rules = {}
      if (values.minimum !== '') {
        rules.min = Number(values.minimum)
      }
      if (values.maximum !== '') {
        rules.max = Number(values.maximum)
      }
      return rules
    }

    if (values.dataType === 'date') {
      const rules = {}
      if (values.minimum !== '') {
        rules.min = values.minimum
      }
      if (values.maximum !== '') {
        rules.max = values.maximum
      }
      return rules
    }

    return {}
  }

  function handleSubmit(event) {
    event.preventDefault()
    onSave({
      code: values.code,
      label: values.label,
      data_type: values.dataType,
      is_required: values.isRequired,
      display_order: Number(values.displayOrder),
      access_level: values.accessLevel,
      validation_rules: buildValidationRules(),
    })
  }

  const numberStep = values.dataType === 'integer' ? '1' : 'any'

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.twoColumns}>
        <div className={styles.field}>
          <label htmlFor="field-label">Field label</label>
          <input
            id="field-label"
            maxLength="255"
            value={values.label}
            onChange={(event) => updateValue('label', event.target.value)}
            required
          />
          <p className={styles.helperText}>The readable name shown to users.</p>
        </div>

        <div className={styles.field}>
          <label htmlFor="field-code">Field code</label>
          <input
            id="field-code"
            maxLength="100"
            pattern="[a-z][a-z0-9_]*"
            placeholder="example_field"
            value={values.code}
            onChange={(event) => updateValue('code', event.target.value)}
            required
          />
          <p className={styles.helperText}>
            Lowercase letters, numbers, and underscores.
          </p>
        </div>
      </div>

      <div className={styles.twoColumns}>
        <div className={styles.field}>
          <label htmlFor="field-type">Data type</label>
          <select
            id="field-type"
            value={values.dataType}
            onChange={(event) => updateValue('dataType', event.target.value)}
          >
            <option value="text">Text</option>
            <option value="integer">Integer</option>
            <option value="decimal">Decimal number</option>
            <option value="boolean">Yes / No</option>
            <option value="date">Date</option>
          </select>
        </div>

        <div className={styles.field}>
          <label htmlFor="field-access">Access level</label>
          <select
            id="field-access"
            value={values.accessLevel}
            onChange={(event) => updateValue('accessLevel', event.target.value)}
          >
            <option value="public">Public</option>
            <option value="manufacturer">Manufacturer only</option>
          </select>
        </div>
      </div>

      <div className={styles.twoColumns}>
        <div className={styles.field}>
          <label htmlFor="field-order">Display order</label>
          <input
            id="field-order"
            type="number"
            min="0"
            max="1000000"
            step="1"
            value={values.displayOrder}
            onChange={(event) => updateValue('displayOrder', event.target.value)}
            required
          />
        </div>

        <label className={styles.checkbox}>
          <input
            type="checkbox"
            checked={values.isRequired}
            onChange={(event) => updateValue('isRequired', event.target.checked)}
          />
          Required field
        </label>
      </div>

      {values.dataType === 'text' && (
        <fieldset className={styles.rules}>
          <legend>Text validation (optional)</legend>
          <div className={styles.twoColumns}>
            <div className={styles.field}>
              <label htmlFor="field-min-length">Minimum length</label>
              <input
                id="field-min-length"
                type="number"
                min="0"
                max="10000"
                step="1"
                value={values.minimumLength}
                onChange={(event) =>
                  updateValue('minimumLength', event.target.value)
                }
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="field-max-length">Maximum length</label>
              <input
                id="field-max-length"
                type="number"
                min="0"
                max="10000"
                step="1"
                value={values.maximumLength}
                onChange={(event) =>
                  updateValue('maximumLength', event.target.value)
                }
              />
            </div>
          </div>
          <div className={styles.field}>
            <label htmlFor="field-values">Allowed values</label>
            <textarea
              id="field-values"
              rows="3"
              value={values.allowedValues}
              onChange={(event) =>
                updateValue('allowedValues', event.target.value)
              }
            />
            <p className={styles.helperText}>Optional: enter one value per line.</p>
          </div>
        </fieldset>
      )}

      {['integer', 'decimal'].includes(values.dataType) && (
        <fieldset className={styles.rules}>
          <legend>Number validation (optional)</legend>
          <div className={styles.twoColumns}>
            <div className={styles.field}>
              <label htmlFor="field-min-number">Minimum</label>
              <input
                id="field-min-number"
                type="number"
                step={numberStep}
                value={values.minimum}
                onChange={(event) => updateValue('minimum', event.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="field-max-number">Maximum</label>
              <input
                id="field-max-number"
                type="number"
                step={numberStep}
                value={values.maximum}
                onChange={(event) => updateValue('maximum', event.target.value)}
              />
            </div>
          </div>
        </fieldset>
      )}

      {values.dataType === 'date' && (
        <fieldset className={styles.rules}>
          <legend>Date validation (optional)</legend>
          <div className={styles.twoColumns}>
            <div className={styles.field}>
              <label htmlFor="field-min-date">Earliest date</label>
              <input
                id="field-min-date"
                type="date"
                value={values.minimum}
                onChange={(event) => updateValue('minimum', event.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="field-max-date">Latest date</label>
              <input
                id="field-max-date"
                type="date"
                value={values.maximum}
                onChange={(event) => updateValue('maximum', event.target.value)}
              />
            </div>
          </div>
        </fieldset>
      )}

      <div className={styles.actions}>
        <button
          className={styles.cancelButton}
          type="button"
          onClick={onCancel}
          disabled={isSaving}
        >
          Cancel
        </button>
        <button className={styles.saveButton} type="submit" disabled={isSaving}>
          {isSaving ? 'Saving…' : initialField ? 'Save field' : 'Add field'}
        </button>
      </div>
    </form>
  )
}

export default TemplateFieldForm
