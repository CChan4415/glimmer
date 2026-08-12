import axios from 'axios'

const api = axios.create({
  baseURL: '/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('glimmer_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('glimmer_token')
      localStorage.removeItem('glimmer_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export default api
