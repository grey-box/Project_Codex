import { test, expect, type Page, type Locator } from '@playwright/test'

const longName = 'SyntheticMedication'.repeat(10)
const longBrand = 'SyntheticBrand'.repeat(10)
const record = { name: longName, brand: longBrand, type: 'ingredient', language: 'EN', country: 'US', source_id: 'responsive-fixture', source_name: 'Synthetic fixture', uploaded_at: '' }

test.use({ hasTouch: true, isMobile: true })

async function setup(page: Page) {
  await page.route('http://localhost:8000/**', route => {
    const path = new URL(route.request().url()).pathname
    return route.fulfill({ json: path === '/languages' ? { languages: ['en', 'es', 'fr', 'de'] }
      : path === '/search' ? [record]
      : path === '/packs/load' ? { message: 'Fixture language pack imported' }
      : { results: [{ translation: longName, brand: longBrand }] } })
  })
  await page.goto('/')
  await expect(page.getByLabel('Medication name', { exact: true })).toBeVisible()
}

async function fitsWidth(locator: Locator) {
  expect(await locator.evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true)
}

async function inViewport(locator: Locator, page: Page) {
  await expect(locator).toBeVisible()
  const bounds = await locator.boundingBox()
  const viewport = page.viewportSize()!
  expect(bounds).not.toBeNull()
  expect(bounds!.x).toBeGreaterThanOrEqual(-1)
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(viewport.width + 1)
  expect(bounds!.y).toBeGreaterThanOrEqual(-1)
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(viewport.height + 1)
}

test('content reflows at every layout boundary without clipping long records', async ({ page }) => {
  await setup(page)
  await page.getByLabel('Medication name', { exact: true }).fill('synthetic')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  for (const width of [320, 360, 390, 479, 480, 639, 640, 767, 768, 1024, 1199, 1200, 1440]) {
    await test.step(`${width}px`, async () => {
      await page.setViewportSize({ width, height: 844 })
      const medication = page.getByRole('button', { name: new RegExp(`^${longName}`) }).filter({ visible: true })
      await medication.click()
      await fitsWidth(page.locator('html'))
      await fitsWidth(page.locator('.workspace-search'))
      await fitsWidth(page.locator('.workspace-results'))
      const table = page.locator('.workspace-results table')
      if (await table.isVisible()) {
        await fitsWidth(table.locator('..'))
        expect((await table.boundingBox())!.width).toBeLessThanOrEqual((await page.locator('.workspace-results').boundingBox())!.width)
      }
      else await fitsWidth(page.locator('.workspace-result-card'))
      await fitsWidth(page.locator('.workspace-selected'))
      await expect(medication).toHaveAttribute('aria-pressed', 'true')
    })
  }
})

test('phone controls have touch-sized targets and input text avoids focus zoom', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 })
  await setup(page)
  for (const locator of [page.getByRole('button', { name: 'Open navigation' }), page.getByRole('button', { name: 'Search', exact: true }), page.getByLabel('Medication name', { exact: true }), page.getByLabel('Search language', { exact: true })]) {
    expect((await locator.boundingBox())!.height).toBeGreaterThanOrEqual(44)
  }
  expect(await page.getByLabel('Medication name', { exact: true }).evaluate(element => parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(16)
})

test('short landscape navigation and account tools remain reachable', async ({ page }) => {
  await page.setViewportSize({ width: 667, height: 320 })
  await setup(page)
  await page.getByRole('button', { name: 'Open navigation' }).click()
  const drawer = page.getByRole('dialog', { name: 'Workspace tools', exact: true })
  const account = drawer.getByRole('button', { name: 'Account', exact: true })
  await account.scrollIntoViewIfNeeded()
  await account.click()
  await page.getByRole('button', { name: 'Dark', exact: true }).scrollIntoViewIfNeeded()
  await inViewport(page.getByRole('button', { name: 'Dark', exact: true }), page)
  await page.getByRole('button', { name: 'Dark', exact: true }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.keyboard.press('Escape')
  await page.keyboard.press('Escape')
  await expect(drawer).toHaveCount(0)
  await expect(page.locator('body')).not.toHaveCSS('overflow', 'hidden')
  await page.setViewportSize({ width: 844, height: 320 })
  const desktopAccount = page.getByRole('button', { name: 'Account', exact: true })
  await desktopAccount.scrollIntoViewIfNeeded()
  await inViewport(desktopAccount, page)
  await desktopAccount.click()
  const lightMode = page.getByRole('button', { name: 'Light', exact: true })
  await lightMode.scrollIntoViewIfNeeded()
  await inViewport(lightMode, page)
  await lightMode.click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
})

test('phone dialogs fit long filenames and allow all form actions', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 320, height: 568 })
  await setup(page)
  await page.getByRole('button', { name: /Filter Languages/ }).click()
  const filter = page.getByRole('dialog', { name: 'Filter Active Languages' })
  await fitsWidth(filter)
  await inViewport(filter.getByRole('button', { name: 'Close dialog' }), page)
  await filter.getByRole('button', { name: /Apply Filter/ }).scrollIntoViewIfNeeded()
  await inViewport(filter.getByRole('button', { name: /Apply Filter/ }), page)
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('button', { name: 'Import Language File', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Import Language File', exact: true })
  await dialog.locator('input[type=file]').setInputFiles({ name: `${'language-pack-'.repeat(12)}.json`, mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({ language: { code: 'en' }, terms: [] })) })
  await expect(dialog.getByText(/language-pack-language-pack/)).toBeVisible()
  await fitsWidth(dialog)
  await expect(dialog.getByRole('button', { name: 'Upload Pack' })).toBeEnabled()
  await dialog.getByRole('button', { name: 'Upload Pack' }).scrollIntoViewIfNeeded()
  await inViewport(dialog.getByRole('button', { name: 'Upload Pack' }), page)
  await page.screenshot({ path: testInfo.outputPath('phone-import.png') })
  await dialog.getByRole('button', { name: 'Upload Pack' }).click()
  await expect(dialog.getByRole('alert')).toContainText('Fixture language pack imported')
})

test('selected details can be reached directly from phone results', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await setup(page)
  await page.getByLabel('Medication name', { exact: true }).fill('synthetic')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await page.getByRole('button', { name: new RegExp(`^${longName}`) }).click()
  await page.getByRole('link', { name: 'View medication details', exact: true }).click()
  await inViewport(page.locator('.workspace-selected h3'), page)
  await page.screenshot({ path: testInfo.outputPath('phone-details.png') })
})

test('phone layout remains usable with German labels and dark appearance', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 320, height: 568 })
  await setup(page)
  await page.getByRole('button', { name: 'English', exact: true }).click()
  await page.getByRole('button', { name: 'German de', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Medikamente', exact: true })).toBeVisible()
  await fitsWidth(page.locator('.workspace-header-inner'))
  await fitsWidth(page.locator('.workspace-search'))
  await page.getByRole('button', { name: 'Navigation öffnen' }).click()
  await page.getByRole('button', { name: 'Konto', exact: true }).click()
  await page.getByRole('button', { name: 'Dunkel', exact: true }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('.workspace-account [data-dropdown-panel]')).toHaveCSS('background-color', 'rgb(24, 25, 27)')
  await fitsWidth(page.locator('.workspace-sidebar'))
  await page.screenshot({ path: testInfo.outputPath('phone-dark-navigation.png'), animations: 'disabled' })
})
