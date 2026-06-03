import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../stores/authStore";

export function ProtectedRoute() {
  const status = useAuth((s) => s.status);
  if (status !== "authenticated") return <Navigate to="/login" replace />;
  return <Outlet />;
}
