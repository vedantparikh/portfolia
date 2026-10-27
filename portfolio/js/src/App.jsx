import { Toaster } from "react-hot-toast";
import { BrowserRouter as Router } from "react-router";
import { AuthProvider } from "./contexts/AuthContext";
import AppRoutes from "./app/router";

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <AppRoutes />
        </div>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: "#1e293b",
              color: "#f1f5f9",
              border: "1px solid #475569",
            },
            success: {
              iconTheme: {
                primary: "#22c55e",
                secondary: "#f1f5f9",
              },
            },
            error: {
              iconTheme: {
                primary: "#ef4444",
                secondary: "#f1f5f9",
              },
            },
          }}
        />
      </Router>
    </AuthProvider>
  );
}

export default App;
