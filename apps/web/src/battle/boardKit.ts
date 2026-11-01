// Loads the Blender-made board kit (hex tiles, towers, walls, props) from public/board/*.glb.
// Each piece has baked vertex colours, so one shared Lambert material draws them all.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

export const KIT_PIECES = [
  'tile_plain_1', 'tile_plain_2', 'tile_cracked_3', 'tile_slab_4', 'tile_moss_5', 'tile_rough_6', 'tile_rubble_7', 'tile_plate_8', 'tile_scorched_9',
  'tower_spire', 'tower_chimney', 'tower_ruined', 'wall_arched', 'wall_long', 'wall_low', 'crate', 'rubble_pile',
] as const;
/** Meshy-made hero scenery (textured, with its own material). Optional: the procedural pieces stand in when a file is missing. */
export const HERO_PIECES = ['hero_tower', 'hero_chimney', 'hero_wall'] as const;
export type KitPiece = (typeof KIT_PIECES)[number] | (typeof HERO_PIECES)[number];

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
      loaded.forEach((gltf, i) => {
        gltf.scene.traverse((o) => {
          const mesh = o as THREE.Mesh;
          if (mesh.isMesh) {
            mesh.material = material;
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
      return { make: (piece: KitPiece) => pieces.get(piece)!.clone(true) as THREE.Group, has: (piece: KitPiece) => pieces.has(piece) };
    } catch (e) {
      console.warn('Board kit unavailable, using the procedural board', e);
      return null;
    }
  })());
}
