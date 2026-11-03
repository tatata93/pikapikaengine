import http from 'node:http';
import {readFile,stat,mkdir,writeFile,rename} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const mime={'.html':'text/html; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.wasm':'application/wasm','.svg':'image/svg+xml','.wav':'audio/wav','.md':'text/plain; charset=utf-8'};
export function createServer({capture=false}={}) {
  const server=http.createServer(async(req,res)=>{
    try {
      const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
      if(pathname==='/__capture/float'){
        if(!capture||req.method!=='POST'){res.writeHead(404);res.end('Not found');return;}
        let origin;try{origin=new URL(req.headers.origin);}catch{}
        const port=server.address().port;
        if(!origin||origin.protocol!=='http:'||!['localhost','127.0.0.1'].includes(origin.hostname)||Number(origin.port)!==port){res.writeHead(403);res.end('Capture requires this local origin');return;}
        if(req.headers['content-type']?.split(';')[0]!=='application/json'){res.writeHead(415);res.end('JSON required');return;}
        const chunks=[];let bytes=0;for await(const chunk of req){bytes+=chunk.length;if(bytes>16*1024*1024){res.writeHead(413);res.end('Capture limit: 16 MiB');return;}chunks.push(chunk);}
        const body=Buffer.concat(chunks),data=JSON.parse(body.toString('utf8'));
        if(data.schema!==1||!data.simulation||!data.render){res.writeHead(400);res.end('Invalid measurement');return;}
        const directory=path.join(root,'build/browser-capture'),name=`float-${port}.json`,file=path.join(directory,name);
        await mkdir(directory,{recursive:true});await writeFile(file+'.tmp',body);await rename(file+'.tmp',file);
        res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify({saved:true,bytes,file:name}));return;
      }
      const parts=pathname.split('/');
      if(parts.some(p=>p.startsWith('.')||p.includes('\\'))||pathname.includes('\0')) {res.writeHead(403);res.end('Forbidden');return;}
      let file=path.resolve(root,'.'+pathname);
      if(file!==root&&!file.startsWith(root+path.sep)) {res.writeHead(403);res.end('Forbidden');return;}
      if((await stat(file)).isDirectory()) file=path.join(file,'index.html');
      const content=await readFile(file);
      res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp'});res.end(content);
    } catch {res.writeHead(404);res.end('Not found');}
  });
  return server;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  const port=Number(process.env.PORT||8080);
  const server=createServer({capture:process.argv.includes('--capture')});server.on('error',e=>{console.error(e.message);process.exitCode=1;});
  server.listen(port,'127.0.0.1',()=>console.log(`pikapikaengine: http://localhost:${port} (local only)`));
}
