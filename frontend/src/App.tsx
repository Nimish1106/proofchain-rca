import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { DashboardPage } from './pages/DashboardPage';
import { InvestigationsListPage } from './pages/InvestigationsListPage';
import { InvestigationWorkspacePage } from './pages/InvestigationWorkspacePage';

export function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="topbar">
          <div className="topbar-brand">
            <ShieldCheck size={20} color="#38bdf8" />
            <span>ProofChain RCA</span>
          </div>
          <nav className="topbar-nav">
            <NavLink
              to="/"
              end
              className={({ isActive }) => `topbar-link ${isActive ? 'active' : ''}`}
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/investigations"
              className={({ isActive }) => `topbar-link ${isActive ? 'active' : ''}`}
            >
              Investigations
            </NavLink>
          </nav>
        </header>

        <main className="main-container">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/investigations" element={<InvestigationsListPage />} />
            <Route path="/investigations/:id" element={<InvestigationWorkspacePage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
