import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { SessionsPage } from './pages/SessionsPage';
import { TimelinePage } from './pages/TimelinePage';
import { ReplayPage } from './pages/ReplayPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { CostsPage } from './pages/CostsPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100 flex">
        <Sidebar />
        <main className="flex-1 ml-60 min-h-screen">
          <Routes>
            <Route path="/" element={<SessionsPage />} />
            <Route path="/timeline" element={<TimelinePage />} />
            <Route path="/replay" element={<ReplayPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/costs" element={<CostsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
