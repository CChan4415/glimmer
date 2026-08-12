import { createContext, useContext, useState } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('glimmer_token'))
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('glimmer_user')
    return raw ? JSON.parse(raw) : null
  })

  const login = async (phone, code) => {
    const { data } = await api.post('/auth/verify', { phone, code })
    const d = data.data
    localStorage.setItem('glimmer_token', d.access_token)
    localStorage.setItem('glimmer_user', JSON.stringify(d.user))
    setToken(d.access_token)
    setUser(d.user)
    return d.user
  }

  const logout = () => {
    localStorage.removeItem('glimmer_token')
    localStorage.removeItem('glimmer_user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
