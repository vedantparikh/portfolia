// The access token lives only in memory. The refresh token is an httpOnly
// cookie that JavaScript never sees; a reload gets a new access token from it.
type Listener = () => void;
const cleared = new Set<Listener>();
let access: string | null = null;

for (const legacy of ["access_token", "refresh_token"]) {
  localStorage.removeItem(legacy);
}

export const tokenStore = {
  getAccess(): string | null {
    return access;
  },
  setAccess(token: string): void {
    access = token;
  },
  clear(): void {
    access = null;
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
