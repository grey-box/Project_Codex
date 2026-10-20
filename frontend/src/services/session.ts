// Access tokens stay in memory and are cleared on refresh or sign-out.
let accessToken = ''
export function setAccessToken(token: string) { accessToken = token }
export function getAuthHeaders(): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
}
