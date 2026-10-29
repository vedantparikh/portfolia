import { Menu, Settings as SettingsIcon } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router";

import { useShell } from "../../app/chrome";
import { useAuth } from "../../contexts/AuthContext";
import useIsMobile from "../../hooks/useIsMobile";
import { apiErrorMessage } from "../../shared/api/client";
import { authAPI } from "../auth/api";

const PROFILE_FIELDS = [
  ["first_name", "First name"],
  ["last_name", "Last name"],
  ["phone", "Phone"],
  ["country", "Country"],
  ["timezone", "Time zone"],
  ["currency_preference", "Preferred currency"],
];

const Section = ({ title, children }) => (
  <section className="card p-6">
    <h2 className="text-lg font-semibold text-gray-100 mb-4">{title}</h2>
    {children}
  </section>
);

const Field = ({ id, label, ...input }) => (
  <label htmlFor={id} className="flex flex-col gap-1 text-sm text-gray-400">
    {label}
    <input id={id} className="input-field" {...input} />
  </label>
);

export default function Settings() {
  const { user, profile, refreshUser, logout } = useAuth();
  const { openSidebar } = useShell();
  const isMobile = useIsMobile();
  const navigate = useNavigate();
  const [details, setDetails] = useState({});
  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [closePassword, setClosePassword] = useState("");
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    if (profile) {
      setDetails(
        Object.fromEntries(PROFILE_FIELDS.map(([key]) => [key, profile[key] || ""])),
      );
    }
  }, [profile]);

  const run = async (name, action, success) => {
    setBusy(name);
    try {
      await action();
      if (success) toast.success(success);
      return true;
    } catch (error) {
      toast.error(apiErrorMessage(error, "That did not work"));
      return false;
    } finally {
      setBusy(null);
    }
  };

  const saveProfile = (event) => {
    event.preventDefault();
    const changed = Object.fromEntries(
      PROFILE_FIELDS.map(([key]) => [key, details[key]?.trim() || null]).filter(
        ([key, value]) => value !== (profile?.[key] || null),
      ),
    );
    if (changed.currency_preference) {
      changed.currency_preference = changed.currency_preference.toUpperCase();
    }
    run("profile", async () => {
      await authAPI.updateProfile(changed);
      await refreshUser();
    }, "Profile saved");
  };

  const changePassword = async (event) => {
    event.preventDefault();
    if (passwords.next !== passwords.confirm) {
      toast.error("The new passwords do not match");
      return;
    }
    const done = await run(
      "password",
      () =>
        authAPI.changePassword({
          current_password: passwords.current,
          new_password: passwords.next,
          confirm_new_password: passwords.confirm,
        }),
      "Password changed. Other devices are signed out.",
    );
    if (done) setPasswords({ current: "", next: "", confirm: "" });
  };

  const closeAccount = async (event) => {
    event.preventDefault();
    if (!window.confirm("Close your account? You will be signed out and cannot sign in again.")) {
      return;
    }
    const done = await run("close", () => authAPI.deleteAccount(closePassword));
    if (done) {
      await logout();
      navigate("/login", { replace: true });
    }
  };

  return (
    <div className="min-h-screen gradient-bg">
      <header className="bg-dark-900/80 backdrop-blur-sm border-b border-dark-700 px-6 py-4">
        <div className="flex items-center space-x-4">
          {isMobile && (
            <button onClick={openSidebar} aria-label="Open menu" className="text-gray-400 hover:text-gray-200">
              <Menu className="w-6 h-6" />
            </button>
          )}
          <SettingsIcon className="w-8 h-8 text-primary-400" />
          <div>
            <h1 className="text-3xl font-bold text-gray-100">Settings</h1>
            <p className="text-sm text-gray-400">
              Signed in as {user?.username} ({user?.email})
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto p-6 space-y-6">
        <Section title="Profile">
          <form onSubmit={saveProfile} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {PROFILE_FIELDS.map(([key, label]) => (
              <Field
                key={key}
                id={`profile-${key}`}
                label={label}
                value={details[key] ?? ""}
                maxLength={key === "currency_preference" ? 3 : 100}
                onChange={(e) => setDetails((prev) => ({ ...prev, [key]: e.target.value }))}
              />
            ))}
            <div className="sm:col-span-2">
              <button type="submit" className="btn-primary" disabled={busy === "profile"}>
                Save profile
              </button>
            </div>
          </form>
        </Section>

        <Section title="Password">
          <form onSubmit={changePassword} className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Field
              id="password-current"
              label="Current password"
              type="password"
              autoComplete="current-password"
              value={passwords.current}
              onChange={(e) => setPasswords((prev) => ({ ...prev, current: e.target.value }))}
              required
            />
            <Field
              id="password-new"
              label="New password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={passwords.next}
              onChange={(e) => setPasswords((prev) => ({ ...prev, next: e.target.value }))}
              required
            />
            <Field
              id="password-confirm"
              label="Repeat new password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={passwords.confirm}
              onChange={(e) => setPasswords((prev) => ({ ...prev, confirm: e.target.value }))}
              required
            />
            <p className="sm:col-span-3 text-xs text-gray-500">
              At least 8 characters with upper and lower case, a digit and a symbol. Other devices are signed out.
            </p>
            <div className="sm:col-span-3">
              <button type="submit" className="btn-primary" disabled={busy === "password"}>
                Change password
              </button>
            </div>
          </form>
        </Section>

        <Section title="Close account">
          <form onSubmit={closeAccount} className="flex flex-wrap items-end gap-4">
            <p className="w-full text-sm text-gray-400">
              Deactivates the account and signs out every device. Your data stays in the database.
            </p>
            <Field
              id="close-password"
              label="Password"
              type="password"
              autoComplete="current-password"
              value={closePassword}
              onChange={(e) => setClosePassword(e.target.value)}
              required
            />
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-danger-600 hover:bg-danger-700 text-white disabled:opacity-50"
              disabled={busy === "close"}
            >
              Close account
            </button>
          </form>
        </Section>
      </main>
    </div>
  );
}
