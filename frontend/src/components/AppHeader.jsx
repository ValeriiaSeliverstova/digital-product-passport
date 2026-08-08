import styles from './AppHeader.module.css'

const navigationItems = [
  { id: 'profile', label: 'Profile' },
  { id: 'templates', label: 'Templates' },
  { id: 'product-models', label: 'Product models' },
  { id: 'product-items', label: 'Product items' },
]

function AppHeader({ currentSection, currentUser, onLogout, onNavigate }) {
  return (
    <header className={styles.header}>
      <div className={styles.topRow}>
        <div className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">
            DPP
          </span>
          <span>Digital Product Passport</span>
        </div>

        <div className={styles.account}>
          <span className={styles.accountName}>
            {currentUser.organization?.name || currentUser.email}
          </span>
          <button className={styles.logoutButton} type="button" onClick={onLogout}>
            Logout
          </button>
        </div>
      </div>

      <nav className={styles.navigation} aria-label="Manufacturer navigation">
        {navigationItems.map((item) => (
          <button
            className={styles.navigationButton}
            type="button"
            aria-current={currentSection === item.id ? 'page' : undefined}
            key={item.id}
            onClick={() => onNavigate(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
    </header>
  )
}

export default AppHeader
