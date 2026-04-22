import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { getMe, loginUser, logoutUser, registerUser } from "../api/auth";
import { getSubscription } from "../api/subscription";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshSubscription = useCallback(async () => {
    try {
      const res = await getSubscription();
      setSubscription(res.data);
      return res.data;
    } catch {
      setSubscription(null);
      return null;
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      getMe()
        .then(async (res) => {
          setUser(res.data);
          await refreshSubscription();
        })
        .catch(() => {
          localStorage.removeItem("access_token");
          setUser(null);
          setSubscription(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [refreshSubscription]);

  const login = async (email, password) => {
    const res = await loginUser({ email, password });
    localStorage.setItem("access_token", res.data.access_token);
    const meRes = await getMe();
    setUser(meRes.data);
    await refreshSubscription();
    return meRes.data;
  };

  const register = async (email, username, password) => {
    await registerUser({ email, username, password });
  };

  const logout = async () => {
    try {
      await logoutUser();
    } catch {
      // ignore errors on logout
    }
    localStorage.removeItem("access_token");
    setUser(null);
    setSubscription(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, subscription, loading, login, register, logout, refreshSubscription }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
