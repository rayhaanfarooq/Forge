import { NavLink, Route, Routes } from "react-router-dom";
import BranchDetail from "./pages/BranchDetail";
import Dashboard from "./pages/Dashboard";
import RepositoryDetail from "./pages/RepositoryDetail";
import RepositoryList from "./pages/RepositoryList";
import TestEvents from "./pages/TestEvents";

function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-lockup">
          <div className="brand-mark">F</div>
          <div className="brand-copy">
            <h1>Forge</h1>
            <p className="app-subtitle">Developer workspace</p>
          </div>
        </div>

        <nav className="app-nav">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/repos">Repositories</NavLink>
          <NavLink to="/test-events">Test Events</NavLink>
        </nav>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/repos" element={<RepositoryList />} />
          <Route path="/repos/:repoId" element={<RepositoryDetail />} />
          <Route path="/branches/:branchId" element={<BranchDetail />} />
          <Route path="/test-events" element={<TestEvents />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
