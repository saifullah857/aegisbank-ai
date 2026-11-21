import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, tokenStore } from "../services/api";
import type { Role } from "../types";

interface AuthUser { username: string; role: Role }
interface AuthCtx { user: AuthUser | null; login: (u: string, p: string) => Promise<void>; logout: () => void }
const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);

function parse(token: string | null): AuthUser | null {
  if (!token) return null;
  try {
    const p = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (p.exp && p.exp * 1000 < Date.now()) return null;
    return { username: p.sub, role: p.role };
  } catch { return null; }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => parse(tokenStore.get()));
  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);
  useEffect(() => { window.addEventListener("aegis:unauthorized", logout); return () => window.removeEventListener("aegis:unauthorized", logout); }, [logout]);
  const login = useCallback(async (u: string, p: string) => {
    const r = await api.login(u, p);
    tokenStore.set(r.access_token);
    setUser(parse(r.access_token) ?? { username: u, role: r.role as Role });
  }, []);
  const value = useMemo(() => ({ user, login, logout }), [user, login, logout]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
export const useAuth = () => useContext(Ctx);
