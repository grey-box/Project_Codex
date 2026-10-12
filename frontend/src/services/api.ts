export const API_BASE_URL = 'http://localhost:8000'

export interface LoginResponse {
  access_token: string
  token_type: string
  role: string
}

export interface User {
  email: string
  real_name: string
  role: string
  affiliation: string
  created_at?: string | null
}

export interface CreateUserRequest {
  email: string
  real_name: string
  password: string
  role: string
  affiliation: string
}

export interface UpdateUserRequest {
  real_name?: string
  password?: string
  role?: string
  affiliation?: string
}

async function getErrorMessage(response: Response): Promise<string> {
  const body = await response.json().catch(() => null)

  if (body?.detail) {
    return body.detail
  }

  return `Request failed with status ${response.status}`
}

function authHeaders(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
  }
}

export async function loginUser(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
    }),
  })

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json()
}

export async function getUsers(token: string): Promise<User[]> {
  const response = await fetch(`${API_BASE_URL}/users`, {
    headers: authHeaders(token),
  })

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json()
}

export async function createUser(
  token: string,
  user: CreateUserRequest,
): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/users`, {
    method: 'POST',
    headers: {
      ...authHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(user),
  })

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json()
}

export async function updateUser(
  token: string,
  email: string,
  updates: UpdateUserRequest,
): Promise<User> {
  const response = await fetch(
    `${API_BASE_URL}/users/${encodeURIComponent(email)}`,
    {
      method: 'PATCH',
      headers: {
        ...authHeaders(token),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    },
  )

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json()
}

export async function deleteUser(
  token: string,
  email: string,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/users/${encodeURIComponent(email)}`,
    {
      method: 'DELETE',
      headers: authHeaders(token),
    },
  )

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }
}
