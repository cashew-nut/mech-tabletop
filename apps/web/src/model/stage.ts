// The lit stage the walker stands on, shared by the builder's 3D view and the
// preview renderer. Each faction gets its own world behind the plinth, after
// the environment moods on the concept boards:
//   covenant  - cathedral cities and fortresses under a broken storm sky
//   foundries - forge wastelands, smokestacks and slag fires under a burning dusk
//   reliquary - ancient ruins and the veil, pale moonlit mist
// A procedural HDR sky draws the background and also lights the metal through
// an environment map. Height fog pools low so distant towers fade at the base,
// and the frame goes through bloom (so glow and fire bleed light) and filmic
// tone mapping. Everything is generated: no textures or models are downloaded.
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export type Backdrop = 'covenant' | 'foundries' | 'reliquary';
export const BACKDROPS: Backdrop[] = ['covenant', 'foundries', 'reliquary'];

export interface Stage {
  scene: THREE.Scene;
  /** Move the shadow camera to fit a newly added model. */
  fit: (model: THREE.Object3D) => void;
  /** Swap the world behind the plinth, with its sky, fog and light. */
  setBackdrop: (backdrop: Backdrop) => void;
  /** Resize the post-processing buffers along with the canvas. */
  setSize: (w: number, h: number) => void;
  /** Draw a frame through bloom and tone mapping. Use this instead of renderer.render. */
  render: (camera: THREE.Camera) => void;
  dispose: () => void;
}

interface Mood {
  exposure: number;
  sky: { zenith: string; horizon: string; ground: string; cloudDark: string; cloudLight: string; cover: number; scale: number; glow: string; glowHeight: number };
  /** Sun (or moon) azimuth and elevation in degrees; azimuth 0 looks down -z. */
  sun: { azimuth: number; elevation: number; colour: string; strength: number; size: number };
  fog: { colour: string; density: number; falloff: number };
  ground: string;
  /** The walker's lights: a soft key from the front, a hard rim from the sun, a coloured fill low down. */
  key: { colour: string; intensity: number };
  rim: { intensity: number };
  fill: { colour: string; intensity: number };
  hemi: { sky: string; ground: string; intensity: number };
  envIntensity: number;
  bloom: { strength: number; radius: number; threshold: number };
}

// Azimuths are in degrees around the stage, measured from straight behind the
// walker as the default cameras see it (they sit at +x +z looking back to the
// origin), so 0 puts the hero skyline and the sun behind the walker.
/** The compass bearing (0 = -z) that lies behind the walker in the default views. */
const HERO = -38;
/** Spreads the skylines out so they sit low on the horizon behind the walker. */
const FAR = 1.8;

const MOODS: Record<Backdrop, Mood> = {
  covenant: {
    exposure: 1.0,
    sky: { zenith: '#101318', horizon: '#4a4a4c', ground: '#17161a', cloudDark: '#16181d', cloudLight: '#7a746c', cover: 0.44, scale: 2.2, glow: '#c88a4a', glowHeight: 14 },
    sun: { azimuth: 16, elevation: 11, colour: '#ffd9a0', strength: 9, size: 0.026 },
    fog: { colour: '#3c3d40', density: 0.0012, falloff: 0.011 },
    ground: '#151413',
    key: { colour: '#f1e6d2', intensity: 2.9 },
    rim: { intensity: 4.2 },
    fill: { colour: '#ff8a3a', intensity: 600 },
    hemi: { sky: '#a8b0bc', ground: '#221a14', intensity: 0.7 },
    envIntensity: 1.25,
    bloom: { strength: 0.45, radius: 0.5, threshold: 0.95 },
  },
  foundries: {
    exposure: 1.05,
    sky: { zenith: '#0e0a0a', horizon: '#7a3018', ground: '#120c0a', cloudDark: '#1a1210', cloudLight: '#7a3a22', cover: 0.4, scale: 2.6, glow: '#ff5a1a', glowHeight: 9 },
    sun: { azimuth: 22, elevation: 5, colour: '#ff9450', strength: 7, size: 0.05 },
    fog: { colour: '#3a1d14', density: 0.0013, falloff: 0.011 },
    ground: '#140e0c',
    key: { colour: '#f4d8bc', intensity: 2.5 },
    rim: { intensity: 3.6 },
    fill: { colour: '#ff6a20', intensity: 1400 },
    hemi: { sky: '#b08070', ground: '#2a1208', intensity: 0.65 },
    envIntensity: 1.15,
    bloom: { strength: 0.75, radius: 0.55, threshold: 0.85 },
  },
  reliquary: {
    exposure: 1.1,
    sky: { zenith: '#0f1317', horizon: '#5e676c', ground: '#16191b', cloudDark: '#262c31', cloudLight: '#9aa4a8', cover: 0.55, scale: 1.8, glow: '#6fb8b0', glowHeight: 18 },
    sun: { azimuth: -16, elevation: 22, colour: '#dfeef2', strength: 7, size: 0.022 },
    fog: { colour: '#535c61', density: 0.0016, falloff: 0.01 },
    ground: '#181a1a',
    key: { colour: '#e4ecf0', intensity: 2.6 },
    rim: { intensity: 3.8 },
    fill: { colour: '#4fd0c0', intensity: 500 },
    hemi: { sky: '#b8c8d0', ground: '#1c1e20', intensity: 0.75 },
    envIntensity: 1.25,
    bloom: { strength: 0.6, radius: 0.6, threshold: 0.88 },
  },
};

