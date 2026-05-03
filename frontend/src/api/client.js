import axios from 'axios'

// Use environment variable for API URL, fallback to relative path for development
const API_URL = import.meta.env.VITE_API_URL || '/api'

const client = axios.create({ baseURL: API_URL, timeout: 120000 })

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default client
