import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../services/api";

/** Runs an async loader; exposes loading / error / data and a reload(). Ignores results from stale runs. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const run = useRef(0);
  const reload = useCallback(() => {
    const id = ++run.current;
    setLoading(true);
    setError(null);
    loader().then((d) => id === run.current && setData(d)).catch((e) => id === run.current && setError(errorMessage(e))).finally(() => id === run.current && setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { reload(); }, [reload]);
  return { data, error, loading, reload };
}