// ---------------------------------------------------------------------------
// Height fog. three.js fog only knows distance, so the fog shader chunks are
// replaced: THREE.Fog's near/far uniforms carry density and falloff, and the
// fog thins exponentially with height above the ground (y = 0). Nothing else
// in the app uses THREE.Fog, and FogExp2 keeps its normal behaviour.

class HeightFog extends THREE.Fog {
  constructor(colour: THREE.ColorRepresentation, density: number, falloff: number) {
    super(colour, density, falloff);
  }
  set(colour: string, density: number, falloff: number) {
    this.color.set(colour);
    this.near = density;
    this.far = falloff;
  }
}

let fogPatched = false;
function patchFogChunks() {
  if (fogPatched) return;
  fogPatched = true;
  THREE.ShaderChunk.fog_pars_vertex = /* glsl */ `
#ifdef USE_FOG
  varying float vFogDepth;
  varying vec3 vFogWorldPosition;
#endif`;
  // The view matrix is rigid, so its inverse is a transpose and a shift.
  THREE.ShaderChunk.fog_vertex = /* glsl */ `
#ifdef USE_FOG
  vFogDepth = - mvPosition.z;
  vFogWorldPosition = transpose( mat3( viewMatrix ) ) * ( mvPosition.xyz - viewMatrix[ 3 ].xyz );
#endif`;
  THREE.ShaderChunk.fog_pars_fragment = /* glsl */ `
#ifdef USE_FOG
  uniform vec3 fogColor;
  varying float vFogDepth;
  varying vec3 vFogWorldPosition;
  #ifdef FOG_EXP2
    uniform float fogDensity;
  #else
    uniform float fogNear;
    uniform float fogFar;
  #endif
#endif`;
  // Density a * exp(-b * y) integrated along the eye ray (after Inigo Quilez).
  THREE.ShaderChunk.fog_fragment = /* glsl */ `
#ifdef USE_FOG
  #ifdef FOG_EXP2
    float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
  #else
    vec3 fogRay = vFogWorldPosition - cameraPosition;
    float fogDist = length( fogRay );
    float fogK = fogFar * fogRay.y;
    float fogSpan = abs( fogK ) > 1e-4 ? ( 1.0 - exp( - fogK ) ) / fogK : 1.0;
    float fogAmount = fogNear * exp( - fogFar * max( cameraPosition.y, 0.0 ) ) * fogDist * fogSpan;
    float fogFactor = 1.0 - exp( - fogAmount );
  #endif
  gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`;
}

// ---------------------------------------------------------------------------
// The sky: a dome drawn at the far plane in HDR, so the sun disc is bright
// enough to bloom. The same dome is captured into the environment map.

const skyVertex = /* glsl */ `
varying vec3 vDir;
void main() {
  vDir = position;
  vec4 p = projectionMatrix * vec4( mat3( viewMatrix ) * position, 1.0 );
  gl_Position = p.xyww;
}`;

const skyFragment = /* glsl */ `
uniform vec3 uZenith, uHorizon, uGround, uCloudDark, uCloudLight, uGlow, uFog, uSunDir, uSunColour;
uniform float uCover, uScale, uGlowHeight, uSunSize;
varying vec3 vDir;

float hash( vec2 p ) { return fract( sin( dot( p, vec2( 127.1, 311.7 ) ) ) * 43758.5453 ); }
float noise( vec2 p ) {
  vec2 i = floor( p ), f = fract( p );
  vec2 u = f * f * ( 3.0 - 2.0 * f );
  return mix( mix( hash( i ), hash( i + vec2( 1, 0 ) ), u.x ), mix( hash( i + vec2( 0, 1 ) ), hash( i + vec2( 1, 1 ) ), u.x ), u.y );
}
float fbm( vec2 p ) {
  float v = 0.0, a = 0.5;
  for ( int i = 0; i < 5; i++ ) { v += a * noise( p ); p = p * 2.03 + 17.1; a *= 0.5; }
  return v;
}

void main() {
  vec3 d = normalize( vDir );
  float h = d.y;
  float sunAmt = max( dot( d, uSunDir ), 0.0 );
  vec3 col = h > 0.0 ? mix( uHorizon, uZenith, pow( h, 0.55 ) ) : mix( uHorizon, uGround, clamp( -h * 8.0, 0.0, 1.0 ) );
  col += uGlow * exp( -abs( h ) * uGlowHeight ) * ( 0.35 + 0.65 * sunAmt );
  col += uSunColour * 0.012 * pow( sunAmt, 10.0 );

  // Cloud deck: fbm on a plane overhead, lit on the side facing the sun.
  float cover = 0.0;
  if ( h > 0.0 ) {
    vec2 p = d.xz / ( h + 0.08 ) * uScale;
    float n = fbm( p );
    float n2 = fbm( p * 2.7 + 5.0 );
    cover = smoothstep( uCover - 0.18, uCover + 0.22, n * 0.75 + n2 * 0.25 ) * smoothstep( 0.0, 0.18, h );
    float lit = clamp( 0.1 + 0.9 * pow( sunAmt, 5.0 ) - ( n - uCover ) * 1.6, 0.0, 1.0 );
    vec3 cloud = mix( uCloudDark, uCloudLight, lit );
    // Silver edges where thin cloud crosses the sun.
    cloud += uSunColour * 0.08 * pow( sunAmt, 12.0 ) * ( 1.0 - cover );
    col = mix( col, cloud, cover * 0.92 );
  }

  float disc = smoothstep( cos( uSunSize ), cos( uSunSize * 0.7 ), dot( d, uSunDir ) );
  col += uSunColour * ( disc * ( 1.0 - cover * 0.8 ) + 0.06 * pow( sunAmt, 90.0 ) );

  // Melt into the fog at the horizon so the ground edge disappears.
  col = mix( col, uFog, exp( -max( h + 0.02, 0.0 ) * 22.0 ) );
  gl_FragColor = vec4( col, 1.0 );
}`;

