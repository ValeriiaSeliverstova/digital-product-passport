import { useState } from 'react'

import styles from './NfcWriter.module.css'

function getNfcAvailability() {
  if (!window.isSecureContext) {
    return {
      isAvailable: false,
      message: 'NFC writing requires an HTTPS connection.',
    }
  }

  if (!('NDEFReader' in window)) {
    return {
      isAvailable: false,
      message:
        'NFC writing is not available in this browser. Use Chrome on an NFC-enabled Android phone.',
    }
  }

  return { isAvailable: true, message: '' }
}

function nfcErrorMessage(error) {
  if (error.name === 'NotAllowedError') {
    return 'NFC permission was denied. Allow NFC access and try again.'
  }

  if (error.name === 'NotSupportedError') {
    return 'This NFC tag does not support the NDEF format.'
  }

  if (error.name === 'NotReadableError' || error.name === 'NetworkError') {
    return 'The NFC tag could not be written. Make sure it is writable and try again.'
  }

  if (error.name === 'AbortError') {
    return 'NFC writing was cancelled.'
  }

  return 'The NFC tag could not be written. Keep it close to the phone and try again.'
}

function NfcWriter({ passportUrl }) {
  const [{ isAvailable, message: availabilityMessage }] = useState(
    getNfcAvailability,
  )
  const [writeState, setWriteState] = useState('idle')
  const [feedback, setFeedback] = useState('')

  async function writePassportUrl() {
    setWriteState('waiting')
    setFeedback('Hold the phone near a writable NFC tag.')

    try {
      const ndef = new window.NDEFReader()
      await ndef.write({
        records: [{ recordType: 'url', data: passportUrl }],
      })
      setWriteState('success')
      setFeedback('The public passport URL was written to the NFC tag.')
    } catch (error) {
      setWriteState('error')
      setFeedback(nfcErrorMessage(error))
    }
  }

  return (
    <section className={styles.card} aria-labelledby="nfc-heading">
      <div className={styles.heading}>
        <div>
          <h2 id="nfc-heading">NFC tag</h2>
          <p>Write a link to this public passport onto an NDEF-compatible tag.</p>
        </div>
        <button
          className={styles.writeButton}
          type="button"
          onClick={writePassportUrl}
          disabled={!isAvailable || writeState === 'waiting'}
        >
          {writeState === 'waiting' ? 'Waiting for NFC tag…' : 'Write URL to NFC'}
        </button>
      </div>

      <p className={styles.url}>{passportUrl}</p>
      <p className={styles.warning}>
        Use a blank or dedicated tag. Writing may replace its existing NDEF content.
      </p>

      {!isAvailable && (
        <p className={styles.unavailable} role="status">
          {availabilityMessage}
        </p>
      )}
      {feedback && (
        <p
          className={writeState === 'error' ? styles.error : styles.feedback}
          role={writeState === 'error' ? 'alert' : 'status'}
          aria-live="polite"
        >
          {feedback}
        </p>
      )}
    </section>
  )
}

export default NfcWriter
