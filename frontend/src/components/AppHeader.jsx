import styles from './AppHeader.module.css'
import { organizationLogoUrl } from '../services/organizations.js'

const administratorNavigation = [
  { id: 'profile', label: 'Profile' },
  { id: 'templates', label: 'Templates' },
  { id: 'product-models', label: 'Product models' },
  { id: 'product-items', label: 'Product items' },
  { id: 'team-members', label: 'Team members' },
]

const technicianNavigation = [
  { id: 'product-items', label: 'Product items' },
  { id: 'profile', label: 'Account' },
]

function AppHeader({ currentSection, currentUser, onLogout, onNavigate }) {
  const logoUrl = organizationLogoUrl(currentUser.organization)
  const isTechnician = currentUser.role.name === 'service_technician'
  const navigationItems = isTechnician
    ? technicianNavigation
    : administratorNavigation

  return (
    <header className={styles.header}>
      <div className={styles.topRow}>
        <div className={styles.brand}>
          {logoUrl ? (
            <img
              className={styles.brandLogo}
              src={logoUrl}
              alt={`${currentUser.organization.name} logo`}
            />
          ) : (
            <span className={styles.brandMark} aria-hidden="true">DPP</span>
          )}
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

      <nav className={styles.navigation} aria-label="Organization navigation">
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
