// The gate probe's crash test: a probe must survive one graphic that throws on some frames (an easing over an empty list: interpolate
// [Infinity, Infinity]) once gate.tsx's GateBoundary has caught it and logged a refusal. This entry repeats that throw on frames 10-14 of
// a 30-frame composition; gate_probe.mjs must finish and log 5 refusals:
//   bash with_remotion_lock.sh "gate crash test" env QA_ENTRY=src/gatecrash_test_index.ts QA_COMP=GateCrash QA_GL=swangle \
//     QA_PUBLIC=<an empty dir> node gate_probe.mjs <out_dir> 0.25 0-29 1
import {registerRoot} from 'remotion';
import {GateCrashRoot} from './gatecrash_test';

registerRoot(GateCrashRoot);
