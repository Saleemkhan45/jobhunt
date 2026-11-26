import { NavLink, Link } from "react-router-dom";
import { Search, LayoutGrid, BookOpen } from "lucide-react";
import { useApp } from "../context/AppContext";

const linkClass = ({ isActive }) =>
  `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
    isActive ? "bg-white/10 text-white" : "text-slate-300 hover:text-white hover:bg-white/5"
  }`;

export default function Navbar() {
  const { applications } = useApp();
  return (
    <header className="bg-ink text-white">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-mint/15 text-mint">
            <Search size={18} strokeWidth={2.5} />
          </span>
          <span className="font-display text-xl font-bold tracking-tight">JobHunt</span>
        </Link>
        <div className="flex items-center gap-1">
          <NavLink to="/" end className={linkClass}>
            <Search size={16} /> <span className="hidden sm:inline">Search</span>
          </NavLink>
          <NavLink to="/tracker" className={linkClass}>
            <LayoutGrid size={16} /> <span className="hidden sm:inline">Tracker</span>
            {applications.length > 0 && (
              <span className="rounded-full bg-mint px-2 py-0.5 text-xs font-semibold text-ink">
                {applications.length}
              </span>
            )}
          </NavLink>
          <a href="/docs" target="_blank" rel="noreferrer" className={linkClass({ isActive: false })}>
            <BookOpen size={16} /> <span className="hidden sm:inline">API docs</span>
          </a>
        </div>
      </nav>
    </header>
  );
}
