/**
 * korea_swim 포트폴리오용 스크린샷 촬영 스크립트
 */

import { chromium } from 'playwright';
import path from 'path';
import fs from 'fs';

const BASE_URL = 'https://korea-swim.onrender.com';
const OUTPUT_DIR = path.join(__dirname, '..', 'screenshots');

async function main() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }
  if (!fs.existsSync(path.join(OUTPUT_DIR, 'pc'))) {
    fs.mkdirSync(path.join(OUTPUT_DIR, 'pc'), { recursive: true });
  }
  if (!fs.existsSync(path.join(OUTPUT_DIR, 'mobile'))) {
    fs.mkdirSync(path.join(OUTPUT_DIR, 'mobile'), { recursive: true });
  }

  console.log('🏊 korea_swim 스크린샷 촬영 시작...');
  console.log(`🌐 URL: ${BASE_URL}`);
  console.log('⏳ Render 무료 플랜이라 서버 깨우는 중... (최대 30초)');

  const browser = await chromium.launch({ headless: true });

  // PC 스크린샷
  console.log('\n🖥️ PC 스크린샷...');
  const pcContext = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  const pcPage = await pcContext.newPage();

  try {
    await pcPage.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 60000 });
    await pcPage.waitForTimeout(3000);

    await pcPage.screenshot({ path: path.join(OUTPUT_DIR, 'pc', '01_main.png') });
    console.log('   ✅ 01_main.png');

    // 지도 확대/필터 조작 시도
    await pcPage.waitForTimeout(2000);
    await pcPage.screenshot({ path: path.join(OUTPUT_DIR, 'pc', '02_map_loaded.png') });
    console.log('   ✅ 02_map_loaded.png');

  } catch (e) {
    console.log(`   ❌ PC 촬영 실패: ${e}`);
  }
  await pcContext.close();

  // 모바일 스크린샷
  console.log('\n📱 모바일 스크린샷...');
  const mobileContext = await browser.newContext({
    viewport: { width: 430, height: 932 },
    deviceScaleFactor: 2,
    isMobile: true,
  });
  const mobilePage = await mobileContext.newPage();

  try {
    await mobilePage.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 60000 });
    await mobilePage.waitForTimeout(3000);

    await mobilePage.screenshot({ path: path.join(OUTPUT_DIR, 'mobile', '01_main.png') });
    console.log('   ✅ 01_main.png');

  } catch (e) {
    console.log(`   ❌ 모바일 촬영 실패: ${e}`);
  }
  await mobileContext.close();

  await browser.close();
  console.log('\n🎉 스크린샷 완료!');
  console.log(`📁 Output: ${OUTPUT_DIR}`);
}

main().catch(console.error);
