import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import TransactionsPage from './pages/TransactionsPage';
import BreakdownPage from './pages/BreakdownPage';
import SetupPage from './pages/SetupPage';
import CoveragePage from './pages/CoveragePage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/breakdown" element={<BreakdownPage />} />
          <Route path="/setup" element={<SetupPage />} />
          <Route path="/coverage" element={<CoveragePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
