const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000'

async function buildApiError(path: string, response: Response): Promise<Error> {
  let message = `API ${path} failed with status ${response.status}`

  try {
    const body = (await response.json()) as { error?: { message?: string } }
    const serverMessage = body?.error?.message
    if (typeof serverMessage === 'string' && serverMessage.trim().length > 0) {
      message = serverMessage
    }
  } catch {
    // Keep fallback message when response body is not JSON.
  }

  return new Error(message)
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`)
  if (!response.ok) {
    throw await buildApiError(path, response)
  }

  return response.json() as Promise<T>
}

export async function apiPost<TRequest, TResponse>(path: string, payload: TRequest): Promise<TResponse> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw await buildApiError(path, response)
  }

  return response.json() as Promise<TResponse>
}

export async function apiPut<TRequest, TResponse>(path: string, payload: TRequest): Promise<TResponse> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw await buildApiError(path, response)
  }

  return response.json() as Promise<TResponse>
}
