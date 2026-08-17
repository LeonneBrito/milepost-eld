import type { ApiErrorBody } from './types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  code: string
  field: string | null

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail)
    this.status = status
    this.code = body.error
    this.field = body.field
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!res.ok) {
    let body: ApiErrorBody
    try {
      body = await res.json()
    } catch {
      body = { error: 'UNKNOWN_ERROR', detail: res.statusText, field: null }
    }
    throw new ApiError(res.status, body)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
}

// User-facing copy for a caught error. Keeps "what happened, what to do next"
// out of components — see SDD §9, no raw exception text on screen.
export function messageFor(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status >= 500 || err.status === 502 || err.status === 504) {
      return "The planner couldn't finish that route. Try again in a moment."
    }
    return err.message || 'Something about that request was invalid.'
  }
  if (err instanceof TypeError) {
    return "Can't reach the planner right now. Check your connection and try again."
  }
  return 'Something went wrong. Try again.'
}
