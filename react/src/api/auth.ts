import i18n from '../i18n'

export interface AuthStatus {
  status: 'logged_out' | 'pending' | 'logged_in'
  is_logged_in: boolean
  user_info?: UserInfo
  tokenExpired?: boolean
}

export interface UserInfo {
  id: string
  username: string
  email?: string
  image_url?: string
  provider?: string
  created_at?: string
  updated_at?: string
}

export interface ApiResponse {
  status: string
  message: string
}

export interface AuthResponse {
  status: string
  message?: string
  token?: string
  user_info?: UserInfo
}

export async function login(
  username: string,
  password: string
): Promise<AuthResponse> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return await response.json()
}

export async function register(
  username: string,
  password: string
): Promise<AuthResponse> {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return await response.json()
}

export async function getAuthStatus(): Promise<AuthStatus> {
  const token = localStorage.getItem('access_token')
  const userInfo = localStorage.getItem('user_info')

  if (!token || !userInfo) {
    return { status: 'logged_out', is_logged_in: false }
  }

  try {
    const response = await fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    const data = await response.json()

    if (data.status === 'success') {
      return {
        status: 'logged_in',
        is_logged_in: true,
        user_info: data.user_info,
      }
    }

    // Token invalid/expired
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
    return { status: 'logged_out', is_logged_in: false, tokenExpired: true }
  } catch {
    // Network error — keep user logged in with cached data
    return {
      status: 'logged_in',
      is_logged_in: true,
      user_info: JSON.parse(userInfo),
    }
  }
}

export async function logout(): Promise<ApiResponse> {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_info')
  return {
    status: 'success',
    message: i18n.t('common:auth.logoutSuccessMessage'),
  }
}

export async function getUserProfile(): Promise<UserInfo> {
  const userInfo = localStorage.getItem('user_info')
  if (!userInfo) {
    throw new Error(i18n.t('common:auth.notLoggedIn'))
  }
  return JSON.parse(userInfo)
}

export function saveAuthData(token: string, userInfo: UserInfo) {
  localStorage.setItem('access_token', token)
  localStorage.setItem('user_info', JSON.stringify(userInfo))
}

export function getAccessToken(): string | null {
  return localStorage.getItem('access_token')
}

export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getAccessToken()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return fetch(url, { ...options, headers })
}
