import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "./stores/auth";

// Pages
import Login      from "./pages/Login";
import Dashboard  from "./pages/Dashboard";
import Stock      from "./pages/Stock";
import Clients    from "./pages/Clients";
import Commandes  from "./pages/Commandes";
import Calendrier from "./pages/Calendrier";
import Analytics  from "./pages/Analytics";
import Parametres from "./pages/Parametres";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

function PrivateRoute({ children }) {
  const token = useAuthStore((s) => s.token);
  return token ? children : <Navigate to="/login" replace />;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="/stock" element={<PrivateRoute><Stock /></PrivateRoute>} />
          <Route path="/clients" element={<PrivateRoute><Clients /></PrivateRoute>} />
          <Route path="/commandes" element={<PrivateRoute><Commandes /></PrivateRoute>} />
          <Route path="/calendrier" element={<PrivateRoute><Calendrier /></PrivateRoute>} />
          <Route path="/analytics" element={<PrivateRoute><Analytics /></PrivateRoute>} />
          <Route path="/parametres" element={<PrivateRoute><Parametres /></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
