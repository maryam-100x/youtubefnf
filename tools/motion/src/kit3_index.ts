// kit3's demo alone (src/kit3/Kit3Demo.tsx): its stills render even when another composition's module throws at import.
//   QA_ENTRY=src/kit3_index.ts QA_COMP=Kit3Demo node stills.mjs <out> 1 <frames>
//   node kit3_proof.mjs <out>   (the demo's stills + every refusal case, one bundle; standard/KIT3.md "The proof")
import {registerRoot} from 'remotion';
import {Kit3Root} from './kit3/Kit3Demo';

registerRoot(Kit3Root);
