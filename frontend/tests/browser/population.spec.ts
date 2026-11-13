import { test, expect, type Page } from '@playwright/test'

const complete = '{"progress":"Selected source completed successfully!"}'
const successText = 'Successfully populated Neo4j!'
const populationStatus = (page: Page) => page.locator('[data-dropdown-panel]').getByRole('status')

async function openPopulation(page: Page) {
  await page.route('**/languages', route => route.fulfill({ json: { languages: ['en', 'es', 'fr', 'ru', 'uk'] } }))
  await page.goto('/')
  if (page.viewportSize()!.width < 768) await page.getByRole('button', { name: 'Open navigation', exact: true }).click()
  await page.getByRole('button', { name: 'Populate sources', exact: true }).click()
}

test('only selected providers expose credentials and required fields receive focus', async ({ page }) => {
  let requests = 0
  await page.route('**/api/populate-sources', route => { requests++; return route.fulfill({ body: complete }) })
  await openPopulation(page)
  await expect(page.locator('#drugbank-key, #icd-id, #icd-secret')).toHaveCount(0)
  await page.getByRole('checkbox', { name: /RxNorm/ }).check()
  await expect(page.locator('#drugbank-key, #icd-id, #icd-secret')).toHaveCount(0)
  await page.getByRole('checkbox', { name: /DrugBank/ }).check()
  await expect(page.locator('#drugbank-key')).toBeVisible()
  await expect(page.locator('#icd-id, #icd-secret')).toHaveCount(0)
  await page.getByRole('button', { name: 'Populate (2)', exact: true }).click()
  await expect(page.locator('#drugbank-key')).toBeFocused()
  await expect(page.locator('#drugbank-key')).toHaveAttribute('aria-invalid', 'true')
  await expect(page.getByRole('alert')).toContainText('Enter the required credentials')
  await page.locator('#drugbank-key').fill('   ')
  await page.getByRole('button', { name: 'Populate (2)', exact: true }).click()
  expect(requests).toBe(0)
  await page.locator('#drugbank-key').fill('synthetic-test-key')
  await expect(page.getByRole('alert')).toHaveCount(0)
  const sent = page.waitForRequest('**/api/populate-sources')
  await page.getByRole('button', { name: 'Populate (2)', exact: true }).click()
  expect((await sent).postDataJSON()).toEqual({ selectedSources: ['drugbank', 'rxnorm'], DBAPIKey: 'synthetic-test-key', ICDID: '', ICDSecret: '' })
  await expect(populationStatus(page)).toHaveText(successText)
  expect(requests).toBe(1)
  await page.getByRole('checkbox', { name: /DrugBank/ }).uncheck()
  await expect(populationStatus(page)).toHaveCount(0)
  await expect(page.locator('#drugbank-key')).toHaveCount(0)
})

test('ICD-11 needs both credentials but does not require a DrugBank key', async ({ page }) => {
  let requests = 0
  await page.route('**/api/populate-sources', route => { requests++; return route.fulfill({ body: complete }) })
  await openPopulation(page)
  await page.getByRole('checkbox', { name: /ICD-11/ }).check()
  await page.getByRole('button', { name: 'Populate (1)', exact: true }).click()
  await expect(page.locator('#icd-id')).toBeFocused()
  await expect(page.locator('#icd-secret')).toHaveAttribute('aria-invalid', 'true')
  await page.locator('#icd-id').fill('synthetic-client')
  await page.getByRole('button', { name: 'Populate (1)', exact: true }).click()
  await expect(page.locator('#icd-secret')).toBeFocused()
  expect(requests).toBe(0)
  await page.locator('#icd-secret').fill('synthetic-secret')
  const sent = page.waitForRequest('**/api/populate-sources')
  await page.getByRole('button', { name: 'Populate (1)', exact: true }).click()
  expect((await sent).postDataJSON()).toEqual({ selectedSources: ['icd11'], DBAPIKey: '', ICDID: 'synthetic-client', ICDSecret: 'synthetic-secret' })
  await expect(populationStatus(page)).toHaveText(successText)
  await page.getByRole('checkbox', { name: /ICD-11/ }).uncheck()
  await page.getByRole('checkbox', { name: /ICD-11/ }).check()
  await expect(page.locator('#icd-id')).toHaveValue('synthetic-client')
  await expect(page.locator('#icd-secret')).toHaveValue('synthetic-secret')
  await page.getByRole('checkbox', { name: /ICD-11/ }).uncheck()
  await page.getByRole('checkbox', { name: /RxNorm/ }).check()
  const uncredentialed = page.waitForRequest('**/api/populate-sources')
  await page.getByRole('button', { name: 'Populate (1)', exact: true }).click()
  expect((await uncredentialed).postDataJSON()).toEqual({ selectedSources: ['rxnorm'], DBAPIKey: '', ICDID: '', ICDSecret: '' })
  await expect(populationStatus(page)).toHaveText(successText)
})

