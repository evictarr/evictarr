export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const headers: Record<string, string> = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(method !== 'GET' && method !== 'HEAD' ? { 'X-Requested-With': 'XMLHttpRequest' } : {}),
    ...(options.headers as Record<string, string> | undefined),
  }

  const response = await fetch(path, {
    ...options,
    method,
    headers,
    credentials: 'include',
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, body.detail ?? 'Request failed')
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
