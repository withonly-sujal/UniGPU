import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const savedToken = localStorage.getItem('token');
        const saved = localStorage.getItem('user');
        if (savedToken) {
            setToken(savedToken);
        }
        if (saved) {
            setUser(JSON.parse(saved));
        }
        setLoading(false);
    }, []);

    const login = async (username, password) => {
        const res = await api.login({ username, password });
        localStorage.setItem('token', res.access_token);
        const userData = {
            id: res.user_id,
            username,
            role: res.role,
        };
        localStorage.setItem('user', JSON.stringify(userData));
        setToken(res.access_token);
        setUser(userData);
        return userData;
    };

    const register = async (data) => {
        // Register the user
        await api.register(data);
        // Auto-login after successful registration
        const userData = await login(data.username, data.password);
        return userData;
    };

    const logout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
