import { Routes, Route, Link, useLocation } from 'react-router-dom';
import RepositoryList from './pages/RepositoryList';
import RepositoryDetail from './pages/RepositoryDetail';
import BranchDetail from './pages/BranchDetail';
import TestEvents from './pages/TestEvents';
import Dashboard from './pages/Dashboard';

function App() {
  const location = useLocation();
  
  return (
    <div className="container">
      <div className="header">
        <h1>⚡ Forge Dashboard</h1>
        <nav>
          <Link 
            to="/" 
            className={location.pathname === '/' ? 'active' : ''}
          >
            Dashboard
          </Link>
          <Link 
            to="/repos" 
            className={location.pathname.startsWith('/repos') ? 'active' : ''}
          >
            Repositories
          </Link>
          <Link 
            to="/test-events" 
            className={location.pathname === '/test-events' ? 'active' : ''}
          >
            Test Events
          </Link>
        </nav>
      </div>

      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/repos" element={<RepositoryList />} />
        <Route path="/repos/:repoId" element={<RepositoryDetail />} />
        <Route path="/branches/:branchId" element={<BranchDetail />} />
        <Route path="/test-events" element={<TestEvents />} />
      </Routes>
    </div>
  );
}

export default App;

