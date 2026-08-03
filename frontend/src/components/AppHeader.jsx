import styles from './AppHeader.module.css'

function AppHeader({ currentUser, onLogout }) {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <span className={styles.brandMark} aria-hidden="true">
          DPP
        </span>
        <span>Digital Product Passport</span>
      </div>

      <div className={styles.account}>
        <span className={styles.email}>{currentUser.email}</span>
        <button className={styles.logoutButton} type="button" onClick={onLogout}>
          Logout
        </button>
      </div>
    </header>
  )
}

export default AppHeader
