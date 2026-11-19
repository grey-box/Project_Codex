import assert from 'node:assert/strict'
import test from 'node:test'
import { readPopulationResponse } from '../src/services/population.js'

const encoder = new TextEncoder()
function streamResponse(chunks: (string | Uint8Array)[]) {
  return new Response(new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(typeof chunk === 'string' ? encoder.encode(chunk) : chunk)
      controller.close()
    },
  }))
}

test('reads split records, multiple records and a final record without a newline', async () => {
  const messages: string[] = []
  await readPopulationResponse(streamResponse([
    '{"prog', 'ress":"Starting"}\n{"progress":"Working"}\n', '{"progress":"Finished"}',
  ]), (message) => messages.push(message))
  assert.deepEqual(messages, ['Starting', 'Working', 'Finished'])
})

test('preserves UTF-8 characters split between byte chunks and CRLF records', async () => {
  const bytes = encoder.encode('{"progress":"Médicaments"}\r\n')
  const split = bytes.indexOf(0xc3) + 1
  const messages: string[] = []
  await readPopulationResponse(streamResponse([bytes.slice(0, split), bytes.slice(split)]), (message) => messages.push(message))
  assert.deepEqual(messages, ['Médicaments'])
})

test('accepts legacy data prefixes and blank lines', async () => {
  const messages: string[] = []
  await readPopulationResponse(streamResponse(['\n data: {"progress":"Finished"}\r\n\n']), (message) => messages.push(message))
  assert.deepEqual(messages, ['Finished'])
})

for (const [status, expected] of [[401, /sign in/], [403, /permission/]] as const) {
  test(`rejects HTTP ${status} instead of interpreting its body as successful progress`, async () => {
    const response = new Response('{"detail":"Access denied"}', { status })
    await assert.rejects(readPopulationResponse(response, () => assert.fail('Must not emit progress')), expected)
  })
}

test('reports a server-provided HTTP error', async () => {
  const response = new Response('{"detail":"Invalid source selection"}', { status: 400 })
  await assert.rejects(readPopulationResponse(response, () => {}), /Invalid source selection/)
})

test('handles non-JSON error responses', async () => {
  const response = new Response('<html>Unavailable</html>', { status: 503 })
  await assert.rejects(readPopulationResponse(response, () => {}), /503/)
})

test('rejects a missing response body', async () => {
  await assert.rejects(readPopulationResponse(new Response(null), () => {}), /no population progress stream/)
})

test('rejects an empty response stream', async () => {
  await assert.rejects(readPopulationResponse(streamResponse(['\n']), () => {}), /empty population progress stream/)
})

for (const record of ['invalid json', '{"progress":', 'null', '{"progress":5}', '{"detail":"Error"}']) {
  test(`rejects malformed progress: ${record}`, async () => {
    await assert.rejects(readPopulationResponse(streamResponse([record]), () => {}), /invalid population progress data/)
  })
}

test('stops on a streamed error, even after valid progress', async () => {
  const messages: string[] = []
  await assert.rejects(readPopulationResponse(streamResponse([
    '{"progress":"Starting"}\n{"error":"Source unavailable"}\n{"progress":"Finished"}\n',
  ]), (message) => messages.push(message)), /Source unavailable/)
  assert.deepEqual(messages, ['Starting'])
})

test('propagates an interrupted stream instead of returning success', async () => {
  let reads = 0
  const response = new Response(new ReadableStream<Uint8Array>({
    pull(controller) {
      if (reads++ === 0) controller.enqueue(encoder.encode('{"progress":"Starting"}\n'))
      else controller.error(new Error('Connection lost'))
    },
  }))
  await assert.rejects(readPopulationResponse(response, () => {}), /Connection lost/)
  assert.equal(response.body?.locked, false)
})

test('cancels and unlocks a stream when a record is rejected', async () => {
  let cancelled = false
  const response = new Response(new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(encoder.encode('invalid\n')) },
    cancel() { cancelled = true },
  }))
  await assert.rejects(readPopulationResponse(response, () => {}), /invalid population progress data/)
  assert.equal(cancelled, true)
  assert.equal(response.body?.locked, false)
})
