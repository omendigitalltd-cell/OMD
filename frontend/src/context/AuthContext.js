import { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const AuthContext = createContext(null);

const API_URL = process.env.REACT_APP_BACKEND_URL;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("hotspot_token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API_URL}/api/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          setUser(response.data);
        } catch (error) {
          localStorage.removeItem("hotspot_token");
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, [token]);

  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/api/auth/login`, {
      email,
      password,
    });
    const newToken = response.data.access_token;
    localStorage.setItem("hotspot_token", newToken);
    setToken(newToken);
    
    const userResponse = await axios.get(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${newToken}` },
    });
    setUser(userResponse.data);
    return response.data;
  };

  const register = async (email, password) => {
    const response = await axios.post(`${API_URL}/api/auth/register`, {
      email,
      password,
    });
    const newToken = response.data.access_token;
    localStorage.setItem("hotspot_token", newToken);
    setToken(newToken);
    
    const userResponse = await axios.get(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${newToken}` },
    });
    setUser(userResponse.data);
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem("hotspot_token");
    setToken(null);
    setUser(null);
  };

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <AuthContext.Provider
      value={{
        user,
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
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
