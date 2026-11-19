import { test, expect, type Page } from '@playwright/test'

// Synthetic responses only. Hold parsed JSON to exercise races even when the
// browser has already received the response and abort alone cannot stop it.
declare global {
  interface Window {
    requestChecks: { path: string; aborted: boolean; blocked: boolean; release?: () => void }[]
  }
}

const medications = ['Fixture Alpha', 'Fixture Beta'].map((name, index) => ({
  name, language: 'EN', country: 'US', source_id: String(index),
  source_name: 'Test fixture', brand: null, type: 'ingredient', uploaded_at: '',
}))

async function fixture(page: Page) {
  await page.addInitScript(() => {
    window.requestChecks = []
    const originalFetch = window.fetch.bind(window)
    window.fetch = async (input, init) => {
      const path = new URL(input instanceof Request ? input.url : String(input), location.href).pathname
      if (path !== '/search' && path !== '/translate') return originalFetch(input, init)
      const signal = init?.signal ?? (input instanceof Request ? input.signal : undefined)
      const check: Window['requestChecks'][number] = { path, aborted: signal?.aborted ?? false, blocked: false }
      window.requestChecks.push(check)
      signal?.addEventListener('abort', () => { check.aborted = true }, { once: true })
      const response = await originalFetch(input, init)
      if (response.headers.get('X-Fixture-Hold') === 'body') {
        const readJson = response.json.bind(response)
        response.json = async () => {
          const data = await readJson()
          await new Promise<void>(resolve => {
            check.release = resolve
            check.blocked = true
          })
          return data
        }
      }
      return response
    }
  })
  await page.route('http://localhost:8000/**', async route => {
    const path = new URL(route.request().url()).pathname
    await route.fulfill({ json: path === '/languages'
      ? { languages: ['en', 'es', 'fr'] }
      : path === '/search' ? medications
      : { results: [{ translation: 'Current translation', brand: 'Fixture brand' }] },
    })
  })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Start with a medication name' })).toBeVisible()
}

async function search(page: Page, query = 'fixture') {
  await page.getByLabel('Medication name', { exact: true }).fill(query)
  await page.getByRole('button', { name: 'Search', exact: true }).click()
}

async function choose(page: Page, selector: string, code: string) {
  await page.locator(selector).click()
  await page.getByRole('option', { name: new RegExp(`\\(${code}\\)$`) }).click()
}

async function blocked(page: Page, index: number) {
  await expect.poll(() => page.evaluate(i => window.requestChecks[i]?.blocked, index)).toBe(true)
}

async function release(page: Page, index: number) {
  await page.evaluate(async i => {
    window.requestChecks[i].release?.()
    await new Promise(resolve => setTimeout(resolve, 0))
  }, index)
}

test('editing a pending search aborts the fetch and allows a new search', async ({ page }) => {
  await fixture(page)
  let finish: () => void = () => {}
  const pending = new Promise<void>(resolve => { finish = resolve })
  await page.route('**/search?*', async route => {
    if (new URL(route.request().url()).searchParams.get('term') === 'old') await pending
    await route.fulfill({ json: medications })
  })
  const started = page.waitForRequest('**/search?*')
  await search(page, 'old')
  await started
  const cancelled = page.waitForEvent('requestfailed', request => new URL(request.url()).pathname === '/search')
  await page.getByLabel('Medication name', { exact: true }).fill('new')
  await cancelled
  await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeEnabled()
  await expect(page.getByRole('heading', { name: 'Start with a medication name' })).toBeVisible()
  finish()
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.locator('.workspace-result-query')).toHaveText('for “new”')
  await expect(page.getByRole('alert')).toHaveCount(0)
})

