import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './lib/theme';
import { Sidebar } from './components/Sidebar';
import { SessionsPage } from './pages/SessionsPage';
import { TopologyPage } from './pages/TopologyPage';
import { TimelinePage } from './pages/TimelinePage';
import { ReplayPage } from './pages/ReplayPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { CostsPage } from './pages/CostsPage';

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <div className="flex min-h-screen" style={{ background: 'var(--bg)' }}>
          <Sidebar />
          <main className="flex-1 ml-56 min-h-screen overflow-x-hidden">
            <Routes>
            <Route path="/" element={<SessionsPage />} />
            <Route path="/topology" element={<TopologyPage />} />
            <Route path="/timeline" element={<TimelinePage />} />
              <Route path="/replay" element={<ReplayPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/costs" element={<CostsPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </ThemeProvider>
  );
}
