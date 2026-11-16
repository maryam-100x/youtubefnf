// kit3d · the core every 3D piece stands on (standard/3D.md). One stage, one way to load, one camera, one light, one finish.
//
//   Stage3D   a <ThreeCanvas> the size of the video (2560 x 1440 at --scale 1.333: R3F's dpr follows the render's deviceScaleFactor),
//             transparent unless `bg` is given (it sits over kit3's Stage: the shot's own footage defocused is the ground), a camera set
//             from `cam` on every frame (a pure function of the frame: render tabs share no state), the environment light (`env`), the
//             finish (`post`), and in the gate's probe (REMOTION_GATE=1) only an empty box marked data-kit3d (no WebGL in the probe).
//   useAsset  every file the scene needs, loaded BEFORE the canvas mounts, under a delayRender handle (kit3's useMeasured): the canvas
//             never draws a frame with a texture still on its way (a texture that arrives after the canvas has drawn stays black)
//   env       the reflections: studio panels (rectangles of light, the shaped light of a product shot), an HDRI, the shot's own picture
//             (so a glossy object reflects the colours of the scene it stands in), baked once per canvas into a PMREM map;
//             `rotation` turns it (a light sweeping across a glossy face is the environment turning, no re-bake)
//   post      the finish, three.js's own passes (no extra package): MSAA x4 on a half-float target (or SSAA), bloom only above
//             `threshold` (nothing glows but real highlights), the tone map (Khronos PBR Neutral by default: the logo's and the
//             cover's own colours stay true under white light), a vignette and a grain seeded by the frame (deterministic)
//   cam       {pos, target, fov, up?}: the pieces compute it from the frame; `project(cam, p)` puts an HTML label on a 3D point
//             with the same math (text stays HTML, the look's display family: kit3's type)
//
// Rules the core keeps for every piece (sources in standard/3D.md §3):
//   - nothing animates by itself: no useFrame for motion, no clock, no Math.random; every pose is f(frame) (remotion.dev/docs/three)
//   - the composer is rendered from R3F's frame callback at priority 1 (R3F then skips its own render): it runs on every advance()
//   - one canvas per shot, mounted with its shot (each canvas is a WebGL context; Chrome keeps ~16 a page)
import React, {useEffect, useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useFrame, useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {EffectComposer} from 'three/examples/jsm/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/examples/jsm/postprocessing/RenderPass.js';
import {SSAARenderPass} from 'three/examples/jsm/postprocessing/SSAARenderPass.js';
import {UnrealBloomPass} from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/examples/jsm/postprocessing/OutputPass.js';
import {ShaderPass} from 'three/examples/jsm/postprocessing/ShaderPass.js';
import {RGBELoader} from 'three/examples/jsm/loaders/RGBELoader.js';
import {TTFLoader} from 'three/examples/jsm/loaders/TTFLoader.js';
import {Font} from 'three/examples/jsm/loaders/FontLoader.js';
import {useMeasured, url} from '../kit3/measure';
import {gateLog, gateOn} from '../gate';

export type V3 = [number, number, number];
export type Cam = {pos: V3; target: V3; fov: number; up?: V3; near?: number; far?: number};

// ============================================================================================================================ timing
export const clampX = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const CURVE = {
  move: Easing.bezier(0.2, 0, 0, 1),      // the house EASE.move: one camera move that lands
  enter: Easing.bezier(0.05, 0.7, 0.1, 1),
  drift: Easing.bezier(0.33, 0, 0.2, 1),
};
// 0..1 over [at, at + d] on a curve
export const prog = (t: number, at: number, d: number, curve = CURVE.move) => interpolate(t, [at, at + Math.max(1e-3, d)], [0, 1], {...clampX, easing: curve});
export const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
export const lerp3 = (a: V3, b: V3, u: number): V3 => [lerp(a[0], b[0], u), lerp(a[1], b[1], u), lerp(a[2], b[2], u)];
export const rad = (deg: number) => (deg * Math.PI) / 180;
// a point on a sphere round `c` (azimuth from +z toward +x, elevation up), for orbit cameras
export const orbit = (c: V3, dist: number, azDeg: number, elDeg: number): V3 => [
  c[0] + dist * Math.cos(rad(elDeg)) * Math.sin(rad(azDeg)),
  c[1] + dist * Math.sin(rad(elDeg)),
  c[2] + dist * Math.cos(rad(elDeg)) * Math.cos(rad(azDeg)),
];

// ============================================================================================================================ loading
const kick = <T,>(p: Promise<T>, what: string) => p.catch((e) => {
  throw new Error(`kit3d: could not load ${what}: ${e && e.message ? e.message : e}`);
});
export const Load = {
  texture: (path: string, srgb = true) => kick(new THREE.TextureLoader().loadAsync(url(path)).then((t) => {
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = 16;
    return t;
  }), path),
  hdr: (path: string) => kick(new RGBELoader().loadAsync(url(path)).then((t) => {
    t.mapping = THREE.EquirectangularReflectionMapping;
    return t;
  }), path),
  pixels: (path: string) => kick(new Promise<ImageData>((resolve, reject) => {
    const im = new Image();
    im.onload = () => {
      const c = document.createElement('canvas');
      c.width = im.naturalWidth;
      c.height = im.naturalHeight;
      const g = c.getContext('2d', {willReadFrequently: true})!;
      g.drawImage(im, 0, 0);
      resolve(g.getImageData(0, 0, c.width, c.height));
    };
    im.onerror = () => reject(new Error('image error'));
    im.src = url(path);
  }), path),
  font: (path: string) => kick(new TTFLoader().loadAsync(url(path)).then((json) => new Font(json as never)), path),
  json: <T,>(path: string) => kick(fetch(url(path)).then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json() as Promise<T>;
  }), path),
};
// every asset of a piece in one hold: null until all are in
export function useAssets<T extends Record<string, unknown>>(key: string, load: () => Promise<T>): T | null {
  return useMeasured<T>(`kit3d:${key}`, load, `kit3d ${key}`);
}
export const all = async <T extends Record<string, Promise<unknown>>>(o: T): Promise<{[K in keyof T]: Awaited<T[K]>}> => {
  const keys = Object.keys(o);
  const vals = await Promise.all(keys.map((k) => o[k]));
  return Object.fromEntries(keys.map((k, i) => [k, vals[i]])) as {[K in keyof T]: Awaited<T[K]>};
};

