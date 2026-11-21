import { test, expect, type Page } from '@playwright/test'

const records = [
  { name: 'Zinc10', language: 'EN', country: 'CA', source_id: 'z10' },
  { name: 'aspirin', language: 'FR', country: 'FR', source_id: 'a' },
  { name: 'Zinc2', language: 'EN', country: 'CA', source_id: 'z2' },
].map(row => ({ ...row, brand: null, type: 'ingredient', source_name: 'Synthetic fixture', uploaded_at: '' }))

async function search(page: Page) {
  let requests = 0
  await page.route('http://localhost:8000/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/search') requests++
    return route.fulfill({ json: path === '/languages' ? { languages: ['en', 'fr'] } : path === '/search' ? records : [] })
  })
  await page.goto('/')
  await expect(page.getByLabel('Sort results', { exact: true })).toHaveCount(0)
  await page.getByLabel('Medication name', { exact: true }).fill('fixture')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByLabel('Sort results', { exact: true })).toBeVisible()
  return () => requests
}

async function sort(page: Page, name: string) {
  await page.getByLabel('Sort results', { exact: true }).click()
  await page.getByRole('option', { name, exact: true }).click()
}

for (const width of [320, 1440]) for (const theme of ['light', 'dark']) {
  test(`result sorting preserves default order and selection at ${width}px in ${theme} mode`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(mode => localStorage.setItem('codex-theme', mode), theme)
    const countRequests = await search(page)
    const names = page.locator(width < 768 ? '.workspace-result-card-name' : '.workspace-result-name button')
    const buttons = page.locator(width < 768 ? '.workspace-result-card' : '.workspace-result-name button')
    await expect(names).toHaveText(['Zinc10', 'aspirin', 'Zinc2'])
    await buttons.filter({ hasText: 'Zinc2' }).click()
    await sort(page, 'Medication name A–Z')
    await expect(names).toHaveText(['aspirin', 'Zinc2', 'Zinc10'])
    await expect(buttons.filter({ hasText: 'Zinc2' })).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.workspace-results-sort [role=status]')).toContainText('Medication name A–Z')
    await sort(page, 'Medication name Z–A')
    await expect(names).toHaveText(['Zinc10', 'Zinc2', 'aspirin'])
    await sort(page, 'Default order')
    await expect(names).toHaveText(['Zinc10', 'aspirin', 'Zinc2'])
    expect(countRequests()).toBe(1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath(`sorting-${width}-${theme}.png`), fullPage: true, animations: 'disabled' })
  })
}

test('sorting stays applied when language filters change and reset', async ({ page }) => {
  const countRequests = await search(page)
  await sort(page, 'Medication name A–Z')
  await page.getByRole('button', { name: 'Filter Languages (2/2)', exact: true }).click()
  await page.getByRole('checkbox', { name: /French/ }).uncheck()
  await page.getByRole('button', { name: /Apply Filter/ }).click()
  await expect(page.locator('.workspace-result-name button')).toHaveText(['Zinc2', 'Zinc10'])
  await page.getByRole('button', { name: 'Reset to all languages', exact: true }).click()
  await expect(page.locator('.workspace-result-name button')).toHaveText(['aspirin', 'Zinc2', 'Zinc10'])
  expect(countRequests()).toBe(1)
})

test('sort control supports keyboard operation', async ({ page }) => {
  await search(page)
  const picker = page.getByLabel('Sort results', { exact: true })
  await picker.focus()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('option', { name: 'Default order', exact: true })).toBeFocused()
  await page.keyboard.press('End')
  await expect(page.getByRole('option', { name: 'Medication name Z–A', exact: true })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(picker).toContainText('Medication name Z–A')
  await expect(picker).toBeFocused()
  await expect(page.locator('.workspace-result-name button')).toHaveText(['Zinc10', 'Zinc2', 'aspirin'])
})