for (const status of [200, 503]) for (const oldFinishesLast of [false, true]) {
  test(`late search ${status}, old finishes last=${oldFinishesLast}, preserves the current request`, async ({ page }) => {
    await fixture(page)
    await page.route('**/search?*', route => {
      const old = new URL(route.request().url()).searchParams.get('term') === 'old'
      return route.fulfill({ status: old ? status : 200, headers: { 'X-Fixture-Hold': 'body', 'Access-Control-Expose-Headers': 'X-Fixture-Hold' },
        json: old && status !== 200 ? { detail: 'Stale search failure' }
          : [{ ...medications[0], name: old ? 'Stale medication' : 'Current medication' }],
      })
    })
    await search(page, 'old')
    await blocked(page, 0)
    await search(page, 'new')
    await blocked(page, 1)
    expect(await page.evaluate(() => window.requestChecks[0].aborted)).toBe(true)
    if (!oldFinishesLast) {
      await release(page, 0)
      await expect(page.getByRole('heading', { name: 'Searching…' })).toBeVisible()
      await expect(page.getByRole('alert')).toHaveCount(0)
    }
    await release(page, 1)
    await expect(page.getByRole('button', { name: 'Current medication', exact: true })).toBeVisible()
    if (oldFinishesLast) await release(page, 0)
    await expect(page.getByRole('button', { name: 'Current medication', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Stale medication', exact: true })).toHaveCount(0)
    await expect(page.locator('.workspace-result-query')).toHaveText('for “new”')
    await expect(page.getByRole('alert')).toHaveCount(0)
  })
}

for (const status of [200, 503]) for (const oldFinishesLast of [false, true]) {
  test(`late translation ${status}, old finishes last=${oldFinishesLast}, preserves the current request`, async ({ page }) => {
    await fixture(page)
    await search(page)
    await page.route('**/translate', route => {
      const old = route.request().postDataJSON().term === 'Fixture Alpha'
      return route.fulfill({ status: old ? status : 200, headers: { 'X-Fixture-Hold': 'body', 'Access-Control-Expose-Headers': 'X-Fixture-Hold' },
        json: old && status !== 200 ? { detail: 'Stale translation failure' }
          : { results: [{ translation: old ? 'Stale translation' : 'Current translation' }] },
      })
    })
    await page.getByRole('button', { name: 'Fixture Alpha', exact: true }).click()
    await page.getByRole('button', { name: 'Translate', exact: true }).click()
    await blocked(page, 1)
    await page.getByRole('button', { name: 'Fixture Beta', exact: true }).click()
    await page.getByRole('button', { name: 'Translate', exact: true }).click()
    await blocked(page, 2)
    expect(await page.evaluate(() => window.requestChecks[1].aborted)).toBe(true)
    if (!oldFinishesLast) {
      await release(page, 1)
      await expect(page.locator('.workspace-details [aria-busy]')).toHaveAttribute('aria-busy', 'true')
      await expect(page.getByRole('alert')).toHaveCount(0)
    }
    await release(page, 2)
    await expect(page.locator('.workspace-translation-output')).toContainText('Current translation')
    if (oldFinishesLast) await release(page, 1)
    await expect(page.locator('.workspace-translation-output')).toContainText('Current translation')
    await expect(page.locator('.workspace-details')).not.toContainText('Stale translation')
    await expect(page.getByRole('alert')).toHaveCount(0)
  })
}

for (const destination of ['country', 'language']) {
  test(`changing target ${destination} cancels translation and supports retry`, async ({ page }) => {
    await fixture(page)
    await search(page)
    await page.route('**/translate', route => route.fulfill({ headers: { 'X-Fixture-Hold': 'body', 'Access-Control-Expose-Headers': 'X-Fixture-Hold' },
      json: { results: [{ translation: 'Destination translation' }] },
    }))
    await page.getByRole('button', { name: 'Fixture Alpha', exact: true }).click()
    await page.getByRole('button', { name: 'Translate', exact: true }).click()
    await blocked(page, 1)
    await choose(page, destination === 'country' ? '#target-country' : '#target-language', destination === 'country' ? 'ES' : 'FR')
    expect(await page.evaluate(() => window.requestChecks[1].aborted)).toBe(true)
    await release(page, 1)
    await expect(page.locator('.workspace-translation-output')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Translate', exact: true })).toBeEnabled()
    await page.getByRole('button', { name: 'Translate', exact: true }).click()
    await blocked(page, 2)
    await release(page, 2)
    await expect(page.locator('.workspace-translation-output')).toContainText(destination === 'country' ? 'ES · ES' : 'FR · FR')
    await expect(page.getByRole('alert')).toHaveCount(0)
  })
}

test('starting a new search aborts and clears an in-flight translation', async ({ page }) => {
  await fixture(page)
  await search(page)
  await page.route('**/translate', route => route.fulfill({ headers: { 'X-Fixture-Hold': 'body', 'Access-Control-Expose-Headers': 'X-Fixture-Hold' },
    json: { results: [{ translation: 'Stale translation' }] },
  }))
  await page.getByRole('button', { name: 'Fixture Alpha', exact: true }).click()
  await page.getByRole('button', { name: 'Translate', exact: true }).click()
  await blocked(page, 1)
  await search(page, 'new')
  expect(await page.evaluate(() => window.requestChecks[1].aborted)).toBe(true)
  await release(page, 1)
  await expect(page.getByRole('heading', { name: 'Select a medication', exact: true })).toBeVisible()
  await expect(page.locator('.workspace-translation-output')).toHaveCount(0)
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('current translation failures still show feedback and allow retry', async ({ page }) => {
  await fixture(page)
  await search(page)
  await page.getByRole('button', { name: 'Fixture Alpha', exact: true }).click()
  await page.route('**/translate', route => route.fulfill({ status: 503, json: { detail: 'Current service failure' } }))
  await page.getByRole('button', { name: 'Translate', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Current service failure')
  await expect(page.getByRole('button', { name: 'Translate', exact: true })).toBeEnabled()
  await page.route('**/translate', route => route.fulfill({ json: { results: [{ translation: 'Retried translation' }] } }))
  await page.getByRole('button', { name: 'Translate', exact: true }).click()
  await expect(page.locator('.workspace-translation-output')).toContainText('Retried translation')
  await expect(page.getByRole('alert')).toHaveCount(0)
})
