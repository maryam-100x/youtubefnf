// kit3d's demo alone (src/kit3d/Kit3dDemo.tsx): its stills and clips render even when another composition's module throws at import.
//   bash with_remotion_lock.sh "kit3d proof" node kit3d_proof.mjs <out_dir> [stills|clips|all]
import {registerRoot} from 'remotion';
import {Kit3dRoot} from './kit3d/Kit3dDemo';

registerRoot(Kit3dRoot);
