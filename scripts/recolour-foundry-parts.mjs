// Recolour the base-colour textures of a composite walker's part GLBs to the Brute's scheme (tools/recolour/foundry_palette.py).
//   node scripts/recolour-foundry-parts.mjs IN_DIR/glb OUT_DIR/glb
// Reads every .glb in IN_DIR (the build.py output, PNG textures, before compress-parts), writes the same files with recoloured
// base-colour textures to OUT_DIR. Roughness, metal and normals are untouched. Then publish OUT_DIR as usual:
//   node scripts/publish-composite.mjs OUT_DIR/glb artillery && node scripts/compress-parts.mjs <files it prints>
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';

const [inDir, outDir] = process.argv.slice(2).map((p) => resolve(p));
if (!inDir || !outDir) throw new Error('usage: recolour-foundry-parts.mjs IN_DIR OUT_DIR');
mkdirSync(outDir, { recursive: true });
const script = resolve('tools/recolour/foundry_palette.py');
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const work = mkdtempSync(join(tmpdir(), 'recolour-'));
try {
  for (const f of readdirSync(inDir).filter((n) => n.endsWith('.glb'))) {
    const doc = await io.read(join(inDir, f));
    for (const [i, mat] of doc.getRoot().listMaterials().entries()) {
      const tex = mat.getBaseColorTexture();
      if (!tex) continue;
      if (tex.getMimeType() !== 'image/png') throw new Error(`${f}: ${mat.getName()} base colour is ${tex.getMimeType()}; recolour before compress-parts`);
      const src = join(work, `${f}.${i}.png`);
      const dst = join(work, `${f}.${i}.out.png`);
      writeFileSync(src, tex.getImage());
      execFileSync('python3', ['-I', script, src, dst], { stdio: 'inherit' });
      tex.setImage(new Uint8Array(readFileSync(dst)));
    }
    await io.write(join(outDir, f), doc);
    console.log(f);
  }
} finally {
  rmSync(work, { recursive: true, force: true });
}