// ============================================================================================================================ environment
// a panel of light in the environment, placed by azimuth (degrees from +z toward +x: the camera's side is +z) and elevation, `dist` away
export type Panel = {az: number; el: number; dist?: number; size: [number, number]; color?: string; intensity: number};
export type EnvSpec = {
  key: string;                       // what makes two specs the same bake (a canvas bakes once per key)
  panels?: Panel[];
  sweep?: Panel;                     // one strip that moves (its az/el per frame): re-baked each frame it moves (a few ms)
  hdri?: THREE.Texture;              // equirect, linear (RGBELoader)
  hdriLevel?: number;
  photo?: THREE.Texture;             // the shot's own picture wrapped round the scene, for reflections that carry its colours
  photoLevel?: number;
  base?: string;                     // the void's colour
  intensity?: number;
  rotation?: number;                 // radians about y
  showAsBackground?: boolean;
};
// a light studio, after the product-shot standard: one large soft key above-left, one tall strip right, a thin rim behind. A flat face
// seen from a camera at azimuth a mirrors the environment round azimuth -a (+-25 deg across a 30-deg lens): that is where a `sweep`
// strip has to pass to cross a glossy face.
export const STUDIO: Panel[] = [
  {az: -45, el: 32, size: [5, 2.6], intensity: 4},
  {az: 72, el: 4, size: [0.9, 7], intensity: 6},
  {az: 165, el: 12, size: [8, 0.6], intensity: 2.5},
];
// the sweep's strip at azimuth `az`
export const strip = (az: number, intensity = 5, el = 6): Panel => ({az, el, size: [0.7, 9], intensity});

