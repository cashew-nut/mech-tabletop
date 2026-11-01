// Loads the Blender-made board kit (hex tiles, towers, walls, props) from public/board/*.glb.
// Each piece has baked vertex colours, so one shared Lambert material draws them all.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { towerFooting } from './boardArt';

export const KIT_PIECES = [
  'tile_plain_1', 'tile_plain_2', 'tile_cracked_3', 'tile_slab_4', 'tile_moss_5', 'tile_rough_6', 'tile_rubble_7', 'tile_plate_8', 'tile_scorched_9',
  'tower_spire', 'tower_chimney', 'tower_ruined', 'wall_arched', 'wall_long', 'wall_low', 'crate', 'rubble_pile',
] as const;
/** Meshy-made hero scenery (textured, with its own material). Optional: the procedural pieces stand in when a file is missing. */
export const HERO_PIECES = ['hero_tower', 'hero_chimney', 'hero_wall'] as const;
export type KitPiece = (typeof KIT_PIECES)[number] | (typeof HERO_PIECES)[number];

/** Pieces with simplified copies (<piece>_lod1.glb, _lod2.glb; made by scripts/board-lod.mjs). The loader swaps them in by distance
 * from the camera; the board camera sits 20 or so units from the action, so the near half of the board keeps full detail. */
export const LOD_PIECES: readonly KitPiece[] = ['hero_tower', 'hero_chimney', 'hero_wall', 'tower_spire', 'tower_chimney', 'tower_ruined', 'wall_arched', 'wall_long'];
/** Camera distances at which each lower level takes over. `?lod=off` shows only full detail, `?lod=1` or `?lod=2` forces a level (for review renders). */
const LOD_AT = [24, 36];
const LOD_MODE = new URLSearchParams(location.search).get('lod');

export interface Kit {
  /** A fresh instance of the piece; geometry and material are shared, so instances are cheap. */
  make: (piece: KitPiece) => THREE.Group;
  /** Whether the piece loaded (hero pieces are optional). */
  has: (piece: KitPiece) => boolean;
}

/** Grain, pitting and hairline cracks over the baked vertex colours: a generated granite texture projected from three axes
 * in world space, so every tile and wall shares one continuous surface and adjacent pieces never show a seam. */
function addStoneDetail(material: THREE.Material, detail: THREE.Texture) {
  detail.wrapS = detail.wrapT = THREE.RepeatWrapping;
  detail.anisotropy = 4;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uDetail = { value: detail };
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vWPos;\nvarying vec3 vWNrm;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWPos = (modelMatrix * vec4(position, 1.0)).xyz;\nvWNrm = normalize(mat3(modelMatrix) * normal);');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform sampler2D uDetail;\nvarying vec3 vWPos;\nvarying vec3 vWNrm;')
      .replace(
        '#include <color_fragment>',
        `#include <color_fragment>
        {
          vec3 w = pow(abs(normalize(vWNrm)), vec3(4.0));
          w /= (w.x + w.y + w.z);
          float d = texture2D(uDetail, vWPos.zy * 0.6).r * w.x + texture2D(uDetail, vWPos.xz * 0.6).r * w.y + texture2D(uDetail, vWPos.xy * 0.6).r * w.z;
          diffuseColor.rgb *= mix(1.0, d * 1.7, 0.8);
        }`,
      );
  };
  material.customProgramCacheKey = () => 'board-stone-detail';
}

/** Plain stone for footings: the board's grey with the same world-space grain and cracks as the kit. */
function footingMaterial(detail: THREE.Texture, colour: number) {
  const m = new THREE.MeshStandardMaterial({ color: colour, roughness: 0.95, metalness: 0 });
  addStoneDetail(m, detail);
  return m;
}

let loading: Promise<Kit | null> | null = null;