for (const failure of ['HTTP', 'stream']) {
  test(`${failure} failure never reports success and the same selection can be retried`, async ({ page }) => {
    let attempts = 0
    await page.route('**/api/populate-sources', route => {
      attempts++
      if (attempts === 1) return failure === 'HTTP'
        ? route.fulfill({ status: 503, json: { detail: 'Synthetic provider outage' } })
        : route.fulfill({ contentType: 'application/x-ndjson', body: '{"progress":"Ingesting selected source..."}\n{"error":"Synthetic provider outage"}\n' })
      return route.fulfill({ contentType: 'application/x-ndjson', body: complete })
    })
    await openPopulation(page)
    await page.getByRole('checkbox', { name: /RxNorm/ }).check()
    await page.getByRole('button', { name: 'Populate (1)', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('Synthetic provider outage')
    await expect(populationStatus(page)).toHaveCount(0)
    await expect(page.getByRole('checkbox', { name: /RxNorm/ })).toBeChecked()
    await page.getByRole('button', { name: 'Populate (1)', exact: true }).click()
    await expect(populationStatus(page)).toHaveText(successText)
    await expect(page.getByRole('alert')).toHaveCount(0)
    expect(attempts).toBe(2)
  })
}

test('an active population request locks its configuration and prevents duplicate requests', async ({ page }) => {
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  let attempts = 0
  await page.route('**/api/populate-sources', async route => {
    attempts++
    await pending
    await route.fulfill({ body: complete })
  })
  await openPopulation(page)
  await page.getByRole('checkbox', { name: /DrugBank/ }).check()
  await page.locator('#drugbank-key').fill('synthetic-key')
  const sent = page.waitForRequest('**/api/populate-sources')
  await page.getByRole('button', { name: 'Populate (1)', exact: true }).click()
  await sent
  await expect(page.locator('#drugbank-key')).toBeDisabled()
  for (const source of [/DrugBank/, /SNOMED CT/, /RxNorm/, /ICD-11/]) await expect(page.getByRole('checkbox', { name: source })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Populate (1)', exact: true })).toBeDisabled()
  release()
  await expect(populationStatus(page)).toHaveText(successText)
  await expect(page.locator('#drugbank-key')).toBeEnabled()
  expect(attempts).toBe(1)
})

for (const width of [320, 1440]) for (const theme of ['light', 'dark']) {
  test(`population form fits ${width}px in ${theme} mode`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(mode => localStorage.setItem('codex-theme', mode), theme)
    await openPopulation(page)
    await page.getByRole('checkbox', { name: /DrugBank/ }).check()
    await page.getByRole('checkbox', { name: /ICD-11/ }).check()
    await expect(page.locator('#drugbank-key')).toBeVisible()
    await expect(page.locator('#icd-secret')).toBeVisible()
    const panel = page.locator('[data-dropdown-panel]').filter({ hasText: 'Populate local source(s):' })
    const bounds = await panel.boundingBox()
    expect(bounds!.x).toBeGreaterThanOrEqual(0)
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width)
    expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath(`population-${width}-${theme}.png`), animations: 'disabled' })
  })
}
