import { Routes, Route, Link, useNavigate } from 'react-router-dom';
import RepositoryList from './pages/RepositoryList';
import RepositoryDetail from './pages/RepositoryDetail';
import BranchDetail from './pages/BranchDetail';
import TestEvents from './pages/TestEvents';

function App() {
  return (
    <div className="container">
      <div className="header">
        <h1>Forge Dashboard</h1>
        <nav style={{ marginTop: '10px' }}>
          <Link to="/" style={{ marginRight: '15px', textDecoration: 'none', color: '#007bff' }}>
            Repositories
          </Link>
          <Link to="/test-events" style={{ textDecoration: 'none', color: '#007bff' }}>
            Test Events
          </Link>
        </nav>
      </div>

      <Routes>
        <Route path="/" element={<RepositoryList />} />
        <Route path="/repos/:repoId" element={<RepositoryDetail />} />
        <Route path="/branches/:branchId" element={<BranchDetail />} />
        <Route path="/test-events" element={<TestEvents />} />
      </Routes>
    </div>
  );
}

export default App;

