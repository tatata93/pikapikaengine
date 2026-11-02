import {readdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
for(const dir of ['engine','samples','scripts','tests','tools','docs/learn']) {
  for(const name of await readdir(new URL('../'+dir+'/',import.meta.url))) if(name.endsWith('.mjs')) {
    const result=spawnSync(process.execPath,['--check',new URL('../'+dir+'/'+name,import.meta.url).pathname.replace(/^\/([A-Z]:)/,'$1')],{encoding:'utf8'});
    if(result.status) {console.error(result.stderr);process.exitCode=1;}
  }
}
