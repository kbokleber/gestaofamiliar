import api from '../lib/api'

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
  first_name: string
  last_name: string
}

export const authService = {
  async login(credentials: LoginCredentials) {
    const formData = new FormData()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)
    
    const response = await api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 15000, // 15s para evitar ficar "Entrando..." para sempre
    })
    return response.data
  },

  async register(data: RegisterData) {
    const response = await api.post('/auth/register', data)
    return response.data
  },

  async getMe() {
    const response = await api.get('/users/me', { timeout: 10000 })
    return response.data
  },
}