const bakeEnv = (gl: THREE.WebGLRenderer, s: EnvSpec) => {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(s.base ?? '#000000');
  const dispose: Array<{dispose: () => void}> = [];
  const sphere = (tex: THREE.Texture, level: number) => {
    const t = tex;
    const prev = t.mapping;
    t.mapping = THREE.UVMapping;
    const geo = new THREE.SphereGeometry(40, 64, 32);
    const mat = new THREE.MeshBasicMaterial({map: t, side: THREE.BackSide, color: new THREE.Color(level, level, level), toneMapped: false});
    scene.add(new THREE.Mesh(geo, mat));
    dispose.push(geo, mat, {dispose: () => { t.mapping = prev; }});
  };
  if (s.hdri) sphere(s.hdri, s.hdriLevel ?? 1);
  if (s.photo) sphere(s.photo, s.photoLevel ?? 0.5);
  for (const p of [...(s.panels ?? []), ...(s.sweep ? [s.sweep] : [])]) {
    const geo = new THREE.PlaneGeometry(p.size[0], p.size[1]);
    const c = new THREE.Color(p.color ?? '#ffffff').multiplyScalar(p.intensity);
    const mat = new THREE.MeshBasicMaterial({color: c, side: THREE.DoubleSide, toneMapped: false});
    const m = new THREE.Mesh(geo, mat);
    m.position.set(...orbit([0, 0, 0], p.dist ?? 6, p.az, p.el));
    m.lookAt(0, 0, 0);
    scene.add(m);
    dispose.push(geo, mat);
  }
  const pmrem = new THREE.PMREMGenerator(gl);
  const rt = pmrem.fromScene(scene, 0, 0.1, 100);
  pmrem.dispose();
  for (const d of dispose) d.dispose();
  return rt;
};

const Envir: React.FC<{spec: EnvSpec}> = ({spec}) => {
  const {gl, scene} = useThree();
  const sweepKey = spec.sweep ? `${spec.sweep.az.toFixed(2)}|${spec.sweep.el.toFixed(2)}|${spec.sweep.intensity.toFixed(3)}` : '';
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const rt = useMemo(() => bakeEnv(gl, spec), [gl, spec.key, sweepKey]);
  useEffect(() => () => rt.dispose(), [rt]);
  useLayoutEffect(() => {
    scene.environment = rt.texture;
    scene.environmentIntensity = spec.intensity ?? 1;
    scene.environmentRotation.set(0, spec.rotation ?? 0, 0);
    if (spec.showAsBackground) {
      scene.background = rt.texture;
      scene.backgroundRotation.set(0, spec.rotation ?? 0, 0);
    }
  });
  return null;
};

// ============================================================================================================================ camera
const Rig: React.FC<{cam: Cam}> = ({cam}) => {
  const {camera} = useThree();
  // a layout effect: it runs before ThreeCanvas's frame renderer (an effect) calls advance() for this frame
  useLayoutEffect(() => {
    const c = camera as THREE.PerspectiveCamera;
    c.position.set(...cam.pos);
    c.up.set(...(cam.up ?? [0, 1, 0]));
    c.fov = cam.fov;
    c.near = cam.near ?? 0.05;
    c.far = cam.far ?? 200;
    c.lookAt(...cam.target);
    c.updateProjectionMatrix();
    c.updateMatrixWorld();
  });
  return null;
};

