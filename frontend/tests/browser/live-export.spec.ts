import { test, expect } from '@playwright/test'
import { mkdir, readFile } from 'node:fs/promises'
import path from 'node:path'

test('live Initial Data export downloads a filtered CSV from the local Neo4j-backed API', async ({ page }, testInfo) => {
  test.skip(!process.env.CODEX_LIVE_EXPORT_URL, 'Opt-in check against a running local API, without intercepted data.')
  test.setTimeout(60000)
  const artifacts = process.env.CODEX_EXPORT_ARTIFACT_DIR || testInfo.outputPath('live-export')
  await mkdir(artifacts, { recursive: true })
  await page.addInitScript(() => { localStorage.setItem('codex-theme', 'dark'); localStorage.setItem('i18nextLng', 'en') })
  await page.goto(process.env.CODEX_LIVE_EXPORT_URL!)
  await expect(page.getByRole('complementary', { name: 'Workspace tools', exact: true }).getByRole('button', { name: 'Export data', exact: true })).toBeVisible()
  await page.screenshot({ path: path.join(artifacts, 'export-sidebar.png'), animations: 'disabled' })
  await page.getByRole('button', { name: 'Export data', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Export medications', exact: true })
  await page.getByRole('combobox', { name: 'Dataset', exact: true }).click()
  await page.getByRole('option', { name: 'RxNorm', exact: true }).click()
  await expect(dialog.getByRole('checkbox')).toHaveCount(5)
  await page.screenshot({ path: path.join(artifacts, 'export-rxnorm.png'), animations: 'disabled' })
  await page.getByRole('combobox', { name: 'Dataset', exact: true }).click()
  await page.getByRole('option', { name: 'Initial Data', exact: true }).click()
  await page.getByLabel('Start medication name', { exact: true }).fill('ibuprofen')
  await page.getByLabel('End medication name', { exact: true }).fill('ibuprofen')
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download CSV', exact: true }).click()
  const file = await download
  await file.saveAs(path.join(artifacts, file.suggestedFilename()))
  const csv = await readFile((await file.path())!, 'utf8')
  expect(csv).toMatch(/^\uFEFFgeneric_name,brand_name,country,original_language,translated_language\r\n/i)
  expect(csv.toLowerCase()).toContain('ibuprofen')
  expect(csv.toLowerCase()).not.toContain('paracetamol')
  await expect(dialog.getByRole('status')).toContainText('Rows exported:')
  await page.screenshot({ path: path.join(artifacts, 'export-initial-data.png'), animations: 'disabled' })
})
