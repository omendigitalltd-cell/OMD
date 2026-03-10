import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const DistributorAuthContext = createContext(null);

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const DistributorAuthProvider = ({ children }) => {
  const [distributor, setDistributor] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("distributor_token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API_URL}/api/distributor/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          setDistributor(response.data);
        } catch (error) {
          localStorage.removeItem("distributor_token");
          setToken(null);
          setDistributor(null);
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, [token]);

  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/api/distributor/login`, {
      email,
      password,
    });
    const newToken = response.data.access_token;
    localStorage.setItem("distributor_token", newToken);
    setToken(newToken);
    
    const userResponse = await axios.get(`${API_URL}/api/distributor/me`, {
      headers: { Authorization: `Bearer ${newToken}` },
    });
    setDistributor(userResponse.data);
    return response.data;
  };

  const register = async (name, email, phone, password) => {
    const response = await axios.post(`${API_URL}/api/distributor/register`, {
      name,
      email,
      phone,
      password,
    });
    const newToken = response.data.access_token;
    localStorage.setItem("distributor_token", newToken);
    setToken(newToken);
    
    const userResponse = await axios.get(`${API_URL}/api/distributor/me`, {
      headers: { Authorization: `Bearer ${newToken}` },
    });
    setDistributor(userResponse.data);
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem("distributor_token");
    setToken(null);
    setDistributor(null);
  };

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <DistributorAuthContext.Provider
      value={{
        distributor,
        token,
        loading,
        isAuthenticated: !!token,
        login,
        register,
        logout,
        getAuthHeader,
      }}
    >
      {children}
    </DistributorAuthContext.Provider>
  );
};

export const useDistributorAuth = () => {
  const context = useContext(DistributorAuthContext);
  if (!context) {
    throw new Error("useDistributorAuth must be used within a DistributorAuthProvider");
  }
  return context;
};
