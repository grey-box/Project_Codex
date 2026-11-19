/** Read the population API's newline-delimited JSON progress stream. */
export async function readPopulationResponse(
  response: Response,
  onProgress: (message: string) => void,
): Promise<void> {
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Please sign in before populating data sources.')
    }
    if (response.status === 403) {
      throw new Error('Your account does not have permission to populate data sources.')
    }
    const body: unknown = await response.json().catch(() => null)
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    throw new Error(typeof detail === 'string' ? detail : `Population request failed (${response.status}).`)
  }

  if (!response.body) {
    throw new Error('The server returned no population progress stream.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let receivedProgress = false
  let finished = false

  const readLine = (line: string) => {
    const trimmed = line.trim()
    if (!trimmed) return
    // Retain compatibility with the older data:-prefixed JSON responses.
    const json = trimmed.startsWith('data:') ? trimmed.slice(5).trim() : trimmed
    let event: unknown
    try {
      event = JSON.parse(json)
    } catch {
      throw new Error('The server returned invalid population progress data.')
    }
    if (!event || typeof event !== 'object') {
      throw new Error('The server returned invalid population progress data.')
    }
    if ('error' in event) {
      throw new Error(typeof event.error === 'string' && event.error
        ? event.error : 'The server could not populate the selected sources.')
    }
    if (!('progress' in event) || typeof event.progress !== 'string' || !event.progress.trim()) {
      throw new Error('The server returned invalid population progress data.')
    }
    receivedProgress = true
    onProgress(event.progress)
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) readLine(line)
    }
    // The last JSON record does not have to end with a newline.
    readLine(buffer + decoder.decode())
    if (!receivedProgress) {
      throw new Error('The server returned an empty population progress stream.')
    }
    finished = true
  } finally {
    // Stop consuming a rejected stream and always release the reader lock.
    if (!finished) await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}
