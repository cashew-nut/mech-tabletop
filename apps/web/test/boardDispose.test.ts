import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import { disposeAll, disposeTree, gpuResources } from '../src/battle/boardDispose';
import { crate, disposeBoardArt } from '../src/battle/boardArt';

/** Count how many times three.js announces each object's disposal; the renderer frees GPU memory in response to this event. */
function watch(...objects: Array<THREE.EventDispatcher<{ dispose: object }>>) {
  const counts = new Map<object, number>();
  for (const o of objects) {
    counts.set(o, 0);
    o.addEventListener('dispose', () => counts.set(o, counts.get(o)! + 1));
  }
  return counts;
}

describe('freeing the 3D board', () => {
  it('disposes every geometry, material and texture under a root, once each', () => {
    const shared = new THREE.BoxGeometry();
    const map = new THREE.Texture();
    const normalMap = new THREE.Texture();
    const lit = new THREE.MeshStandardMaterial({ map, normalMap });
    const flat = new THREE.MeshBasicMaterial();
    const own = new THREE.SphereGeometry();
    const root = new THREE.Group();
    const nested = new THREE.Group();
    root.add(new THREE.Mesh(shared, lit), nested);
    nested.add(new THREE.Mesh(shared, lit)); // the same geometry and material again
    nested.add(new THREE.Mesh(own, [flat, lit])); // a multi-material mesh
    const counts = watch(shared, map, normalMap, lit, flat, own);

    disposeTree(root);

    for (const n of counts.values()) expect(n).toBe(1);
    expect(root.children).toHaveLength(2); // freed, not detached: the objects remain usable
  });

  it('ignores objects with nothing to free', () => {
    const root = new THREE.Group().add(new THREE.Object3D(), new THREE.DirectionalLight());
    expect(gpuResources(root).size).toBe(0);
    expect(() => disposeTree(root)).not.toThrow();
  });

  it('disposes a list of resources once each', () => {
    const t = new THREE.Texture();
    const counts = watch(t);
    disposeAll([t, t]);
    expect(counts.get(t)).toBe(1);
  });

  it('frees the props kept at module level, which no scene owns', () => {
    const parent = new THREE.Group();
    crate(parent, [0, 0, 0]);
    const meshes: THREE.Mesh[] = [];
    parent.traverse((o) => (o as THREE.Mesh).isMesh && meshes.push(o as THREE.Mesh));
    expect(meshes.length).toBeGreaterThan(0);
    const counts = watch(meshes[0].geometry, meshes[0].material as THREE.Material);

    disposeBoardArt();

    for (const n of counts.values()) expect(n).toBe(1);
    // They are still cached, so a later board reuses them (three.js uploads them again).
    const again = new THREE.Group();
    crate(again, [0, 0, 0]);
    expect((again.children[0].children[0] as THREE.Mesh).geometry).toBe(meshes[0].geometry);
  });
});
