import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";

// One place for state that several pages share:
// the tracked applications, which status moves are allowed, and toast messages.
const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [applications, setApplications] = useState([]);
  const [transitions, setTransitions] = useState({});
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const notify = useCallback((message, tone = "success") => {
    const id = nextId.current++;
    setToasts((list) => [...list, { id, message, tone }]);
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 3500);
  }, []);

  const refresh = useCallback(async () => {
    try {
      setApplications(await api.applications());
    } catch (error) {
      notify(error.message, "error");
    }
  }, [notify]);

  useEffect(() => {
    refresh();
    api.transitions().then(setTransitions).catch(() => {});
  }, [refresh]);

  const trackedIds = useMemo(() => new Set(applications.map((a) => a.id)), [applications]);

  const saveJob = useCallback(
    async (job) => {
      try {
        await api.saveJob(job);
        notify(`Saved “${job.title}” to your tracker`);
        await refresh();
      } catch (error) {
        notify(error.message, "error");
      }
    },
    [notify, refresh],
  );

  const moveTo = useCallback(
    async (id, status, note) => {
      try {
        await api.updateStatus(id, status, note);
        await refresh();
      } catch (error) {
        notify(error.message, "error");
      }
    },
    [notify, refresh],
  );

  const remove = useCallback(
    async (id) => {
      try {
        await api.remove(id);
        notify("Removed from tracker");
        await refresh();
      } catch (error) {
        notify(error.message, "error");
      }
    },
    [notify, refresh],
  );

  const value = { applications, transitions, trackedIds, toasts, notify, refresh, saveJob, moveTo, remove };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside <AppProvider>");
  return context;
}
