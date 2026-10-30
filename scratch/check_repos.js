const fs = require('fs');
const s = fs.readFileSync('C:/Users/91967/.gemini/antigravity/brain/d7e68e31-f7d9-45f2-b3f8-a0509024b26c/.system_generated/steps/7696/content.md', 'utf8');
const re = /href="\/shruthisree610\/([^"/]+)"/g;
let m;
const repos = new Set();
while ((m = re.exec(s)) !== null) {
  repos.add(m[1]);
}
console.log('Repositories:', Array.from(repos));