// a 3D point on screen (CSS px of the video, z < 1 when in front of the camera): the same camera, built in the page's own tree
export const project = (cam: Cam, p: V3, w = 1920, h = 1080) => {
  const c = new THREE.PerspectiveCamera(cam.fov, w / h, cam.near ?? 0.05, cam.far ?? 200);
  c.position.set(...cam.pos);
  c.up.set(...(cam.up ?? [0, 1, 0]));
  c.lookAt(...cam.target);
  c.updateProjectionMatrix();
  c.updateMatrixWorld();
  const v = new THREE.Vector3(...p).project(c);
  return {x: ((v.x + 1) / 2) * w, y: ((1 - v.y) / 2) * h, z: v.z};
};

// ============================================================================================================================ finish
export type PostSpec = {
  tone?: 'neutral' | 'agx' | 'aces' | 'none';
  exposure?: number;
  ssaa?: number;                      // 0 = MSAA x4; 1-3 = SSAA with 2^n samples (a still-clean edge on fine detail, n times the cost)
  bloom?: {strength: number; radius: number; threshold: number};
  grain?: number;                     // 0..0.06, in display space, seeded by the frame
  vignette?: number;                  // 0..1 (0 when the canvas is a transparent layer: the Stage below has its own)
  // the bloom's veil: three's UnrealBloomPass writes alpha 1 from its blur and adds it at the bloom's strength (0.2 x its mips' factors
  // 3.0 = 0.6), so a transparent canvas turns black at alpha 0.6 wherever nothing was drawn and the Stage under it shows at 0.4 of its
  // `dim`. false (the DEFAULT: the brighter of the two on an A/B): the bloom adds its light (the same colour as before) and leaves the
  // canvas's alpha as the scene drew it, so the ground shows at its own `dim` (a dark ground's mean 20.5 -> 49.9); true: the veil, only
  // to match a shot already made with it
  veil?: boolean;
};
const TONE = {neutral: THREE.NeutralToneMapping, agx: THREE.AgXToneMapping, aces: THREE.ACESFilmicToneMapping, none: THREE.NoToneMapping};

