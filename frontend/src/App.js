import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Customers from "./pages/Customers";
import Calculator from "./pages/Calculator";
import Reminders from "./pages/Reminders";
import Settings from "./pages/Settings";
import Commissions from "./pages/Commissions";
import Vouchers from "./pages/Vouchers";
import PaymentPage from "./pages/PaymentPage";
import PaymentSuccess from "./pages/PaymentSuccess";
import PaymentCancel from "./pages/PaymentCancel";
import DistributorLogin from "./pages/DistributorLogin";
import DistributorDashboard from "./pages/DistributorDashboard";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { DistributorAuthProvider } from "./context/DistributorAuthContext";

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-pulse text-slate-600">Loading...</div>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Admin Routes */}
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/customers"
        element={
          <ProtectedRoute>
            <Customers />
          </ProtectedRoute>
        }
      />
      <Route
        path="/calculator"
        element={
          <ProtectedRoute>
            <Calculator />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reminders"
        element={
          <ProtectedRoute>
            <Reminders />
          </ProtectedRoute>
        }
      />
      <Route
        path="/commissions"
        element={
          <ProtectedRoute>
            <Commissions />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />
      <Route
        path="/vouchers"
        element={
          <ProtectedRoute>
            <Vouchers />
          </ProtectedRoute>
        }
      />
      
      {/* Public Payment Routes */}
      <Route path="/pay" element={<PaymentPage />} />
      <Route path="/payment/success" element={<PaymentSuccess />} />
      <Route path="/payment/cancel" element={<PaymentCancel />} />
      
      {/* Distributor Routes */}
      <Route
        path="/distributor/login"
        element={
          <DistributorAuthProvider>
            <DistributorLogin />
          </DistributorAuthProvider>
        }
      />
      <Route
        path="/distributor"
        element={
          <DistributorAuthProvider>
            <DistributorDashboard />
          </DistributorAuthProvider>
        }
      />
      
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
