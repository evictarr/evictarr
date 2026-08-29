import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  FiBell,
  FiChevronDown,
  FiClock,
  FiFolder,
  FiHome,
  FiInbox,
  FiList,
  FiLock,
  FiLogOut,
  FiSettings,
  FiSliders,
  FiUser,
} from 'react-icons/fi'
import { useAuth } from '../api/AuthContext'
import { VersionBadge } from './VersionBadge'
import styles from './Layout.module.css'

export function Layout() {
  const { session, authMethod, logout } = useAuth()
  const location = useLocation()
  const inSettings = location.pathname.startsWith('/settings') || location.pathname.startsWith('/orphaned-files')

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <img src="/logo.svg" alt="" className={styles.logo} />
          Evictarr
        </div>
        <nav className={styles.nav}>
          <NavLink to="/" end className={({ isActive }) => (isActive ? styles.navLinkActive : styles.navLink)}>
            <FiHome /> Dashboard
          </NavLink>
          <NavLink to="/rules" className={({ isActive }) => (isActive ? styles.navLinkActive : styles.navLink)}>
            <FiList /> Rules
          </NavLink>
          <NavLink
            to="/pending-deletions"
            className={({ isActive }) => (isActive ? styles.navLinkActive : styles.navLink)}
          >
            <FiInbox /> Pending
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => (isActive ? styles.navLinkActive : styles.navLink)}>
            <FiClock /> History
          </NavLink>
          <div className={styles.dropdown}>
            <button type="button" className={inSettings ? styles.navLinkActive : styles.navLink}>
              <FiSettings /> Settings <FiChevronDown />
            </button>
            <div className={styles.dropdownMenu}>
              <NavLink to="/settings/integrations" className={styles.dropdownItem}>
                <FiSettings /> Integrations
              </NavLink>
              <NavLink to="/settings/notifications" className={styles.dropdownItem}>
                <FiBell /> Notifications
              </NavLink>
              <NavLink to="/settings/general" className={styles.dropdownItem}>
                <FiSliders /> General
              </NavLink>
              <NavLink to="/settings/security" className={styles.dropdownItem}>
                <FiLock /> Security
              </NavLink>
              <NavLink to="/orphaned-files" className={styles.dropdownItem}>
                <FiFolder /> Orphaned Files
              </NavLink>
            </div>
          </div>
          {authMethod === 'basic' && (
            <NavLink to="/profile" className={({ isActive }) => (isActive ? styles.navLinkActive : styles.navLink)}>
              <FiUser /> My Profile
            </NavLink>
          )}
        </nav>
        <div className={styles.userArea}>
          <VersionBadge />
          {authMethod === 'basic' && (
            <>
              <span className={styles.username}>{session?.username}</span>
              <button className={styles.logoutButton} onClick={() => logout()} title="Log out">
                <FiLogOut />
              </button>
            </>
          )}
        </div>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  )
}
