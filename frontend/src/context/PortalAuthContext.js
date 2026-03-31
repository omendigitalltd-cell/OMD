import { createContext, useContext, useState, useEffect, useCallback } from "react";

const PortalAuthContext = createContext();

export function PortalAuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("portal_token"));
  const [customerId, setCustomerId] = useState(localStorage.getItem("portal_customer_id"));

  useEffect(() => {
    if (token) {
      localStorage.setItem("portal_token", token);
    } else {
      localStorage.removeItem("portal_token");
    }
  }, [token]);

  useEffect(() => {
    if (customerId) {
      localStorage.setItem("portal_customer_id", customerId);
    } else {
      localStorage.removeItem("portal_customer_id");
    }
  }, [customerId]);

  const login = (accessToken, custId) => {
    setToken(accessToken);
    setCustomerId(custId);
  };

  const logout = () => {
    setToken(null);
    setCustomerId(null);
    localStorage.removeItem("portal_token");
    localStorage.removeItem("portal_customer_id");
  };

  const getAuthHeader = useCallback(() => ({
    headers: { Authorization: `Bearer ${token}` }
  }), [token]);

  return (
    <PortalAuthContext.Provider value={{ token, customerId, login, logout, getAuthHeader, isAuthenticated: !!token }}>
      {children}
    </PortalAuthContext.Provider>
  );
}

export const usePortalAuth = () => useContext(PortalAuthContext);
