import { useCallback, useEffect, useState } from "react";

/**
 * Polls `fetcher` on mount and while the returned `state` is "running".
 * Returns the latest status object and a `refresh` function to force-fetch.
 */
export function usePollingStatus(fetcher, { intervalMs = 4000 } = {}) {
  const [status, setStatus] = useState({ state: "idle" });

  const refresh = useCallback(async () => {
    try {
      const res = await fetcher();
      setStatus(res.data);
      return res.data;
    } catch {
      // keep previous status on error
    }
  }, [fetcher]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (status.state !== "running") return;
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [status.state, refresh, intervalMs]);

  return { status, refresh };
}
