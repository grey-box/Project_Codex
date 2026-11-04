import { test, expect, type Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'
const initial = [{ generic_name: 'Alpha, vitamin', brand_name: 'Марка', country: 'US', original_language: 'English', translated_language: 'Russian' }]
const rxnorm = [{ conceptID: 'fixture-id', ds: 'Synthetic fixture', name: 'Alpha brand', rxcui: '123', tty: 'BN' }]
async function fixture(page: Page) {
  await page.route('http://localhost:8000/**', async route => {
    const url = new URL(route.request().url())
    await route.fulfill({ json: url.pathname === '/languages' ? { languages: ['en', 'es', 'fr', 'ru', 'uk'] } : url.pathname === '/csv' ? { csv: url.searchParams.get('source') === 'rxnorm' ? rxnorm : initial, row_count: 1 } : [] })
  })
  await page.goto('/')
  if (page.viewportSize()!.width < 768) await page.getByRole('button', { name: 'Open navigation', exact: true }).click()
  await page.getByRole('button', { name: 'Export data', exact: true }).click()
}

test('export filters and selected columns reach the downloaded CSV with Unicode intact', async ({ page }) => {
  await fixture(page)
  await page.getByRole('button', { name: 'Brand', exact: true }).click()
  await page.getByLabel('Start medication name', { exact: true }).fill(' Alpha ')
  await page.getByLabel('End medication name', { exact: true }).fill('Zulu')
  for (const column of ['country', 'original_language', 'translated_language']) await page.getByLabel(column, { exact: true }).uncheck()
  const request = page.waitForRequest('**/csv?*'), download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  expect(Object.fromEntries(new URL((await request).url()).searchParams)).toEqual({ source: 'demo', name_type: 'brand', start_name: 'Alpha', end_name: 'Zulu' })
  const file = await download
  expect(file.suggestedFilename()).toBe('medications-initial-data-brand.csv')
  expect(await readFile((await file.path())!, 'utf8')).toBe('\uFEFFgeneric_name,brand_name\r\n"Alpha, vitamin",Марка')
  await expect(page.getByRole('dialog').getByRole('status')).toContainText('Rows exported: 1')
})

test('dataset selection swaps five columns and preserves RxNorm property names', async ({ page }) => {
  await fixture(page)
  await page.getByRole('combobox', { name: 'Dataset', exact: true }).click()
  await page.getByRole('option', { name: 'RxNorm', exact: true }).click()
  await expect(page.getByRole('checkbox')).toHaveCount(5)
  await expect(page.getByLabel('generic_name', { exact: true })).toHaveCount(0)
  for (const column of ['conceptID', 'ds', 'name', 'rxcui', 'tty']) await expect(page.getByLabel(column, { exact: true })).toBeChecked()
  await page.getByRole('button', { name: 'Brand', exact: true }).click()
  const request = page.waitForRequest('**/csv?*'), download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  expect(new URL((await request).url()).searchParams.get('source')).toBe('rxnorm')
  expect(await readFile((await (await download).path())!, 'utf8')).toBe('\uFEFFconceptID,ds,name,rxcui,tty\r\nfixture-id,Synthetic fixture,Alpha brand,123,BN')
})

test('empty selection and reversed range prevent requests; empty result shows a toast', async ({ page }) => {
  let requests = 0
  await fixture(page)
  await page.route('**/csv?*', async route => { requests++; await route.fulfill({ json: { csv: [], row_count: 0 } }) })
  await page.getByRole('button', { name: 'Deselect All', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Download CSV', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Select All', exact: true }).click()
  await page.getByLabel('Start medication name', { exact: true }).fill('Zulu')
  await page.getByLabel('End medication name', { exact: true }).fill('Alpha')
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  await expect(page.getByLabel('End medication name', { exact: true })).toHaveAttribute('aria-invalid', 'true')
  expect(requests).toBe(0)
  await page.getByLabel('End medication name', { exact: true }).fill('Zulu')
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('No medications match')
  expect(requests).toBe(1)
})

test('failed export keeps settings and permits retry', async ({ page }) => {
  await fixture(page)
  await page.getByLabel('Start medication name', { exact: true }).fill('Alpha')
  await page.route('**/csv?*', route => route.fulfill({ status: 500, json: { detail: 'Synthetic export outage' } }))
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Synthetic export outage')
  await expect(page.getByLabel('Start medication name', { exact: true })).toHaveValue('Alpha')
  await page.route('**/csv?*', route => route.fulfill({ json: { csv: initial, row_count: 1 } }))
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  await download
  await expect(page.getByRole('alert')).toHaveCount(0)
})

for (const width of [320, 390, 1440]) for (const theme of ['light', 'dark']) {
  test(`export dialog fits ${width}px in ${theme} mode and returns focus`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 844 })
    await page.addInitScript(mode => localStorage.setItem('codex-theme', mode), theme)
    await fixture(page)
    const dialog = page.getByRole('dialog', { name: 'Export medications', exact: true }), bounds = await dialog.boundingBox()
    expect(bounds!.x).toBeGreaterThanOrEqual(0)
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width)
    expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
    await page.screenshot({ path: testInfo.outputPath(`export-${width}-${theme}.png`), animations: 'disabled' })
    await page.getByRole('button', { name: 'Cancel', exact: true }).click()
    await expect(dialog).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Export data', exact: true })).toBeFocused()
  })
}
