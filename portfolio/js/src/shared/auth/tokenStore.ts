const ACCESS = "access_token";
const REFRESH = "refresh_token";

type Listener = () => void;
const cleared = new Set<Listener>();

export const tokenStore = {
  getAccess(): string | null {
    return localStorage.getItem(ACCESS);
  },
  getRefresh(): string | null {
    return localStorage.getItem(REFRESH);
  },
  set(access: string, refresh: string): void {
    localStorage.setItem(ACCESS, access);
    localStorage.setItem(REFRESH, refresh);
  },
  clear(): void {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
    localStorage.removeItem("user");
    localStorage.removeItem("profile");
    cleared.forEach((listener) => listener());
  },
};

export function onSessionCleared(listener: Listener): () => void {
  cleared.add(listener);
  return () => {
    cleared.delete(listener);
  };
}
