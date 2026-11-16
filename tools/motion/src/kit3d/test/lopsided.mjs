// the centring test's logo, as Emblem3D's <name>_shape.json holds one (image px of a 4000 x 2000 face): a ring on the left and a solid
// block on the right with a raised word block on it, so its weight sits right of its box's middle (a camera aimed at the box centre
// puts it visibly off centre: what the test must catch)
const circle = (cx, cy, r, n = 96, cw = false) =>
  Array.from({length: n}, (_, i) => {
    const a = ((cw ? -1 : 1) * 2 * Math.PI * i) / n;
    return [Math.round((cx + r * Math.cos(a)) * 10) / 10, Math.round((cy + r * Math.sin(a)) * 10) / 10];
  });
const rect = (x0, y0, x1, y1) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

export const lopsided = () => ({
  w: 4000, h: 2000, png: 'lopsided_4k.png',
  base: [{outer: circle(900, 1000, 800), holes: [circle(900, 1000, 560, 96, true)]}, {outer: rect(2000, 200, 3900, 1800), holes: []}],
  raised: [{outer: rect(2200, 700, 3700, 1300), holes: []}],
});
