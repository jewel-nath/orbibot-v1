/**
 * PathContext - Simple path-based routing without React Router.
 * Syncs with browser URL (pushState / popstate) so Diagnostics and Dashboard are reachable.
 */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';

type PathContextValue = {
  path: string;
  navigate: (path: string) => void;
};

const PathContext = createContext<PathContextValue | null>(null);

export function PathProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState(() =>
    typeof window !== 'undefined' ? window.location.pathname : '/'
  );

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const navigate = useCallback((newPath: string) => {
    window.history.pushState({}, '', newPath);
    setPath(newPath);
  }, []);

  return (
    <PathContext.Provider value={{ path, navigate }}>
      {children}
    </PathContext.Provider>
  );
}

export function usePath() {
  const ctx = useContext(PathContext);
  if (!ctx) throw new Error('usePath must be used within PathProvider');
  return ctx;
}
