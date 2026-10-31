import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Trends from './pages/Trends';
import Financial from './pages/Financial';
import Platforms from './pages/Platforms';
import Research from './pages/Research';
import Pipeline from './pages/Pipeline';
import Settings from './pages/Settings';
import Seasonality from './pages/Seasonality';

function App() {
  const pagesBuild = import.meta.env.MODE === 'pages';
  return (
    <BrowserRouter basename={pagesBuild ? '/praesagus/seasonality' : undefined}>
      {pagesBuild ? <Routes><Route path="/" element={<main className="seasonality-static"><Seasonality /></main>} /></Routes> : (
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="trends" element={<Trends />} />
            <Route path="seasonality" element={<Seasonality />} />
            <Route path="financial" element={<Financial />} />
            <Route path="platforms" element={<Platforms />} />
            <Route path="research" element={<Research />} />
            <Route path="pipeline" element={<Pipeline />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      )}
    </BrowserRouter>
  );
}

export default App;
