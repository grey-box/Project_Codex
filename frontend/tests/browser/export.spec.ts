import { test, expect, type Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'

const medication = [
  {
    generic_name: 'Alpha, vitamin',
    brand_name: 'Марка',
    country: 'US',
    original_language: 'English',
    translated_language: 'Russian',
  },
]

const clinical = [
  {
    conceptID: 'fixture-id',
    ds: 'Synthetic fixture',
    name: 'Alpha condition',
    code: '1A00',
    system: 'ICD-11',
  },
]

async function fixture(page: Page) {
  await page.route('http://localhost:8000/**', async route => {
    const url = new URL(route.request().url())
    if (url.pathname === '/languages') {
      await route.fulfill({ json: { languages: ['en', 'es', 'fr', 'ru', 'uk'] } })
      return
    }
    if (url.pathname.includes('csv') || url.pathname.includes('export')) {
      const isClinical =
          url.searchParams.get('report_type') === 'clinical' ||
          url.searchParams.get('source') === 'icd11' ||
          url.pathname.includes('clinical')
      const rows = isClinical ? clinical : medication
      await route.fulfill({ json: { csv: rows, records: rows, results: rows, row_count: 1 } })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/')
  if (page.viewportSize()!.width < 768) {
    await page.getByRole('button', { name: 'Open navigation', exact: true }).click()
  }
  await page.getByRole('button', { name: 'Export data', exact: true }).click()
}

test('export filters and selected columns reach the downloaded CSV with Unicode intact', async ({ page }) => {
  await fixture(page)
  await page.getByRole('button', { name: 'Brand', exact: true }).click()
  await page.getByLabel('Start name', { exact: true }).fill(' Alpha ')
  await page.getByLabel('End name', { exact: true }).fill('Zulu')

  const dialog = page.getByRole('dialog', { name: 'Export data', exact: true })
  await dialog.getByRole('button', { name: 'Search', exact: true }).click()

  for (const column of ['country', 'original_language', 'translated_language']) {
    await page.getByLabel(column, { exact: true }).uncheck()
  }

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  const file = await download

  expect(file.suggestedFilename()).toBe('medications-rxnorm-brand.csv')
  expect(await readFile((await file.path())!, 'utf8')).toBe('\uFEFFgeneric_name,brand_name\r\n"Alpha, vitamin",Марка')
  await expect(dialog.getByRole('status').last()).toContainText('Rows exported: 1')
})

test('report type selection swaps five columns and preserves clinical property names', async ({ page }) => {
  await fixture(page)
  await page.getByRole('combobox', { name: 'Report type', exact: true }).click()
  await page.getByRole('option', { name: 'Clinical Findings', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Brand', exact: true })).toHaveCount(0)

  const dialog = page.getByRole('dialog', { name: 'Export data', exact: true })
  await dialog.getByRole('button', { name: 'Search', exact: true }).click()

  await expect(page.getByRole('checkbox')).toHaveCount(5)
  await expect(page.getByLabel('generic_name', { exact: true })).toHaveCount(0)
  for (const column of ['conceptID', 'ds', 'name', 'code', 'system']) {
    await expect(page.getByLabel(column, { exact: true })).toBeChecked()
  }

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  const file = await download

  expect(file.suggestedFilename()).toBe('clinical-icd11.csv')
  expect(await readFile((await file.path())!, 'utf8')).toBe(
      '\uFEFFconceptID,ds,name,code,system\r\nfixture-id,Synthetic fixture,Alpha condition,1A00,ICD-11',
  )
})

test('empty selection and reversed range prevent requests; empty result shows a toast', async ({ page }) => {
  let requests = 0
  await fixture(page)

  const dialog = page.getByRole('dialog', { name: 'Export data', exact: true })
  await page.getByLabel('Start name', { exact: true }).fill('Zulu')
  await page.getByLabel('End name', { exact: true }).fill('Alpha')

  await page.route('http://localhost:8000/**', async route => {
    const url = new URL(route.request().url())
    if (url.pathname !== '/languages') requests++
    await route.fulfill({ json: { csv: [], records: [], results: [], row_count: 0 } })
  })

  await dialog.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByLabel('End name', { exact: true })).toHaveAttribute('aria-invalid', 'true')
  expect(requests).toBe(0)

  await page.getByLabel('End name', { exact: true }).fill('Zulu')
  await dialog.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('No records matched')
  expect(requests).toBe(1)

  // Verify empty column selection disables Download CSV
  await page.route('http://localhost:8000/**', async route => {
    await route.fulfill({ json: { csv: medication, records: medication, results: medication, row_count: 1 } })
  })
  await dialog.getByRole('button', { name: 'Search', exact: true }).click()
  await page.getByRole('button', { name: 'Deselect All', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Download CSV', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Select All', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Download CSV', exact: true })).toBeEnabled()
})

test('failed search keeps settings and permits retry', async ({ page }) => {
  await fixture(page)
  const dialog = page.getByRole('dialog', { name: 'Export data', exact: true })
  await page.getByLabel('Start name', { exact: true }).fill('Alpha')

  await page.route('http://localhost:8000/**', route =>
      route.fulfill({ status: 500, json: { detail: 'Synthetic export outage' } }),
  )
  await dialog.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Synthetic export outage')
  await expect(page.getByLabel('Start name', { exact: true })).toHaveValue('Alpha')

  await page.route('http://localhost:8000/**', route =>
      route.fulfill({ json: { csv: medication, records: medication, results: medication, row_count: 1 } }),
  )
  await dialog.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveCount(0)

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  await download
})

for (const width of [320, 390, 1440]) {
  for (const theme of ['light', 'dark']) {
    test(`export dialog fits ${width}px in ${theme} mode and returns focus`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 844 })
      await page.addInitScript(mode => localStorage.setItem('codex-theme', mode), theme)
      await fixture(page)
      const dialog = page.getByRole('dialog', { name: 'Export data', exact: true })
      const bounds = await dialog.boundingBox()
      expect(bounds!.x).toBeGreaterThanOrEqual(0)
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width)
      expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
      await page.screenshot({ path: testInfo.outputPath(`export-${width}-${theme}.png`), animations: 'disabled' })
      await page.getByRole('button', { name: 'Cancel', exact: true }).click()
      await expect(dialog).toHaveCount(0)
      await expect(page.getByRole('button', { name: 'Export data', exact: true })).toBeFocused()
    })
  }
}