export function loadBoardKit(): Promise<Kit | null> {
  return (loading ??= (async () => {
    try {
      const loader = new GLTFLoader();
      const material = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0, color: 0xa8a8a8 });
      const base = `${import.meta.env.BASE_URL}board/`;
      const detail = new THREE.TextureLoader().load(`${base}stone_detail.jpg`);
      addStoneDetail(material, detail);
      const loaded = await Promise.all(KIT_PIECES.map((name) => loader.loadAsync(`${base}${name}.glb`)));
      const pieces = new Map<string, THREE.Object3D>();
      /** Give every mesh of a loaded kit piece the shared material and its baked colours. */
      const dress = (scene: THREE.Object3D, m: THREE.Material) =>
        scene.traverse((o) => {
          const mesh = o as THREE.Mesh;
          if (mesh.isMesh) {
            mesh.material = m;
            // Blender exports our baked colours as the second colour set (COLOR_1) and a blank white one as COLOR_0; use the baked set.
            const baked = mesh.geometry.getAttribute('color_1');
            if (baked) {
              mesh.geometry.setAttribute('color', baked);
              mesh.geometry.deleteAttribute('color_1');
            }
            mesh.castShadow = true;
            mesh.receiveShadow = true;
          }
        });
      loaded.forEach((gltf, i) => {
        dress(gltf.scene, material);
        pieces.set(KIT_PIECES[i], gltf.scene);
      });
      const heroes = await Promise.allSettled(HERO_PIECES.map((name) => loader.loadAsync(`${base}${name}.glb`)));
      heroes.forEach((r, i) => {
        if (r.status !== 'fulfilled') return;
        r.value.scene.traverse((o) => {
          const mesh = o as THREE.Mesh;
          if (mesh.isMesh) {
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            // The bell tower came back near-white: grade it to the board's stone and give it the same grain and cracks.
            if (HERO_PIECES[i] === 'hero_tower') {
              const m = mesh.material as THREE.MeshStandardMaterial;
              m.color.setHex(0xa8a5a0);
              addStoneDetail(m, detail);
            }
          }
        });
        pieces.set(HERO_PIECES[i], r.value.scene);
      });
      // Chunky footings for the Meshy towers, whose own buttresses are ragged fins.
      const footings: Partial<Record<KitPiece, THREE.Group>> = {};
      if (pieces.has('hero_tower')) footings.hero_tower = towerFooting(footingMaterial(detail, 0x625f5a), 0.645, 8);
      if (pieces.has('hero_chimney')) footings.hero_chimney = towerFooting(footingMaterial(detail, 0x3d302c), 0.7, 16, false);
      // Distance LODs. Kit LODs share the piece's material; hero LODs are vertex-coloured copies (their texture atlas cannot be simplified).
      const lods = LOD_MODE === 'off' ? [] : LOD_PIECES;
      await Promise.all(
        lods.map(async (name) => {
          const high = pieces.get(name);
          if (!high) return;
          const levels = await Promise.allSettled([1, 2].map((n) => loader.loadAsync(`${base}${name}_lod${n}.glb`)));
          const hero = (HERO_PIECES as readonly string[]).includes(name);
          const lod = new THREE.LOD();
          const forced = LOD_MODE === '1' ? 1 : LOD_MODE === '2' ? 2 : 0;
          if (!forced) lod.addLevel(high, 0);
          levels.forEach((r, n) => {
            if (r.status !== 'fulfilled' || (forced && forced !== n + 1)) return;
            let m: THREE.Material = material;
            if (hero) {
              const original = (high.getObjectByProperty('isMesh', true) as THREE.Mesh).material as THREE.MeshStandardMaterial;
              const vm = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: original.roughness, metalness: 0, color: original.color });
              if (name === 'hero_tower') addStoneDetail(vm, detail);
              m = vm;
            }
            dress(r.value.scene, m);
            lod.addLevel(r.value.scene, forced ? 0 : LOD_AT[n]);
          });
          if (lod.levels.length === 0) return;
          const wrapper = new THREE.Group();
          wrapper.add(lod);
          wrapper.userData.isWrapper = true;
          pieces.set(name, wrapper);
        }),
      );
      for (const [name, footing] of Object.entries(footings)) {
        const piece = pieces.get(name as KitPiece)!;
        const wrapper = piece.userData.isWrapper ? piece : new THREE.Group().add(piece);
        wrapper.userData.isWrapper = true;
        wrapper.add(footing!);
        pieces.set(name as KitPiece, wrapper as THREE.Group);
      }
      return { make: (piece: KitPiece) => pieces.get(piece)!.clone(true) as THREE.Group, has: (piece: KitPiece) => pieces.has(piece) };
    } catch (e) {
      console.warn('Board kit unavailable, using the procedural board', e);
      return null;
    }
  })());
}
