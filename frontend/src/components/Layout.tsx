import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, Upload, Users, Receipt, PieChart, CalendarCheck } from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/breakdown', icon: PieChart, label: 'Breakdown' },
  { to: '/upload', icon: Upload, label: 'Upload' },
  { to: '/transactions', icon: Receipt, label: 'Transactions' },
  { to: '/coverage', icon: CalendarCheck, label: 'Coverage' },
  { to: '/setup', icon: Users, label: 'Setup' },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-slate-50">
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <h1 className="text-xl font-bold text-indigo-600 flex items-center gap-2">
            <span className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">$</span>
            Finance Tracker
          </h1>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-200 text-xs text-slate-400">
          All data stored locally
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
