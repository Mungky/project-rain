// Nuclear fix: replace ALL Bun-managed packages with real directories
const fs = require('fs');
const path = require('path');

const ROOT_BUN = path.join(__dirname, '..', '..', '..', 'node_modules', '.bun');
const NM = path.join(__dirname, '..', 'node_modules');

if (!fs.existsSync(ROOT_BUN)) {
  console.log('[copy-deps] No .bun store, skipping');
  process.exit(0);
}

let copied = 0, failed = 0;

for (const storeDir of fs.readdirSync(ROOT_BUN, { withFileTypes: true })) {
  if (!storeDir.isDirectory()) continue;

  // Parse "@scope+pkg@version" → "@scope/pkg"  or  "pkg@version" → "pkg"
  const raw = storeDir.name;
  const atIndex = raw.lastIndexOf('@');
  if (atIndex <= 0) continue;
  const pkgName = raw.substring(0, atIndex).replace(/\+/g, '/');

  const srcPkg = path.join(ROOT_BUN, storeDir.name, 'node_modules', ...pkgName.split('/'));
  if (!fs.existsSync(srcPkg)) continue;

  const dstPkg = path.join(NM, ...pkgName.split('/'));

  try {
    // Always replace — symlink or not
    fs.mkdirSync(path.dirname(dstPkg), { recursive: true });
    if (fs.existsSync(dstPkg)) fs.rmSync(dstPkg, { recursive: true, force: true });
    fs.cpSync(srcPkg, dstPkg, { recursive: true, dereference: true });
    copied++;
  } catch (e) {
    console.error(`[copy-deps] FAIL: ${pkgName} — ${e.message}`);
    failed++;
  }
}

console.log(`[copy-deps] done — ${copied} copied, ${failed} failed`);
