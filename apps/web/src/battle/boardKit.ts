// Loads the Blender-made board kit (hex tiles, towers, walls, props) from public/board/*.glb.
// Each piece has baked vertex colours, so one shared Lambert material draws them all.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

export const KIT_PIECES = [
  'tile_plain_1', 'tile_plain_2', 'tile_cracked_3', 'tile_slab_4', 'tile_moss_5', 'tile_rough_6', 'tile_rubble_7', 'tile_plate_8', 'tile_scorched_9',
  'tower_spire', 'tower_chimney', 'tower_ruined', 'wall_arched', 'wall_long', 'wall_low', 'crate', 'rubble_pile',
] as const;
export type KitPiece = (typeof KIT_PIECES)[number];

export interface Kit {
  /** A fresh instance of the piece; geometry and material are shared, so instances are cheap. */
  make: (piece: KitPiece) => THREE.Group;
}

let loading: Promise<Kit | null> | null = null;

export function loadBoardKit(): Promise<Kit | null> {
  return (loading ??= (async () => {
    try {
      const loader = new GLTFLoader();
      const material = new THREE.MeshLambertMaterial({ vertexColors: true });
      const base = `${import.meta.env.BASE_URL}board/`;
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
      return { make: (piece: KitPiece) => pieces.get(piece)!.clone(true) as THREE.Group };
    } catch (e) {
      console.warn('Board kit unavailable, using the procedural board', e);
      return null;
    }
  })());
}
