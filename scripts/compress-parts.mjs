// Convert the PNG/JPEG textures packed in exported part GLBs to KTX2 (Basis
// Universal), so they stay small on disk and on the GPU.
//   node scripts/compress-parts.mjs [file.glb ...]     (default: every GLB under apps/web/public/parts)
// Base colour and ORM use ETC1S (small); normal maps use UASTC, which keeps their relief clean
// (KTX2_NORMAL=etc1s encodes them as ETC1S too: about a quarter of the size, a little blockier).
// Needs the `basisu` encoder: set BASISU=/path/to/basisu, put it on PATH, or
// `npm i --no-save basisu` (prebuilt binaries). Already-compressed GLBs are skipped.
// Vertex data is quantised too (KHR_mesh_quantization: 16-bit positions and UVs,
// 8-bit normals), which roughly halves the geometry. three.js and Blender read it natively.
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, KHRMeshQuantization, KHRTextureBasisu } from '@gltf-transform/extensions';
import { quantize } from '@gltf-transform/functions';

const PARTS = resolve('apps/web/public/parts');

function findBasisu() {
  const candidates = [
    process.env.BASISU,
    resolve('node_modules/basisu/bin', process.platform === 'darwin' ? 'darwin' : process.platform === 'win32' ? 'win' : 'linux', process.arch === 'arm64' ? 'arm64' : 'x64', 'basisu'),
  ].filter(Boolean);
  for (const c of candidates) if (existsSync(c)) return c;
  try {
    execFileSync('basisu', ['-version'], { stdio: 'ignore' });
    return 'basisu';
  } catch {
    throw new Error('No basisu encoder found: set BASISU, put basisu on PATH, or run `npm i --no-save basisu`.');
  }
}

const walk = (dir) =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : p.endsWith('.glb') ? [p] : [];
  });

const basisu = findBasisu();
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const files = process.argv.slice(2).length ? process.argv.slice(2).map((f) => resolve(f)) : walk(PARTS);
const work = mkdtempSync(join(tmpdir(), 'ktx2-'));

try {
  for (const file of files) {
    const doc = await io.read(file);
    const root = doc.getRoot();
    const textures = root.listTextures().filter((t) => t.getMimeType() !== 'image/ktx2');
    const quantised = root.listExtensionsUsed().some((e) => e.extensionName === KHRMeshQuantization.EXTENSION_NAME);
    if (!textures.length && quantised) continue;
    // How each texture is used decides its colour space and codec.
    const role = new Map();
    for (const m of root.listMaterials()) {
      if (m.getBaseColorTexture()) role.set(m.getBaseColorTexture(), 'color');
      for (const t of [m.getMetallicRoughnessTexture(), m.getOcclusionTexture()]) if (t) role.set(t, 'data');
      if (m.getNormalTexture()) role.set(m.getNormalTexture(), 'normal');
    }
    const before = statSync(file).size;
    for (const [i, tex] of textures.entries()) {
      const ext = tex.getMimeType() === 'image/jpeg' ? 'jpg' : 'png';
      const src = join(work, `t${i}.${ext}`);
      const dst = join(work, `t${i}.ktx2`);
      writeFileSync(src, tex.getImage());
      const args = ['-ktx2', '-mipmap', src, '-output_file', dst];
      if (role.get(tex) === 'normal' && process.env.KTX2_NORMAL === 'etc1s') args.unshift('-q', '255', '-linear', '-normal_map');
      else if (role.get(tex) === 'normal') args.unshift('-uastc', '-uastc_level', '2', '-uastc_rdo_l', '2', '-linear', '-normal_map');
      else if (role.get(tex) === 'data') args.unshift('-q', '255', '-linear');
      else args.unshift('-q', process.env.KTX2_BASE_Q ?? '200');
      execFileSync(basisu, args, { stdio: 'ignore' });
      tex.setImage(new Uint8Array(readFileSync(dst))).setMimeType('image/ktx2');
      if (tex.getURI()) tex.setURI(tex.getURI().replace(/\.(png|jpe?g)$/i, '.ktx2'));
    }
    if (textures.length) doc.createExtension(KHRTextureBasisu).setRequired(true);
    if (!quantised && root.listMeshes().length) await doc.transform(quantize({ quantizePosition: 16, quantizeNormal: 8, quantizeTexcoord: 16 }));
    await io.write(file, doc);
    console.log(`${file.replace(`${resolve('.')}/`, '')}: ${(before / 1024).toFixed(0)} KB -> ${(statSync(file).size / 1024).toFixed(0)} KB`);
  }
} finally {
  rmSync(work, { recursive: true, force: true });
}
