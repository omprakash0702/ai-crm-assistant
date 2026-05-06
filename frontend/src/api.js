// OLD: http://localhost:8000
export const API = import.meta.env.VITE_API_URL || 'http://13.233.132.223:8000'

export function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': localStorage.getItem('api_key') || '',
  }
}

export function getJwtHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('jwt_token') || ''}`,
  }
}

export async function apiFetch(url, options = {}) {
  const res = await fetch(url, options)
  if (res.status === 401) {
    localStorage.removeItem('jwt_token')
    window.dispatchEvent(new Event('auth:logout'))
  }
  return res
}
