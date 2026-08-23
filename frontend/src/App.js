import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AppShell } from "@/components/layout/AppShell";
import DashboardPage from "@/pages/DashboardPage";
import RunsPage from "@/pages/RunsPage";
import GraphicsPage from "@/pages/GraphicsPage";
import CaptionsPage from "@/pages/CaptionsPage";
import PublishingPage from "@/pages/PublishingPage";
import HistoryPage from "@/pages/HistoryPage";
import SettingsPage from "@/pages/SettingsPage";

function App() {
  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/graphics" element={<GraphicsPage />} />
          <Route path="/captions" element={<CaptionsPage />} />
          <Route path="/publishing" element={<PublishingPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </AppShell>
      <Toaster position="bottom-right" richColors />
    </BrowserRouter>
  );
}

export default App;
