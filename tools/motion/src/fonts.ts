// fonts.ts: the studio's font shelf. A look (src/look.json) names its families from this list; each is a Google Font (SIL Open Font
// License) through @remotion/google-fonts, loaded only when a look uses it. To give a creator a family that is not here, add its import
// and its line in SHELF (the name exactly as Google Fonts spells it); `node -e "console.log(require('@remotion/google-fonts/<Name>')
// .getInfo().fonts)"` lists its weights.
import * as BebasNeue from '@remotion/google-fonts/BebasNeue';
import * as BarlowCondensed from '@remotion/google-fonts/BarlowCondensed';
import * as BricolageGrotesque from '@remotion/google-fonts/BricolageGrotesque';
import * as DMSans from '@remotion/google-fonts/DMSans';
import * as Figtree from '@remotion/google-fonts/Figtree';
import * as Fraunces from '@remotion/google-fonts/Fraunces';
import * as IBMPlexSans from '@remotion/google-fonts/IBMPlexSans';
import * as JetBrainsMono from '@remotion/google-fonts/JetBrainsMono';
import * as LeagueSpartan from '@remotion/google-fonts/LeagueSpartan';
import * as Lexend from '@remotion/google-fonts/Lexend';
import * as Lora from '@remotion/google-fonts/Lora';
import * as Manrope from '@remotion/google-fonts/Manrope';
import * as Oswald from '@remotion/google-fonts/Oswald';
import * as Outfit from '@remotion/google-fonts/Outfit';
import * as PlusJakartaSans from '@remotion/google-fonts/PlusJakartaSans';
import * as Rubik from '@remotion/google-fonts/Rubik';
import * as Sora from '@remotion/google-fonts/Sora';
import * as Unbounded from '@remotion/google-fonts/Unbounded';
import * as WorkSans from '@remotion/google-fonts/WorkSans';

type Loaded = {fontFamily: string; waitUntilDone: () => Promise<unknown>};
type Mod = {loadFont: (style?: string, opts?: {weights?: string[]; subsets?: string[]}) => Loaded;
  getInfo: () => {fontFamily: string; fonts: Record<string, Record<string, unknown>>; subsets?: string[]}};

const SHELF: Record<string, unknown> = {
  'Bebas Neue': BebasNeue, 'Barlow Condensed': BarlowCondensed, 'Bricolage Grotesque': BricolageGrotesque, 'DM Sans': DMSans,
  Figtree, Fraunces, 'IBM Plex Sans': IBMPlexSans, 'JetBrains Mono': JetBrainsMono, 'League Spartan': LeagueSpartan, Lexend, Lora,
  Manrope, Oswald, Outfit, 'Plus Jakarta Sans': PlusJakartaSans, Rubik, Sora, Unbounded, 'Work Sans': WorkSans,
};
export const FAMILIES = Object.keys(SHELF);

const cache: Record<string, Loaded> = {};
// one family at the weights asked for (a weight the family lacks is dropped; italics come with it where the family has them)
export const loadFamily = (family: string, weights: number[]): Loaded => {
  const key = `${family}|${weights.join(',')}`;
  if (cache[key]) return cache[key];
  const m = SHELF[family] as Mod | undefined;
  if (!m) throw new Error(`font "${family}" is not on the shelf (src/fonts.ts): add its @remotion/google-fonts import there first`);
  const info = m.getInfo();
  const have = Object.keys(info.fonts.normal ?? {});
  const ws = weights.map(String).filter((w) => have.includes(w));
  const use = ws.length ? ws : [have[have.length - 1]];
  // Latin and, where the family has it, Latin Extended (the accented letters of Polish, Turkish, Vietnamese and more)
  const subsets = ['latin', 'latin-ext'].filter((s) => (info.subsets ?? ['latin']).includes(s));
  const normal = m.loadFont('normal', {weights: use, subsets});
  if (info.fonts.italic) {
    const it = Object.keys(info.fonts.italic).filter((w) => use.includes(w));
    if (it.length) m.loadFont('italic', {weights: it, subsets});
  }
  cache[key] = normal;
  return normal;
};