function sunDirection(m: Mood) {
  const az = THREE.MathUtils.degToRad(HERO + m.sun.azimuth);
  const el = THREE.MathUtils.degToRad(m.sun.elevation);
  return new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el));
}

function createSky() {
  const lin = (c: string) => new THREE.Color(c);
  const material = new THREE.ShaderMaterial({
    name: 'stage_sky',
    vertexShader: skyVertex,
    fragmentShader: skyFragment,
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      uZenith: { value: lin('#000') },
      uHorizon: { value: lin('#000') },
      uGround: { value: lin('#000') },
      uCloudDark: { value: lin('#000') },
      uCloudLight: { value: lin('#000') },
      uGlow: { value: lin('#000') },
      uFog: { value: lin('#000') },
      uSunDir: { value: new THREE.Vector3(0, 1, 0) },
      uSunColour: { value: lin('#000') },
      uCover: { value: 0.5 },
      uScale: { value: 2 },
      uGlowHeight: { value: 10 },
      uSunSize: { value: 0.03 },
    },
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 24), material);
  mesh.name = 'stage_sky';
  mesh.frustumCulled = false;
  mesh.renderOrder = -1000;
  const apply = (m: Mood) => {
    const u = material.uniforms;
    u.uZenith.value.set(m.sky.zenith);
    u.uHorizon.value.set(m.sky.horizon);
    u.uGround.value.set(m.sky.ground);
    u.uCloudDark.value.set(m.sky.cloudDark);
    u.uCloudLight.value.set(m.sky.cloudLight);
    u.uGlow.value.set(m.sky.glow).multiplyScalar(0.35);
    u.uFog.value.set(m.fog.colour);
    u.uSunDir.value.copy(sunDirection(m));
    u.uSunColour.value.set(m.sun.colour).multiplyScalar(m.sun.strength);
    u.uCover.value = m.sky.cover;
    u.uScale.value = m.sky.scale;
    u.uGlowHeight.value = m.sky.glowHeight;
    u.uSunSize.value = m.sun.size;
  };
  return { mesh, apply };
}

// ---------------------------------------------------------------------------
// The plinth floor: the faint hex grid of the game table, fading into the ground.

/** White in the middle fading to clear at the rim, so the floor melts into the ground. */
function fadeTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grad.addColorStop(0, '#fff');
  grad.addColorStop(0.35, '#fff');
  grad.addColorStop(1, '#000');
  g.fillStyle = grad;
  g.fillRect(0, 0, 256, 256);
  return new THREE.CanvasTexture(c);
}

function floorTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(256, 256, 0, 256, 256, 256);
  grad.addColorStop(0, '#34302b');
  grad.addColorStop(1, '#23201d');
  g.fillStyle = grad;
  g.fillRect(0, 0, 512, 512);
  g.strokeStyle = 'rgba(210, 170, 100, 0.05)';
  g.lineWidth = 1.5;
  const r = 26;
  for (let row = -1; row < 14; row++) {
    for (let col = -1; col < 12; col++) {
      const x = col * r * 1.5;
      const y = row * r * Math.sqrt(3) + (col % 2 ? (r * Math.sqrt(3)) / 2 : 0);
      g.beginPath();
      for (let i = 0; i <= 6; i++) {
        const a = (Math.PI / 3) * i;
        g.lineTo(x + r * Math.cos(a), y + r * Math.sin(a));
      }
      g.stroke();
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// ---------------------------------------------------------------------------
// Backdrops: low-poly silhouettes merged into a few meshes (stone, smoke and
// glow) so a whole skyline costs a handful of draw calls. The ground and
// skyline are Lambert: cheaper, and without the grazing sheen that made the
// ground read as pale sand when looking toward the sun.

type Rand = () => number;
function seeded(seed: number): Rand {
  let s = seed;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

class Parts {
  stone: THREE.BufferGeometry[] = [];
  glow: THREE.BufferGeometry[] = [];
  smoke: THREE.BufferGeometry[] = [];
  add(list: 'stone' | 'glow' | 'smoke', g: THREE.BufferGeometry, x: number, y: number, z: number, ry = 0, rx = 0, rz = 0) {
    g.rotateX(rx).rotateZ(rz).rotateY(ry).translate(x, y, z);
    // Merging needs one attribute layout, so drop UVs.
    g.deleteAttribute('uv');
    this[list].push(g.index ? g.toNonIndexed() : g);
  }
}

/** A point on the ring around the stage, at an azimuth (see MOODS) and a distance from the centre. */
function ring(az: number, dist: number): [number, number] {
  const a = THREE.MathUtils.degToRad(HERO + az);
  const d = dist * FAR;
  return [Math.sin(a) * d, -Math.cos(a) * d];
}

/** The y rotation that turns a wall at this azimuth to face the stage. */
const facing = (az: number) => THREE.MathUtils.degToRad(-(HERO + az));

/** A tapering spire on a square tower, the basic Covenant silhouette. */
function spireTower(p: Parts, x: number, z: number, w: number, h: number, spire: number, r: Rand, windows: boolean) {
  p.add('stone', new THREE.BoxGeometry(w, h, w), x, h / 2, z, r() * Math.PI);
  p.add('stone', new THREE.ConeGeometry(w * 0.72, spire, 4), x, h + spire / 2, z, Math.PI / 4);
  // Pinnacles on the corners.
  for (let i = 0; i < 4; i++) {
    const a = (Math.PI / 2) * i + Math.PI / 4;
    const ph = spire * (0.25 + r() * 0.15);
    p.add('stone', new THREE.ConeGeometry(w * 0.12, ph, 4), x + Math.cos(a) * w * 0.55, h + ph / 2, z + Math.sin(a) * w * 0.55);
  }
  if (windows) {
    for (let i = 0; i < 3; i++) {
      if (r() < 0.45) continue;
      const wy = h * (0.3 + r() * 0.6);
      const a = r() * Math.PI * 2;
      p.add('glow', new THREE.BoxGeometry(w * 0.16, w * 0.32, w * 0.16), x + Math.cos(a) * w * 0.48, wy, z + Math.sin(a) * w * 0.48);
    }
  }
}

function covenant(p: Parts) {
  const r = seeded(7);
  // The hero cathedral behind the walker: nave, transept, a great spire and two west towers.
  const [cx, cz] = ring(-16, 520);
  const face = Math.atan2(cx, cz);
  p.add('stone', new THREE.BoxGeometry(70, 70, 170), cx, 35, cz, face);
  p.add('stone', new THREE.CylinderGeometry(0, 50, 40, 4, 1, false, Math.PI / 4), cx, 90, cz, face, 0, 0);
  p.add('stone', new THREE.BoxGeometry(160, 60, 50), cx, 30, cz, face);
  spireTower(p, cx, cz, 36, 120, 190, r, true);
  for (const side of [-1, 1]) {
    const ox = Math.cos(face) * 42 * side + Math.sin(face) * 80;
    const oz = -Math.sin(face) * 42 * side + Math.cos(face) * 80;
    spireTower(p, cx + ox, cz + oz, 26, 110, 90, r, true);
  }
  // Flying buttresses down each side.
  for (let i = -3; i <= 3; i++) {
    for (const side of [-1, 1]) {
      const ox = Math.cos(face) * 50 * side + Math.sin(face) * i * 22;
      const oz = -Math.sin(face) * 50 * side + Math.cos(face) * i * 22;
      p.add('stone', new THREE.BoxGeometry(5, 60, 5), cx + ox, 30, cz + oz, face, 0, side * 0.3);
      p.add('stone', new THREE.ConeGeometry(3, 18, 4), cx + ox * 1.15, 66, cz + oz * 1.02);
    }
  }
  // An arched bridge running off to one side of the cathedral.
  const bridgeAz = 34;
  for (let i = 0; i < 12; i++) {
    const [bx, bz] = ring(bridgeAz + i * 2.6, 470);
    p.add('stone', new THREE.BoxGeometry(9, 46, 12), bx, 23, bz, facing(bridgeAz + i * 2.6));
    const [tx, tz] = ring(bridgeAz + i * 2.6 + 1.3, 470);
    p.add('stone', new THREE.BoxGeometry(36, 9, 12), tx, 50, tz, facing(bridgeAz + i * 2.6 + 1.3));
    if (r() < 0.5) p.add('glow', new THREE.BoxGeometry(2, 3, 2), tx, 56, tz);
  }
  // The rest of the city around the horizon, thinning away from the hero view.
  for (let i = 0; i < 70; i++) {
    const az = -180 + r() * 360;
    const near = Math.abs(az) < 60 ? 1 : 0.6;
    const [x, z] = ring(az, 420 + r() * 380);
    const h = (25 + r() * 70) * near;
    const w = 14 + r() * 26;
    if (r() < 0.55) spireTower(p, x, z, w, h, h * (0.6 + r()), r, r() < 0.7);
    else {
      p.add('stone', new THREE.BoxGeometry(w * 1.8, h * 0.6, w), x, h * 0.3, z, r() * Math.PI);
      p.add('stone', new THREE.CylinderGeometry(0, w * 1.1, h * 0.35, 4, 1, false, Math.PI / 4), x, h * 0.6 + h * 0.17, z, r() * Math.PI);
      if (r() < 0.6) p.add('glow', new THREE.BoxGeometry(3, 5, 3), x + w * 0.5, h * 0.3, z);
    }
  }
  // A dense crown of spires on the far skyline behind the walker.
  for (let i = 0; i < 36; i++) {
    const [x, z] = ring((r() - 0.5) * 150, 620 + r() * 320);
    const w = 10 + r() * 16;
    const h = 30 + r() * 60;
    spireTower(p, x, z, w, h, h * (0.9 + r() * 1.2), r, r() < 0.5);
  }
  // Fortress walls on a ridge to the far side.
  for (let i = 0; i < 26; i++) {
    const az = -150 + i * 3;
    const [x, z] = ring(az, 640);
    p.add('stone', new THREE.BoxGeometry(62, 28, 10), x, 14, z, facing(az));
    if (i % 4 === 0) {
      p.add('stone', new THREE.CylinderGeometry(9, 10, 50, 8), x, 25, z);
      p.add('stone', new THREE.ConeGeometry(11, 26, 8), x, 63, z);
    }
  }
  return { stone: '#16151a', glow: new THREE.Color(5.5, 3.4, 1.3) };
}

/** A smokestack with a glowing lip and a drifting plume of dark smoke. */
function smokestack(p: Parts, x: number, z: number, h: number, rad: number, r: Rand, drift: THREE.Vector2) {
  p.add('stone', new THREE.CylinderGeometry(rad * 0.75, rad, h, 10), x, h / 2, z);
  for (let b = 0.25; b < 1; b += 0.25) p.add('stone', new THREE.CylinderGeometry(rad * 1.08, rad * 1.08, 2.5, 10), x, h * b, z);
  p.add('glow', new THREE.CylinderGeometry(rad * 0.82, rad * 0.8, 3, 10, 1, true), x, h + 1, z);
  let px = x;
  let pz = z;
  let py = h + rad;
  let s = rad * 1.1;
  for (let i = 0; i < 14; i++) {
    for (let k = 0; k < 2; k++) {
      const puff = new THREE.IcosahedronGeometry(s * (0.6 + r() * 0.5), 1);
      puff.scale(1.3, 0.75, 1);
      p.add('smoke', puff, px + (r() - 0.5) * s, py + (r() - 0.5) * s * 0.5, pz + (r() - 0.5) * s, r() * 3);
    }
    px += drift.x * s * 0.8;
    pz += drift.y * s * 0.8;
    py += s * (0.35 + r() * 0.25);
    s *= 1.14;
  }
}

/** A dockyard gantry crane: two legs, a high beam and a long jib. */
function gantry(p: Parts, x: number, z: number, h: number, ry: number) {
  const c = Math.cos(ry);
  const s = Math.sin(ry);
  for (const side of [-1, 1]) {
    for (let y = 0; y < h; y += 12) p.add('stone', new THREE.BoxGeometry(2, 14, 2), x + c * 14 * side, y + 7, z - s * 14 * side, ry, 0, 0.5 * side);
    p.add('stone', new THREE.BoxGeometry(3, h, 3), x + c * 14 * side, h / 2, z - s * 14 * side, ry);
  }
  p.add('stone', new THREE.BoxGeometry(40, 5, 6), x, h, z, ry);
  p.add('stone', new THREE.BoxGeometry(4, 4, 110), x + s * 45, h + 4, z + c * 45, ry);
  p.add('stone', new THREE.BoxGeometry(1, 40, 1), x + s * 90, h - 18, z + c * 90, ry);
}

function foundries(p: Parts) {
  const r = seeded(31);
  const drift = new THREE.Vector2(0.45, 0.25);
  // The forge city behind the walker: stacks, sawtooth sheds and blast furnaces.
  for (let i = 0; i < 16; i++) {
    const [x, z] = ring((r() - 0.5) * 110, 420 + r() * 300);
    smokestack(p, x, z, 90 + r() * 140, 5 + r() * 5, r, drift);
  }
  for (let i = 0; i < 40; i++) {
    const az = -180 + r() * 360;
    const [x, z] = ring(az, 360 + r() * 420);
    const w = 30 + r() * 60;
    const h = 18 + r() * 40;
    const ry = r() * Math.PI;
    p.add('stone', new THREE.BoxGeometry(w, h, w * 0.6), x, h / 2, z, ry);
    // Sawtooth roof.
    for (let t = 0; t < 3; t++) {
      const off = (t - 1) * w * 0.3;
      const roof = new THREE.CylinderGeometry(0, w * 0.2, w * 0.3, 3, 1);
      p.add('stone', roof, x + Math.cos(ry) * off, h + w * 0.1, z - Math.sin(ry) * off, ry, 0, Math.PI / 2);
    }
    if (r() < 0.5) p.add('glow', new THREE.BoxGeometry(w * 0.3, h * 0.25, 1), x, h * 0.3, z, ry);
  }
  // Blast furnaces: fat cones with a molten mouth.
  for (let i = 0; i < 6; i++) {
    const [x, z] = ring(-40 + i * 16 + r() * 10, 380 + r() * 120);
    const h = 50 + r() * 30;
    p.add('stone', new THREE.CylinderGeometry(10, 22, h, 10), x, h / 2, z);
    p.add('glow', new THREE.CylinderGeometry(9, 9, 4, 10), x, h + 2, z);
    smokestack(p, x + 18, z, h + 40, 4, r, drift);
  }
  gantry(p, ...ring(34, 380), 90, 0.9);
  gantry(p, ...ring(-30, 560), 120, -0.4);
  gantry(p, ...ring(-150, 500), 80, 2.1);
  // Slag fires and burning wrecks across the wasteland.
  for (let i = 0; i < 40; i++) {
    const [x, z] = ring(-180 + r() * 360, 170 + r() * 420);
    const s = 2 + r() * 6;
    p.add('glow', new THREE.IcosahedronGeometry(s, 0), x, s * 0.2, z, r() * 3, r() * 3);
    p.add('stone', new THREE.BoxGeometry(s * 3, s * 1.2, s * 2), x + s, s * 0.5, z, r() * 3, r() * 0.4);
  }
  return { stone: '#120e0d', glow: new THREE.Color(7, 2.2, 0.5) };
}

/** A pointed gothic arch standing alone: two piers and two leaning arcs. */
function archway(p: Parts, x: number, z: number, h: number, w: number, ry: number, broken: boolean) {
  const c = Math.cos(ry);
  const s = Math.sin(ry);
  for (const side of [-1, 1]) {
    if (broken && side === 1) {
      p.add('stone', new THREE.BoxGeometry(6, h * 0.55, 6), x + c * w * side, h * 0.27, z - s * w * side, ry);
      continue;
    }
    p.add('stone', new THREE.BoxGeometry(6, h, 6), x + c * w * side, h / 2, z - s * w * side, ry);
    // Each arc is centred on the opposite pier, so the two meet in a point.
    const arc = new THREE.TorusGeometry(w * 2, 2.6, 4, 12, Math.PI / 3);
    if (side === -1) arc.rotateZ((Math.PI * 2) / 3);
    p.add('stone', arc, x - c * w * side, h, z + s * w * side, ry);
  }
}

function reliquary(p: Parts) {
  const r = seeded(53);
  // The veil: a vast halo gate hanging over the ruins behind the walker.
  const [vx, vz] = ring(4, 680);
  const face = Math.atan2(vx, vz);
  p.add('glow', new THREE.TorusGeometry(95, 2.2, 6, 64), vx, 170, vz, face);
  p.add('glow', new THREE.TorusGeometry(70, 1.2, 6, 64), vx, 170, vz, face);
  for (let i = 0; i < 24; i++) {
    const a = (Math.PI * 2 * i) / 24;
    const len = i % 2 ? 24 : 44;
    const ray = new THREE.BoxGeometry(1.6, len, 1.6);
    ray.translate(0, 95 + len / 2, 0).rotateZ(a);
    p.add('glow', ray, vx, 170, vz, face);
  }
  // Tall broken spires of a drowned city.
  for (let i = 0; i < 34; i++) {
    const az = -180 + r() * 360;
    const [x, z] = ring(az, 380 + r() * 420);
    const h = 60 + r() * 180;
    const w = 7 + r() * 12;
    const lean = (r() - 0.5) * 0.12;
    p.add('stone', new THREE.CylinderGeometry(w * (r() < 0.5 ? 0.15 : 0.55), w, h, 6), x, h / 2, z, r() * 3, lean, lean);
    if (r() < 0.4) p.add('stone', new THREE.ConeGeometry(w * 0.5, h * 0.3, 6), x, h + h * 0.15, z, 0, lean, lean);
    if (r() < 0.25) p.add('glow', new THREE.BoxGeometry(1.6, 1.6, 1.6), x, h * 0.7, z);
  }
  // Standing arches and fallen colonnades closer in.
  for (let i = 0; i < 14; i++) {
    const az = -180 + r() * 360;
    const [x, z] = ring(az, 230 + r() * 260);
    archway(p, x, z, 40 + r() * 50, 12 + r() * 10, facing(az) + (r() - 0.5), r() < 0.4);
  }
  // Grave markers and toppled blocks near the plinth.
  for (let i = 0; i < 46; i++) {
    const [x, z] = ring(-180 + r() * 360, 150 + r() * 200);
    const h = 4 + r() * 14;
    p.add('stone', new THREE.BoxGeometry(3 + r() * 4, h, 2 + r() * 3), x, h / 2 - 1, z, r() * 3, (r() - 0.5) * 0.5, (r() - 0.5) * 0.5);
  }
  // Floating relic shards around the veil.
  for (let i = 0; i < 18; i++) {
    const a = r() * Math.PI * 2;
    const d = 120 + r() * 60;
    p.add('stone', new THREE.OctahedronGeometry(4 + r() * 8, 0), vx + Math.cos(a) * d * Math.cos(face), 170 + Math.sin(a) * d * 0.7, vz - Math.cos(a) * d * Math.sin(face), r() * 3, r() * 3);
  }
  return { stone: '#1c1f21', glow: new THREE.Color(1.2, 5.2, 4.6) };
}

const BUILDERS: Record<Backdrop, (p: Parts) => { stone: string; glow: THREE.Color }> = { covenant, foundries, reliquary };

/** Rolling ground out to the horizon, flat under the plinth. */
function groundGeometry(seed: number) {
  const g = new THREE.PlaneGeometry(4400, 4400, 140, 140);
  g.rotateX(-Math.PI / 2);
  const pos = g.attributes.position;
  const r = seeded(seed);
  const bumps = Array.from({ length: 40 }, () => ({ x: (r() - 0.5) * 3600, z: (r() - 0.5) * 3600, s: 80 + r() * 300, h: (r() - 0.3) * 40 }));
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const flat = THREE.MathUtils.smoothstep(Math.hypot(x, z), 110, 260);
    let y = 0;
    for (const b of bumps) y += b.h * Math.exp(-((x - b.x) ** 2 + (z - b.z) ** 2) / (b.s * b.s));
    pos.setY(i, -0.3 + y * flat);
  }
  g.computeVertexNormals();
  return g;
}

function buildBackdrop(backdrop: Backdrop, mood: Mood) {
  const group = new THREE.Group();
  group.name = `stage_backdrop_${backdrop}`;
  const p = new Parts();
  const look = BUILDERS[backdrop](p);
  const stone = new THREE.Mesh(mergeGeometries(p.stone), new THREE.MeshLambertMaterial({ color: look.stone, flatShading: true }));
  stone.name = 'stage_skyline';
  group.add(stone);
  if (p.smoke.length) {
    const smoke = new THREE.Mesh(mergeGeometries(p.smoke), new THREE.MeshLambertMaterial({ color: '#1c1614' }));
    smoke.name = 'stage_smoke';
    group.add(smoke);
  }
  if (p.glow.length) {
    const glow = new THREE.Mesh(mergeGeometries(p.glow), new THREE.MeshBasicMaterial({ color: look.glow }));
    glow.name = 'stage_lights';
    group.add(glow);
  }
  const r = seeded(99);
  const rubble: THREE.BufferGeometry[] = [];
  for (let i = 0; i < 90; i++) {
    const a = r() * Math.PI * 2;
    const d = 120 + r() * 260;
    const sz = 1.5 + r() * 6;
    const g = new THREE.DodecahedronGeometry(sz, 0);
    g.scale(1 + r(), 0.5 + r() * 0.5, 1 + r());
    g.rotateY(r() * 3).translate(Math.cos(a) * d, sz * 0.15, Math.sin(a) * d);
    g.deleteAttribute('uv');
    rubble.push(g.toNonIndexed());
  }
  const rocks = new THREE.Mesh(mergeGeometries(rubble), new THREE.MeshLambertMaterial({ color: mood.ground, flatShading: true }));
  rocks.receiveShadow = true;
  rocks.name = 'stage_rubble';
  group.add(rocks);
  const ground = new THREE.Mesh(groundGeometry(BACKDROPS.indexOf(backdrop) + 3), new THREE.MeshLambertMaterial({ color: mood.ground }));
  ground.receiveShadow = true;
  ground.name = 'stage_ground';
  group.add(ground);
  return group;
}

// ---------------------------------------------------------------------------

export function setupRenderer(renderer: THREE.WebGLRenderer) {
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
}

export function createStage(renderer: THREE.WebGLRenderer, initial: Backdrop = 'covenant'): Stage {
  patchFogChunks();
  setupRenderer(renderer);
  const scene = new THREE.Scene();
  const fog = new HeightFog('#000', 0, 0);
  scene.fog = fog;
  const sky = createSky();
  scene.add(sky.mesh);

  const hemi = new THREE.HemisphereLight('#fff', '#000', 1);
  const key = new THREE.DirectionalLight('#fff', 1);
  key.position.set(60, 110, 70);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.02;
  key.shadow.radius = 4;
  const rim = new THREE.DirectionalLight('#fff', 1);
  const fill = new THREE.PointLight('#fff', 1, 0, 2);
  fill.position.set(-40, 12, 50);
  scene.add(hemi, key, key.target, rim, fill);

  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(130, 64),
    new THREE.MeshLambertMaterial({ map: floorTexture(), alphaMap: fadeTexture(), transparent: true, depthWrite: false }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = 0.05;
  floor.receiveShadow = true;
  floor.renderOrder = 1;
  floor.name = 'stage_floor';
  scene.add(floor);

  const size = renderer.getSize(new THREE.Vector2());
  const target = new THREE.WebGLRenderTarget(size.x * renderer.getPixelRatio(), size.y * renderer.getPixelRatio(), { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, target);
  const renderPass = new RenderPass(scene, new THREE.PerspectiveCamera());
  const bloom = new UnrealBloomPass(new THREE.Vector2(size.x, size.y), 0.6, 0.5, 0.9);
  composer.addPass(renderPass);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  const pmrem = new THREE.PMREMGenerator(renderer);
  let env: THREE.WebGLRenderTarget | null = null;
  let backdrop: THREE.Group | null = null;

  const setBackdrop = (b: Backdrop) => {
    const m = MOODS[b];
    renderer.toneMappingExposure = m.exposure;
    fog.set(m.fog.colour, m.fog.density, m.fog.falloff);
    sky.apply(m);

    // Capture the sky alone into the environment map, so metal reflects the storm.
    // The sun is dimmed for the capture: at full strength every gold edge blows out.
    // Two soft boxes, overhead and to the camera side, give the gold the studio
    // highlights the dark sky alone would not. Only the walker and plinth use
    // the environment map; the world is Lambert.
    const skyOnly = new THREE.Scene();
    skyOnly.add(sky.mesh.clone());
    const box = new THREE.MeshBasicMaterial({ color: new THREE.Color(m.key.colour).multiplyScalar(1.6), side: THREE.DoubleSide });
    const top = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), box);
    top.position.set(0, 3, 0);
    top.scale.set(3, 3, 1);
    top.rotation.x = Math.PI / 2;
    const side = new THREE.Mesh(top.geometry, box);
    side.position.copy(key.position).normalize().multiplyScalar(3);
    side.scale.set(2.4, 1.2, 1);
    side.lookAt(0, 0, 0);
    skyOnly.add(top, side);
    const sun = sky.mesh.material.uniforms.uSunColour.value;
    sun.multiplyScalar(0.3);
    env?.dispose();
    env = pmrem.fromScene(skyOnly, 0.02, 1, 1000);
    sun.multiplyScalar(1 / 0.3);
    top.geometry.dispose();
    box.dispose();
    scene.environment = env.texture;
    scene.environmentIntensity = m.envIntensity;

    hemi.color.set(m.hemi.sky);
    hemi.groundColor.set(m.hemi.ground);
    hemi.intensity = m.hemi.intensity;
    key.color.set(m.key.colour);
    key.intensity = m.key.intensity;
    rim.color.set(m.sun.colour);
    rim.intensity = m.rim.intensity;
    rim.position.copy(sunDirection(m)).multiplyScalar(150);
    fill.color.set(m.fill.colour);
    fill.intensity = m.fill.intensity;
    bloom.strength = m.bloom.strength;
    bloom.radius = m.bloom.radius;
    bloom.threshold = m.bloom.threshold;

    if (backdrop) {
      scene.remove(backdrop);
      backdrop.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (!mesh.isMesh) return;
        mesh.geometry.dispose();
        (mesh.material as THREE.Material).dispose();
      });
    }
    backdrop = buildBackdrop(b, m);
    scene.add(backdrop);
  };
  setBackdrop(initial);

  const fit = (model: THREE.Object3D) => {
    model.traverse((o) => {
      if ((o as THREE.Mesh).isMesh) o.castShadow = o.receiveShadow = true;
    });
    const box = new THREE.Box3().setFromObject(model);
    const r = Math.max(30, box.getSize(new THREE.Vector3()).length() * 0.7);
    const cam = key.shadow.camera;
    cam.left = cam.bottom = -r;
    cam.right = cam.top = r;
    cam.near = 1;
    cam.far = 400;
    cam.updateProjectionMatrix();
  };

  const setSize = (w: number, h: number) => {
    composer.setPixelRatio(renderer.getPixelRatio());
    composer.setSize(w, h);
  };

  const render = (camera: THREE.Camera) => {
    renderPass.camera = camera;
    composer.render();
  };

  const dispose = () => {
    composer.dispose();
    target.dispose();
    env?.dispose();
    pmrem.dispose();
    // Only the stage's own meshes: the walker belongs to the caller.
    for (const owned of [sky.mesh, floor, backdrop]) {
      owned?.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (!mesh.isMesh) return;
        mesh.geometry.dispose();
        (mesh.material as THREE.Material).dispose();
      });
    }
  };

  return { scene, fit, setBackdrop, setSize, render, dispose };
}
