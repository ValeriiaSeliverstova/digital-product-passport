import { useState } from 'react'

import { ApiError } from '../services/api.js'
import {
  replyToSupportTicket,
  trackSupportTicket,
} from '../services/supportTickets.js'
import styles from './PublicSupportTicketPage.module.css'

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'long',
  timeStyle: 'short',
})

function formatDateTime(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : dateTimeFormatter.format(date)
}

function PublicSupportTicketPage({ ticketId }) {
  const [ticketNumber, setTicketNumber] = useState(ticketId || '')
  const [trackingCode, setTrackingCode] = useState('')
  const [ticket, setTicket] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [reply, setReply] = useState('')
  const [isSendingReply, setIsSendingReply] = useState(false)
  const [replyError, setReplyError] = useState('')

  async function loadTicketStatus() {
    setIsLoading(true)
    setError('')

    try {
      setTicket(
        await trackSupportTicket(ticketNumber.trim(), trackingCode.trim()),
      )
    } catch (requestError) {
      setTicket(null)
      setError(
        requestError instanceof ApiError && requestError.status === 404
          ? 'The ticket number or tracking code is incorrect.'
          : 'The ticket status could not be loaded. Please try again.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    loadTicketStatus()
  }

  async function handleReply(event) {
    event.preventDefault()
    setIsSendingReply(true)
    setReplyError('')

    try {
      await replyToSupportTicket(
        ticketNumber.trim(),
        trackingCode.trim(),
        reply.trim(),
      )
      setReply('')
      await loadTicketStatus()
    } catch {
      setReplyError('Your reply could not be sent. Please try again.')
    } finally {
      setIsSendingReply(false)
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">DPP</span>
          <span>Digital Product Passport</span>
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.card}>
          <h1>
            {ticketId ? `Track support ticket #${ticketId}` : 'Track a support ticket'}
          </h1>
          <p className={styles.introduction}>
            Enter the ticket details sent to your email address.
          </p>

          <form className={styles.form} onSubmit={handleSubmit}>
            {!ticketId && (
              <>
                <label htmlFor="ticket-number">Ticket number</label>
                <input
                  id="ticket-number"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]+"
                  maxLength={10}
                  placeholder="For example, 991"
                  value={ticketNumber}
                  onChange={(event) => setTicketNumber(event.target.value)}
                  required
                />
              </>
            )}
            <label htmlFor="tracking-code">Tracking code</label>
            <input
              id="tracking-code"
              autoComplete="one-time-code"
              minLength={16}
              maxLength={64}
              value={trackingCode}
              onChange={(event) => setTrackingCode(event.target.value)}
              required
            />
            {error && <p className={styles.error} role="alert">{error}</p>}
            <button type="submit" disabled={isLoading}>
              {isLoading ? 'Loading…' : 'View ticket status'}
            </button>
          </form>

          {ticket && (
            <div className={styles.result} role="status">
              <div className={styles.resultHeading}>
                <h2>{ticket.subject}</h2>
                <span>{ticket.status}</span>
              </div>
              <dl>
                <div>
                  <dt>Submitted</dt>
                  <dd>{formatDateTime(ticket.submitted_at)}</dd>
                </div>
                {ticket.updated_at && (
                  <div>
                    <dt>Last updated</dt>
                    <dd>{formatDateTime(ticket.updated_at)}</dd>
                  </div>
                )}
              </dl>
              <button
                className={styles.refreshButton}
                type="button"
                onClick={loadTicketStatus}
                disabled={isLoading}
              >
                {isLoading ? 'Refreshing…' : 'Refresh status'}
              </button>


              <section className={styles.conversation}>
                <h3>Conversation</h3>
                {ticket.comments.length === 0 ? (
                  <p className={styles.emptyConversation}>
                    No replies yet. Support comments added in Azure DevOps will
                    appear here after refresh.
                  </p>
                ) : (
                  <ol className={styles.commentList}>
                    {ticket.comments.map((comment) => (
                      <li
                        className={comment.author === 'Customer'
                          ? styles.customerComment
                          : styles.supportComment}
                        key={`${comment.id}-${comment.created_at}`}
                      >
                        <div className={styles.commentMeta}>
                          <strong>{comment.author}</strong>
                          <time dateTime={comment.created_at}>
                            {formatDateTime(comment.created_at)}
                          </time>
                        </div>
                        <p>{comment.message}</p>
                      </li>
                    ))}
                  </ol>
                )}

                <form className={styles.replyForm} onSubmit={handleReply}>
                  <label htmlFor="ticket-reply">Reply to support</label>
                  <textarea
                    id="ticket-reply"
                    maxLength={2000}
                    rows={4}
                    value={reply}
                    onChange={(event) => setReply(event.target.value)}
                    required
                  />
                  {replyError && (
                    <p className={styles.error} role="alert">{replyError}</p>
                  )}
                  <button type="submit" disabled={isSendingReply}>
                    {isSendingReply ? 'Sending…' : 'Send reply'}
                  </button>
                </form>
              </section>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default PublicSupportTicketPage
