const fs = require('fs');
const path = require('path');

function searchDir(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.name === 'node_modules' || entry.name === '.git' || entry.name === '__pycache__' || entry.name === '.gemini' || entry.name === 'yarn.lock' || entry.name === 'package-lock.json') continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      searchDir(full);
    } else {
      try {
        const txt = fs.readFileSync(full, 'utf8');
        const matches = txt.match(/https?:\/\/[^\s"'<>`)]+/g);
        if (matches) {
          for (const m of matches) {
            if (!m.includes('w3.org') && !m.includes('github') && !m.includes('leaflet') && !m.includes('lucide') && !m.includes('schema.org') && !m.includes('unpkg') && !m.includes('openstreetmap') && !m.includes('registry.npmjs')) {
              console.log(`${full}: ${m}`);
            }
          }
        }
      } catch (e) {}
    }
  }
}

searchDir('.');
