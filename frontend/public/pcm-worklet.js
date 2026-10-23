class PCMProcessor extends AudioWorkletProcessor {
  constructor(){
    super();this.samples=[];this.position=0;this.pending=[];
    this.port.onmessage=event=>{
      if(event.data==='flush'){
        if(this.pending.length){const pcm=new Int16Array(this.pending);this.port.postMessage(pcm.buffer,[pcm.buffer]);this.pending=[];}
        this.port.postMessage({flushed:true});
      }
    };
  }
  process(inputs){
    const input=inputs[0]?.[0];if(!input)return true;
    for(const x of input)this.samples.push(x);
    const ratio=sampleRate/16000;
    const output=[];
    while(this.position+1<this.samples.length){
      const i=Math.floor(this.position),f=this.position-i;
      const value=this.samples[i]*(1-f)+this.samples[i+1]*f;
      output.push(Math.max(-32768,Math.min(32767,Math.round(value*32767))));this.position+=ratio;
    }
    const consumed=Math.min(Math.floor(this.position),this.samples.length);this.samples=this.samples.slice(consumed);this.position-=consumed;
    this.pending.push(...output);
    while(this.pending.length>=1600){const pcm=new Int16Array(this.pending.splice(0,1600));this.port.postMessage(pcm.buffer,[pcm.buffer]);}
    return true;
  }
}
registerProcessor('pcm-capture',PCMProcessor);
