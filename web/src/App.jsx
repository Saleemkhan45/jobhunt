import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Toasts from "./components/Toasts";
import SearchPage from "./pages/SearchPage";
import JobPage from "./pages/JobPage";
import TrackerPage from "./pages/TrackerPage";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/jobs/:id" element={<JobPage />} />
          <Route path="/tracker" element={<TrackerPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="border-t border-line py-6 text-center text-sm text-muted">
        JobHunt · Data from{" "}
        <a className="underline hover:text-teal" href="https://www.arbeitnow.com" target="_blank" rel="noreferrer">Arbeitnow</a>,{" "}
        <a className="underline hover:text-teal" href="https://remotive.com" target="_blank" rel="noreferrer">Remotive</a> and{" "}
        <a className="underline hover:text-teal" href="https://himalayas.app" target="_blank" rel="noreferrer">Himalayas</a>
      </footer>
      <Toasts />
    </div>
  );
}
