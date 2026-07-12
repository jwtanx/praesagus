import { NavLink, Outlet } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/trends', label: 'Trends' },
  { to: '/platforms', label: 'Platforms' },
  { to: '/research', label: 'Research' },
  { to: '/pipeline', label: 'Pipeline' },
  { to: '/settings', label: 'Settings' },
];

export default function Layout() {
  return (
    <div className="layout-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>Praesagus</h1>
          <p>Market intelligence workspace</p>
        </div>
        <nav className="nav-menu">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content-area">
        <Outlet />
      </main>
    </div>
  );
}
