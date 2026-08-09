import { useEffect, useRef, useState } from 'react'

import styles from './NfcWriter.module.css'

const VERIFICATION_TIMEOUT_MS = 20000

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

function verificationErrorMessage(error) {
  if (error.name === 'TimeoutError') {
    return 'Verification timed out. Tap Write and verify to try again.'
  }

  if (error.name === 'NotAllowedError') {
    return 'NFC permission was denied. Allow NFC access and try again.'
  }

  if (error.name === 'NotSupportedError') {
    return 'This NFC tag does not support the NDEF format.'
  }

  if (error.name === 'DataError') {
    return 'The tag was read, but it does not contain a passport URL.'
  }

  return 'The tag was written, but it could not be verified. Try the operation again.'
}

function readUrlRecord(message) {
  const urlRecord = [...message.records].find(
    (record) => record.recordType === 'url',
  )

  if (!urlRecord) {
    throw new DOMException('No URL record found', 'DataError')
  }

  return new TextDecoder().decode(urlRecord.data)
}

function urlsMatch(firstUrl, secondUrl) {
  try {
    return new URL(firstUrl).href === new URL(secondUrl).href
  } catch {
    return false
  }
}

function scanForUrl(ndef, abortController) {
  return new Promise((resolve, reject) => {
    let isFinished = false

    function cleanup() {
      isFinished = true
      window.clearTimeout(timeoutId)
      abortController.signal.removeEventListener('abort', handleAbort)
      ndef.onreading = null
      ndef.onreadingerror = null
    }

    function finish(callback, value, abortScan = false) {
      if (isFinished) return
      cleanup()
      if (abortScan) abortController.abort()
      callback(value)
    }

    function handleAbort() {
      finish(
        reject,
        abortController.signal.reason ||
          new DOMException('NFC verification cancelled', 'AbortError'),
      )
    }

    const timeoutId = window.setTimeout(() => {
      abortController.abort(
        new DOMException('NFC verification timed out', 'TimeoutError'),
      )
    }, VERIFICATION_TIMEOUT_MS)

    abortController.signal.addEventListener('abort', handleAbort)
    ndef.onreading = (event) => {
      try {
        finish(resolve, readUrlRecord(event.message), true)
      } catch (error) {
        finish(reject, error, true)
      }
    }
    ndef.onreadingerror = () => {
      finish(
        reject,
        new DOMException('NFC tag could not be read', 'NotReadableError'),
        true,
      )
    }

    ndef.scan({ signal: abortController.signal }).catch((error) => {
      finish(reject, error)
    })
  })
}

function NfcWriter({ passportUrl }) {
  const [{ isAvailable, message: availabilityMessage }] = useState(
    getNfcAvailability,
  )
  const [writeState, setWriteState] = useState('idle')
  const [feedback, setFeedback] = useState('')
  const verificationAbortRef = useRef(null)

  useEffect(
    () => () => {
      verificationAbortRef.current?.abort()
    },
  )

  async function writePassportUrl() {
    setWriteState('writing')
    setFeedback('Hold the phone near a writable NFC tag.')

    try {
      const ndef = new window.NDEFReader()
      await ndef.write({
        records: [{ recordType: 'url', data: passportUrl }],
      })

      setWriteState('verifying')
      setFeedback(
        'URL written. Move the phone away, then tap the same tag again to verify it.',
      )

      const abortController = new AbortController()
      verificationAbortRef.current = abortController

      try {
        const scannedUrl = await scanForUrl(ndef, abortController)

        if (urlsMatch(scannedUrl, passportUrl)) {
          setWriteState('verified')
          setFeedback('NFC tag verified. It contains the correct passport URL.')
        } else {
          setWriteState('mismatch')
          setFeedback('Verification failed: the tag contains a different URL.')
        }
      } catch (error) {
        if (error.name === 'AbortError') return
        setWriteState('verification-error')
        setFeedback(verificationErrorMessage(error))
      } finally {
        if (verificationAbortRef.current === abortController) {
          verificationAbortRef.current = null
        }
      }
    } catch (error) {
      setWriteState('write-error')
      setFeedback(nfcErrorMessage(error))
    }
  }

  const isBusy = writeState === 'writing' || writeState === 'verifying'
  const feedbackIsError = [
    'write-error',
    'verification-error',
    'mismatch',
  ].includes(writeState)
  const feedbackIsSuccess = writeState === 'verified'

  let buttonLabel = 'Write and verify NFC'
  if (writeState === 'writing') buttonLabel = 'Waiting for NFC tag…'
  if (writeState === 'verifying') buttonLabel = 'Waiting to verify…'
  if (writeState === 'verified') buttonLabel = 'Write another tag'

  return (
    <section className={styles.card} aria-labelledby="nfc-heading">
      <div className={styles.heading}>
        <div>
          <h2 id="nfc-heading">NFC tag</h2>
          <p>Write and verify this public passport URL on an NDEF-compatible tag.</p>
        </div>
        <button
          className={styles.writeButton}
          type="button"
          onClick={writePassportUrl}
          disabled={!isAvailable || isBusy}
        >
          {buttonLabel}
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
          className={
            feedbackIsError
              ? styles.error
              : feedbackIsSuccess
                ? styles.feedback
                : styles.inProgress
          }
          role={feedbackIsError ? 'alert' : 'status'}
          aria-live="polite"
        >
          {feedback}
        </p>
      )}
    </section>
  )
}

export default NfcWriter