const FINISH = {
  uniforms: {tDiffuse: {value: null}, seed: {value: 0}, grain: {value: 0}, vignette: {value: 0}, res: {value: new THREE.Vector2(1, 1)}},
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float seed; uniform float grain; uniform float vignette; uniform vec2 res; varying vec2 vUv;
    // an integer hash (PCG) of the pixel and the frame: a float hash that repeats on whole pixels shows a ~10-px grid
    uint pcg(uint v){ uint s = v * 747796405u + 2891336453u; uint w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u; return (w >> 22u) ^ w; }
    float hash(vec2 p){ uvec2 q = uvec2(p); return float(pcg(q.x + pcg(q.y + pcg(uint(seed))))) / 4294967295.0; }
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      vec2 d = (vUv - 0.5) * vec2(1.0, 0.82);
      c.rgb *= 1.0 - vignette * smoothstep(0.28, 0.78, length(d) * 1.25);
      float n = hash(floor(vUv * res)) - 0.5;
      c.rgb += n * grain * c.a;
      gl_FragColor = c;
    }`,
};

const Post: React.FC<{spec: PostSpec}> = ({spec}) => {
  const {gl, scene, camera, size} = useThree();
  const frame = useCurrentFrame();
  const ssaa = spec.ssaa ?? 0;
  const bloomKey = spec.bloom ? `${spec.bloom.strength}|${spec.bloom.radius}|${spec.bloom.threshold}|${spec.veil === true ? 'veil' : 'clear'}` : '';
  const pipe = useMemo(() => {
    const dpr = gl.getPixelRatio();
    const w = Math.round(size.width * dpr);
    const h = Math.round(size.height * dpr);
    const rt = new THREE.WebGLRenderTarget(w, h, {type: THREE.HalfFloatType, samples: ssaa ? 0 : 4});
    const composer = new EffectComposer(gl, rt);
    composer.setPixelRatio(dpr);
    composer.setSize(size.width, size.height);
    if (ssaa) {
      const p = new SSAARenderPass(scene, camera, 0x000000, 0);
      p.sampleLevel = ssaa;
      p.unbiased = true;
      composer.addPass(p);
    } else {
      const p = new RenderPass(scene, camera);
      p.clearAlpha = 0;
      composer.addPass(p);
    }
    if (spec.bloom) {
      const bp = new UnrealBloomPass(new THREE.Vector2(w, h), spec.bloom.strength, spec.bloom.radius, spec.bloom.threshold);
      if (spec.veil !== true) {
        // its colour blended as three's AdditiveBlending does (src x src alpha + dst), its alpha not at all (PostSpec.veil)
        const m = bp.blendMaterial;
        m.blending = THREE.CustomBlending;
        m.blendEquation = THREE.AddEquation;
        m.blendSrc = THREE.SrcAlphaFactor;
        m.blendDst = THREE.OneFactor;
        m.blendEquationAlpha = THREE.AddEquation;
        m.blendSrcAlpha = THREE.ZeroFactor;
        m.blendDstAlpha = THREE.OneFactor;
        m.needsUpdate = true;
      }
      composer.addPass(bp);
    }
    composer.addPass(new OutputPass());
    const fin = new ShaderPass(FINISH);
    fin.uniforms.res.value.set(w, h);
    composer.addPass(fin);
    return {composer, fin};
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gl, scene, camera, size.width, size.height, ssaa, bloomKey]);
  useEffect(() => () => pipe.composer.dispose(), [pipe]);
  useLayoutEffect(() => {
    gl.toneMapping = TONE[spec.tone ?? 'neutral'];
    gl.toneMappingExposure = spec.exposure ?? 1;
    pipe.fin.uniforms.seed.value = frame % 997;
    pipe.fin.uniforms.grain.value = spec.grain ?? 0;
    pipe.fin.uniforms.vignette.value = spec.vignette ?? 0;
  });
  useFrame(() => {
    pipe.composer.render();
  }, 1);
  return null;
};

// without a composer: the renderer's own tone map (MSAA from the context)
const Tone: React.FC<{spec: PostSpec}> = ({spec}) => {
  const {gl} = useThree();
  useLayoutEffect(() => {
    gl.toneMapping = TONE[spec.tone ?? 'neutral'];
    gl.toneMappingExposure = spec.exposure ?? 1;
  });
  return null;
};

// ============================================================================================================================ the stage
export const Stage3D: React.FC<{
  kind: string;                       // the piece's name: data-kit3d, the gate's log
  cam: Cam;
  env?: EnvSpec;
  post?: PostSpec | false;            // false: no composer (a photo piece needs none)
  tone?: PostSpec['tone'];
  bg?: string;                        // an opaque clear colour; default transparent
  children?: React.ReactNode;
}> = ({kind, cam, env, post, tone = 'neutral', bg, children}) => {
  const {width, height} = useVideoConfig();
  if (gateOn) {
    gateLog('kit3d', {kind, frame: null});
    return <AbsoluteFill data-kit3d={kind} />;
  }
  return (
    <AbsoluteFill data-kit3d={kind}>
      <ThreeCanvas width={width} height={height} flat gl={{antialias: true, alpha: true, powerPreference: 'high-performance'}}
        camera={{fov: cam.fov, near: cam.near ?? 0.05, far: cam.far ?? 200, position: cam.pos}}>
        {bg ? <color attach="background" args={[bg]} /> : null}
        <Rig cam={cam} />
        {env ? <Envir spec={env} /> : null}
        {post ? <Post spec={{tone, ...post}} /> : <Tone spec={{tone}} />}
        {children}
      </ThreeCanvas>
    </AbsoluteFill>
  );
};

// a colour token as linear RGB for a material (three's Color does the sRGB -> linear step when ColorManagement is on, as it is)
export const col = (hex: string) => new THREE.Color(hex);
