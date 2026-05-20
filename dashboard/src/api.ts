const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000'

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`API ${path} failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}
