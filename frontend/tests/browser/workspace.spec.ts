import { test, expect, type Page } from '@playwright/test'

// Deliberately synthetic records: these tests verify UI behavior, not clinical data.
const medications = [
  { name: 'Ibuprofen', language: 'EN', country: 'US' },
  { name: 'Ibuprofène', language: 'FR', country: 'FR' },
  { name: 'Ibuprofeno', language: 'ES', country: 'MX' },
].map((row, index) => ({ ...row, source_id: String(index), source_name: 'Test fixture', brand: null, type: 'ingredient', uploaded_at: '' }))

async function fixture(page: Page) {
  await page.route('http://localhost:8000/**', async route => {
    const path = new URL(route.request().url()).pathname
    const body = path === '/languages' ? { languages: ['en', 'es', 'fr'] }
      : path === '/search' ? medications
      : { canonical: 'ibuprofen', results: [{ translation: 'Fixture translation', language: 'Spanish', country: 'MX', brand: 'Fixture brand' }] }
    await route.fulfill({ json: body })
  })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Start with a medication name' })).toBeVisible()
}

async function search(page: Page) {
  await page.getByLabel('Medication name', { exact: true }).fill('ibuprofen')
  await page.getByLabel('Medication name', { exact: true }).press('Enter')
  await expect(page.getByRole('button', { name: /^Ibuprofen(?: |$)/ })).toBeVisible()
}

test('search, keyboard selection, translation and destination changes', async ({ page }) => {
  await fixture(page)
  await search(page)
  const medication = page.getByRole('button', { name: 'Ibuprofen', exact: true })
  await medication.focus()
  await page.keyboard.press('Enter')
  await expect(medication).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: 'Translate', exact: true }).click()
  await expect(page.locator('dd').filter({ hasText: 'Fixture translation' })).toBeVisible()
  await page.getByLabel('Target Country', { exact: true }).selectOption('ES')
  await expect(page.locator('dd')).toHaveCount(0)
})

test('language filters hide records and reset restores them without another search', async ({ page }) => {
  await fixture(page)
  await search(page)
  let searches = 0
  page.on('request', request => { if (new URL(request.url()).pathname === '/search') searches++ })
  await page.getByRole('button', { name: /Filter Languages/ }).click()
  await page.getByRole('checkbox', { name: /French/ }).uncheck()
  await page.getByRole('button', { name: /Apply Filter/ }).click()
  await expect(page.getByRole('button', { name: 'Ibuprofène', exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Reset to all languages' }).click()
  await expect(page.getByRole('button', { name: 'Ibuprofène', exact: true })).toBeVisible()
  expect(searches).toBe(0)
})

test('loading, no matches, failed request and retry have distinct states', async ({ page }) => {
  await fixture(page)
  let release: () => void = () => {}
  const pending = new Promise<void>(resolve => { release = resolve })
  await page.route('**/search?*', async route => { await pending; await route.fulfill({ json: [] }) })
  await page.getByLabel('Medication name', { exact: true }).fill('missing')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Searching…' })).toBeVisible()
  release()
  await expect(page.getByRole('heading', { name: 'No matching medications' })).toBeVisible()
  await page.route('**/search?*', route => route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } }))
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Fixture unavailable')
  await expect(page.getByRole('heading', { name: 'Search unavailable' })).toBeVisible()
  await page.route('**/search?*', route => route.fulfill({ json: medications }))
  await search(page)
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('late translation cannot appear under a different selected medication', async ({ page }) => {
  await fixture(page)
  await search(page)
  let release: () => void = () => {}
  const pending = new Promise<void>(resolve => { release = resolve })
  await page.route('**/translate', async route => {
    await pending
    await route.fulfill({ json: { results: [{ translation: 'Stale translation' }] } })
  })
  await page.getByRole('button', { name: 'Ibuprofen', exact: true }).click()
  const request = page.waitForRequest('**/translate')
  await page.getByRole('button', { name: 'Translate', exact: true }).click()
  await request
  await page.getByRole('button', { name: 'Ibuprofène', exact: true }).click()
  const response = page.waitForResponse('**/translate')
  release()
  await (await response).finished()
  await page.evaluate(() => new Promise(requestAnimationFrame))
  await expect(page.getByRole('complementary')).toContainText('Ibuprofène')
  await expect(page.locator('dd')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Translate', exact: true })).toBeEnabled()
})

for (const width of [390, 768, 1024, 1440]) {
  test(`workspace and utility controls fit at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 })
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await fixture(page)
    await search(page)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.getByRole('button', { name: /Filter Languages/ }).click()
    await expect(page.getByRole('dialog', { name: 'Filter Active Languages' })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Filter Languages/ })).toBeFocused()
    await page.getByRole('button', { name: 'Populate', exact: true }).click()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.keyboard.press('Escape')
    for (const name of ['Import Language File', 'OCR Scan']) {
      await page.getByRole('button', { name, exact: true }).click()
      await expect(page.getByRole('dialog')).toBeVisible()
      await page.keyboard.press('Escape')
      await expect(page.getByRole('dialog')).toHaveCount(0)
    }
    expect(errors).toEqual([])
  })
}

test('workspace copy follows the selected interface language', async ({ page }) => {
  await fixture(page)
  await page.getByRole('button', { name: 'English', exact: true }).click()
  await page.getByRole('button', { name: 'Spanish es', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Un medicamento. Varios idiomas.' })).toBeVisible()
  await expect(page.getByLabel('Nombre del medicamento', { exact: true })).toBeVisible()
})
