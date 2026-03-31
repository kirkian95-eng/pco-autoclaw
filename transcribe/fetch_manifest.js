#!/usr/bin/env node
// Fetches a guest JWT from Subsplash and builds a manifest of all sermons.
// Output: manifest.json in the project directory.
//
// Prerequisites: playwright (npx playwright install chromium)
//
// Usage:
//   SUBSPLASH_APP_KEY=YOUR_KEY node fetch_manifest.js
//   # or edit APP_KEY below

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const APP_KEY = process.env.SUBSPLASH_APP_KEY || 'CHANGE_ME';
const MANIFEST_PATH = path.join(__dirname, 'manifest.json');

if (APP_KEY === 'CHANGE_ME') {
  console.error('Set SUBSPLASH_APP_KEY env var or edit APP_KEY in this script.');
  console.error('Find your app key in any Subsplash embed URL: subsplash.com/u/-APPKEY/...');
  process.exit(1);
}

async function getToken() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  // Use any published media item's embed URL to get a guest JWT
  // You may need to replace the short_code with a valid one from your church
  await page.goto(
    `https://subsplash.com/u/-${APP_KEY}/media`,
    { waitUntil: 'networkidle', timeout: 30000 }
  );
  const content = await page.content();
  await browser.close();

  const match = content.match(/eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/);
  if (!match) throw new Error('Could not extract guest JWT');
  return match[0];
}

async function fetchAllItems(token) {
  const items = [];
  let pageNum = 1;
  const pageSize = 50;

  while (true) {
    const url = `https://core.subsplash.com/media/v1/media-items?filter%5Bapp_key%5D=${APP_KEY}&filter%5Bstatus%5D=published&page%5Bnumber%5D=${pageNum}&page%5Bsize%5D=${pageSize}&sort=-position`;
    const resp = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resp.ok) throw new Error(`API ${resp.status}: ${await resp.text()}`);
    const data = await resp.json();
    const batch = data._embedded?.['media-items'] || [];
    if (batch.length === 0) break;
    items.push(...batch);
    if (batch.length < pageSize) break;
    pageNum++;
  }
  return items;
}

(async () => {
  console.log('Getting guest token...');
  const token = await getToken();

  console.log('Fetching sermon list...');
  const items = await fetchAllItems(token);
  console.log(`Found ${items.length} sermons`);

  const manifest = items.map((item) => ({
    id: item.id,
    title: item.title,
    date: item.date?.substring(0, 10) || '',
    speaker: item.speaker || '',
    short_code: item.short_code,
    slug: item.slug,
    audio_id: item._embedded?.audio?.id || null,
  }));

  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2));
  console.log(`Manifest saved: ${MANIFEST_PATH} (${manifest.length} entries)`);

  const withAudio = manifest.filter((m) => m.audio_id);
  const withoutAudio = manifest.filter((m) => !m.audio_id);
  console.log(`  With audio: ${withAudio.length}`);
  if (withoutAudio.length > 0) {
    console.log(`  Without audio: ${withoutAudio.length}`);
    withoutAudio.forEach((m) => console.log(`    - ${m.date} ${m.title}`));
  }
})();
