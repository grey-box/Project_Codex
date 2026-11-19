import { test, expect, type Page } from '@playwright/test'

// A one-pixel synthetic image. OCR responses are fixtures, not medical claims.
const image = {
  name: 'first.png', mimeType: 'image/png',
  buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lz0AAAAASUVORK5CYII=', 'base64'),
}

async function openScanner(page: Page) {
  await page.route('**/languages', route => route.fulfill({ json: { languages: ['en', 'es'] } }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Scan medication', exact: true }).click()
}

test('rejects unsupported, empty and oversized files without uploading', async ({ page }) => {
  let requests = 0
  await page.route('**/ocrmatching/', route => { requests++; return route.fulfill({ json: [] }) })
  await openScanner(page)
  for (const [file, message] of [
    [{ ...image, name: 'animated.gif', mimeType: 'image/gif' }, 'valid image file'],
    [{ ...image, buffer: Buffer.alloc(0) }, 'image is empty'],
    [{ ...image, buffer: Buffer.alloc(10 * 1024 * 1024 + 1) }, 'no larger than 10 MB'],
  ] as const) {
    await page.getByLabel('Image file', { exact: true }).setInputFiles(file)
    await expect(page.getByRole('alert')).toContainText(message)
    await expect(page.getByRole('button', { name: 'Extract & Match', exact: true })).toBeDisabled()
    await expect(page.getByAltText('Uploaded preview')).toHaveCount(0)
  }
  expect(requests).toBe(0)
  await page.getByLabel('Image file', { exact: true }).setInputFiles(image)
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Extract & Match', exact: true })).toBeEnabled()
})

test('replacing an image aborts its scan and keeps only the replacement result', async ({ page }) => {
  let release: () => void = () => {}
  const pending = new Promise<void>(resolve => { release = resolve })
  let calls = 0
  await page.route('**/ocrmatching/', async route => {
    if (++calls === 1) {
      await pending
      await route.fulfill({ json: [{ rec_text: 'Stale text' }] }).catch(() => {})
    } else {
      await route.fulfill({ json: { results: [{ rec_text: 'Replacement text', rec_score: 0.92 }] } })
    }
  })
  await openScanner(page)
  await page.getByLabel('Image file', { exact: true }).setInputFiles(image)
  const started = page.waitForRequest('**/ocrmatching/')
  await page.getByRole('button', { name: 'Extract & Match', exact: true }).click()
  await started
  const cancelled = page.waitForEvent('requestfailed', { predicate: request => request.url().endsWith('/ocrmatching/') })
  await page.getByLabel('Image file', { exact: true }).setInputFiles({ ...image, name: 'replacement.png' })
  expect((await cancelled).failure()?.errorText).toContain('ERR_ABORTED')
  await expect(page.getByText('replacement.png', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Extract & Match', exact: true }).click()
  await expect(page.getByRole('cell', { name: 'Replacement text', exact: true })).toBeVisible()
  release()
  await expect(page.getByText('Stale text', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('closing during a scan aborts the request and reopening starts clean', async ({ page }) => {
  let release: () => void = () => {}
  const pending = new Promise<void>(resolve => { release = resolve })
  await page.route('**/ocrmatching/', async route => {
    await pending
    await route.fulfill({ json: [{ rec_text: 'Closed scan result' }] }).catch(() => {})
  })
  await openScanner(page)
  await page.getByLabel('Image file', { exact: true }).setInputFiles(image)
  const started = page.waitForRequest('**/ocrmatching/')
  await page.getByRole('button', { name: 'Extract & Match', exact: true }).click()
  await started
  const cancelled = page.waitForEvent('requestfailed', { predicate: request => request.url().endsWith('/ocrmatching/') })
  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  expect((await cancelled).failure()?.errorText).toContain('ERR_ABORTED')
  release()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: 'Scan medication', exact: true }).click()
  await expect(page.getByAltText('Uploaded preview')).toHaveCount(0)
  await expect(page.getByText('Closed scan result', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Extract & Match', exact: true })).toBeDisabled()
})

test('keyboard upload, failure retry and recognized text to search work together', async ({ page }) => {
  let calls = 0
  await page.route('**/ocrmatching/', route => ++calls === 1
    ? route.fulfill({ status: 503, json: { detail: 'Scanner unavailable' } })
    : route.fulfill({ json: [{ rec_text: 'Fixture medication', rec_score: 0.94 }] }))
  await openScanner(page)
  const chooserPromise = page.waitForEvent('filechooser')
  await page.getByRole('button', { name: 'Choose an image', exact: true }).press('Enter')
  await (await chooserPromise).setFiles(image)
  await page.getByRole('button', { name: 'Extract & Match', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Scanner unavailable')
  await page.getByRole('button', { name: 'Extract & Match', exact: true }).click()
  await expect(page.getByRole('cell', { name: 'Fixture medication', exact: true })).toBeVisible()
  await expect(page.getByRole('cell', { name: '94.0%', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Use in Search', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByLabel('Medication name', { exact: true })).toHaveValue('Fixture medication')
})
