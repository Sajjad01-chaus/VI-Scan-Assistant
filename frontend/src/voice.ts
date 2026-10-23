export type VoiceHandle={stop:()=>void;cancel:()=>void};
export async function startVoice(sessionId:string,onEvent:(event:any)=>void,autoEnd=true):Promise<VoiceHandle>{
  const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,channelCount:1}});
  const context=new AudioContext();
  let node:AudioWorkletNode|undefined,stopped=false,stopping=false,cancelled=false;
  let timer:ReturnType<typeof setTimeout>,flushTimer:ReturnType<typeof setTimeout>;
  let speechMs=0,lastSpeech=0;
  const ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/sessions/${sessionId}/voice`);
  const cleanup=()=>{stream.getTracks().forEach(t=>t.stop());node?.disconnect();if(context.state!=='closed')void context.close().catch(()=>{});clearTimeout(timer);clearTimeout(flushTimer);};
  function finish(){if(stopped||cancelled)return;stopped=true;cleanup();if(ws.readyState===WebSocket.OPEN)ws.send(JSON.stringify({type:'stop'}));}
  const handle={stop:()=>{
    if(stopped||stopping||cancelled)return;
    if(!node){handle.cancel();onEvent({type:'voice.cancelled'});return;}
    stopping=true;clearTimeout(timer);onEvent({type:'voice.finalizing'});
    node.port.postMessage('flush');flushTimer=setTimeout(finish,200);
  },cancel:()=>{cancelled=true;stopped=true;cleanup();ws.close();}};
  ws.onmessage=async message=>{
    if(cancelled)return;
    const event=JSON.parse(message.data);
    if(event.type==='voice.ready'){
      if(stopped)return;
      try{await context.audioWorklet.addModule('/pcm-worklet.js');}catch{handle.cancel();onEvent({type:'error',message:'Audio capture could not start. Use typed input.'});return;}
      if(cancelled)return;
      node=new AudioWorkletNode(context,'pcm-capture');
      node.port.onmessage=({data})=>{
        if(data?.flushed){finish();return;}
        if(ws.readyState!==WebSocket.OPEN||stopped||cancelled)return;
        if(ws.bufferedAmount>128000){handle.cancel();onEvent({type:'error',message:'Voice connection is too slow. Retry or use typed input.'});return;}
        ws.send(data);
        if(autoEnd&&!stopping){
          const samples=new Int16Array(data as ArrayBuffer);let energy=0;
          for(const sample of samples)energy+=sample*sample;
          const rms=Math.sqrt(energy/Math.max(samples.length,1)),now=performance.now();
          if(rms>450){speechMs+=samples.length/16;lastSpeech=now;}
          if(speechMs>=300&&lastSpeech&&now-lastSpeech>1600)handle.stop();
        }
      };
      const mute=context.createGain();mute.gain.value=0;
      context.createMediaStreamSource(stream).connect(node);node.connect(mute).connect(context.destination);
      timer=setTimeout(()=>handle.stop(),19000);
    }
    if(event.type==='transcript.final'||event.type==='error'){stopped=true;cleanup();}
    onEvent(event);
  };
  ws.onerror=()=>{if(cancelled)return;stopped=true;cleanup();onEvent({type:'error',message:'Voice connection failed. Use a typed transcript.'});};
  ws.onclose=()=>{cleanup();if(!stopped&&!cancelled){stopped=true;onEvent({type:'error',message:'Voice session closed. Try again or type your request.'});}};
  return handle;
}
