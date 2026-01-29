import React, { createContext, useState, useCallback } from 'react'

interface AuthContextType {
  token: string | null
  userId: number | null
  role: string | null
  login: (email: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string, full_name: string, role: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [userId, setUserId] = useState<number | null>(parseInt(localStorage.getItem('userId') || '0') || null)
  const [role, setRole] = useState<string | null>(localStorage.getItem('role'))

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })

    if (!response.ok) throw new Error('Login failed')

    const data = await response.json()
    setToken(data.access_token)
    setUserId(data.user_id)
    setRole(data.role)
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('userId', data.user_id.toString())
    localStorage.setItem('role', data.role)
    localStorage.setItem('username', data.username || email)
  }, [])

  const register = useCallback(async (username: string, email: string, password: string, full_name: string, role: string) => {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password, full_name, role })
    })

    if (!response.ok) throw new Error('Registration failed')

    const data = await response.json()
    setToken(data.access_token)
    setUserId(data.user_id)
    setRole(data.role)
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('userId', data.user_id.toString())
    localStorage.setItem('role', data.role)
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUserId(null)
    setRole(null)
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    localStorage.removeItem('role')
  }, [])

  return (
    <AuthContext.Provider value={{
      token,
      userId,
      role,
      login,
      register,
      logout,
      isAuthenticated: !!token
    }}>
      {children}
    </AuthContext.Provider>
  )
}
