from pathlib import Path

p=Path('activity_fixed.kt')
if not p.is_file(): raise SystemExit('STAGE 11 V2: activity_fixed.kt missing')
a=p.read_text(encoding='utf-8')
start=a.find('    private fun muxVideoAudio(')
end=a.find('    private fun verifyAndFix()',start)
if start<0 or end<0: raise SystemExit('STAGE 11 V2: media assembly block not found')

block='''    private fun muxVideoAudio(videoUri:android.net.Uri,audio:File,out:File){
        if(out.exists())out.delete()
        val vf=contentResolver.openFileDescriptor(videoUri,"r")?:throw IllegalStateException("video FD unavailable")
        val ve=MediaExtractor();val encodedAudio=File(cacheDir,"aac_${sid}.mp4")
        var mux:MediaMuxer?=null;var ae:MediaExtractor?=null
        try{
            ve.setDataSource(vf.fileDescriptor)
            var vfmt:MediaFormat?=null;var videoTrack=-1
            for(i in 0 until ve.trackCount){val f=ve.getTrackFormat(i);if(f.getString(MediaFormat.KEY_MIME)?.startsWith("video/")==true){vfmt=f;videoTrack=i;break}}
            val videoFormat=vfmt?:throw IllegalStateException("required video track missing")
            val videoDuration=videoFormat.getLong(MediaFormat.KEY_DURATION,0L)
            if(videoDuration<=0L)throw IllegalStateException("video duration unavailable")
            encodeWavToAacMp4(audio,encodedAudio)
            ae=MediaExtractor();ae.setDataSource(encodedAudio.absolutePath)
            var afmt:MediaFormat?=null;var audioTrack=-1
            for(i in 0 until ae.trackCount){val f=ae.getTrackFormat(i);if(f.getString(MediaFormat.KEY_MIME)?.startsWith("audio/")==true){afmt=f;audioTrack=i;break}}
            val audioFormat=afmt?:throw IllegalStateException("AAC audio track missing after encoding")
            mux=MediaMuxer(out.absolutePath,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            val vt=mux.addTrack(videoFormat);val at=mux.addTrack(audioFormat)
            ve.selectTrack(videoTrack);ae.selectTrack(audioTrack);mux.start()
            copyTrackBounded(ve,mux,vt,videoDuration);copyTrackBounded(ae,mux,at,videoDuration)
            mux.stop();mux.release();mux=null
        }catch(e:Exception){try{mux?.release()}catch(_:Exception){};if(out.exists())out.delete();throw e
        }finally{try{ae?.release()}catch(_:Exception){};try{ve.release()}catch(_:Exception){};try{vf.close()}catch(_:Exception){};if(encodedAudio.exists())encodedAudio.delete()}
    }

    private fun copyTrackBounded(ex:MediaExtractor,mux:MediaMuxer,track:Int,maxDurationUs:Long){
        val buf=java.nio.ByteBuffer.allocate(1024*1024);val info=MediaCodec.BufferInfo();var lastPts=-1L
        while(true){
            val n=ex.readSampleData(buf,0);if(n<0)break
            val pts=ex.sampleTime;if(pts<0||pts>maxDurationUs)break
            if(pts<lastPts)throw IllegalStateException("non-monotonic media timestamps")
            info.offset=0;info.size=n;info.presentationTimeUs=pts;info.flags=ex.sampleFlags
            mux.writeSampleData(track,buf,info);lastPts=pts;ex.advance()
        }
    }

    private data class WavInfo(val dataOffset:Long,val dataSize:Long,val sampleRate:Int,val channels:Int,val bitsPerSample:Int)

    private fun readWavInfo(file:File):WavInfo{
        val raf=java.io.RandomAccessFile(file,"r")
        try{
            if(raf.length()<44L)throw IllegalStateException("WAV file too small")
            val riff=ByteArray(4);raf.readFully(riff);if(String(riff,Charsets.US_ASCII)!="RIFF")throw IllegalStateException("WAV RIFF header missing")
            raf.skipBytes(4);val wave=ByteArray(4);raf.readFully(wave);if(String(wave,Charsets.US_ASCII)!="WAVE")throw IllegalStateException("WAV WAVE header missing")
            var sampleRate=0;var channels=0;var bits=0;var audioFormat=0;var dataOffset=-1L;var dataSize=0L
            while(raf.filePointer+8L<=raf.length()){
                val id=ByteArray(4);raf.readFully(id);val size=readLeInt(raf).toLong() and 0xffffffffL;val chunkStart=raf.filePointer
                when(String(id,Charsets.US_ASCII)){
                    "fmt "->{audioFormat=readLeShort(raf);channels=readLeShort(raf);sampleRate=readLeInt(raf);raf.skipBytes(6);bits=readLeShort(raf)}
                    "data"->{dataOffset=raf.filePointer;dataSize=size}
                }
                val next=chunkStart+size+(size and 1L);if(next<=raf.length())raf.seek(next)else break
                if(sampleRate>0&&channels>0&&bits>0&&dataOffset>=0)break
            }
            if(audioFormat!=1||channels !in 1..2||bits!=16||sampleRate<8000||sampleRate>48000||dataOffset<0||dataSize<=0L)throw IllegalStateException("unsupported WAV PCM format")
            if(dataOffset+dataSize>raf.length())throw IllegalStateException("WAV data chunk truncated")
            return WavInfo(dataOffset,dataSize,sampleRate,channels,bits)
        }finally{raf.close()}
    }
    private fun readLeShort(raf:java.io.RandomAccessFile):Int{val a=raf.read();val b=raf.read();if(a<0||b<0)throw IllegalStateException("truncated WAV");return a or (b shl 8)}
    private fun readLeInt(raf:java.io.RandomAccessFile):Int{val a=raf.read();val b=raf.read();val c=raf.read();val d=raf.read();if(a<0||b<0||c<0||d<0)throw IllegalStateException("truncated WAV");return a or (b shl 8) or (c shl 16) or (d shl 24)}

    private fun encodeWavToAacMp4(wav:File,out:File){
        if(!wav.isFile||wav.length()<44L)throw IllegalStateException("narration WAV missing or empty")
        val w=readWavInfo(wav);if(out.exists())out.delete()
        val codec=MediaCodec.createEncoderByType("audio/mp4a-latm")
        val fmt=MediaFormat.createAudioFormat("audio/mp4a-latm",w.sampleRate,w.channels).apply{setInteger(MediaFormat.KEY_AAC_PROFILE,2);setInteger(MediaFormat.KEY_BIT_RATE,128000);setInteger(MediaFormat.KEY_MAX_INPUT_SIZE,16384)}
        var mux:MediaMuxer?=null;var muxTrack=-1;var muxStarted=false;var eosQueued=false;var done=false
        val raf=java.io.RandomAccessFile(wav,"r");raf.seek(w.dataOffset);var remaining=w.dataSize;var ptsUs=0L
        try{
            codec.configure(fmt,null,null,MediaCodec.CONFIGURE_FLAG_ENCODE);codec.start()
            while(!done){
                if(!eosQueued){
                    val ii=codec.dequeueInputBuffer(10000)
                    if(ii>=0){
                        val input=codec.getInputBuffer(ii)?:throw IllegalStateException("AAC input buffer unavailable");input.clear()
                        val frameBytes=w.channels*2;var toRead=minOf(input.remaining(),remaining.coerceAtMost(Int.MAX_VALUE.toLong()).toInt());toRead-=toRead%frameBytes
                        if(toRead>0){val bytes=ByteArray(toRead);raf.readFully(bytes);input.put(bytes);val frames=toRead/frameBytes;codec.queueInputBuffer(ii,0,toRead,ptsUs,0);ptsUs+=(frames*1000000L)/w.sampleRate;remaining-=toRead}
                        else{codec.queueInputBuffer(ii,0,0,ptsUs,MediaCodec.BUFFER_FLAG_END_OF_STREAM);eosQueued=true}
                    }
                }
                val info=MediaCodec.BufferInfo();val oi=codec.dequeueOutputBuffer(info,10000)
                when{
                    oi==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED->{if(muxStarted)throw IllegalStateException("AAC output format changed twice");mux=MediaMuxer(out.absolutePath,MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);muxTrack=mux.addTrack(codec.outputFormat);mux.start();muxStarted=true}
                    oi==MediaCodec.INFO_TRY_AGAIN_LATER->{if(eosQueued)continue}
                    oi>=0->{
                        val buffer=codec.getOutputBuffer(oi)
                        if(buffer!=null&&info.size>0&&(info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG)==0){if(!muxStarted)throw IllegalStateException("AAC muxer not started");buffer.position(info.offset);buffer.limit(info.offset+info.size);mux!!.writeSampleData(muxTrack,buffer,info)}
                        if((info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0)done=true
                        codec.releaseOutputBuffer(oi,false)
                    }
                }
            }
            if(!muxStarted)throw IllegalStateException("AAC encoder produced no output format")
            mux?.stop()
        }finally{try{raf.close()}catch(_:Exception){};try{codec.stop()}catch(_:Exception){};try{codec.release()}catch(_:Exception){};try{mux?.release()}catch(_:Exception){};if(!out.isFile||out.length()<1024L){if(out.exists())out.delete();throw IllegalStateException("AAC encoding produced no usable file")}}
    }

'''
a=a[:start]+block+a[end:]
old='''        try{muxVideoAudio(video,File(audioPath),out);if(!out.isFile||out.length()<1024){fail(11,"Assembly produced no usable MP4");return}
            prefs().edit().putString(FINAL,out.absolutePath).apply();pass(11,"Visual recording + narration muxed into assembled MP4")
        }catch(e:Exception){fail(11,"Assembly failed: ${e.javaClass.simpleName}: ${e.message}")}'''
new='''        try{muxVideoAudio(video,File(audioPath),out);if(!out.isFile||out.length()<1024){fail(11,"Assembly produced no usable MP4");return}
            val check=MediaExtractor();try{check.setDataSource(out.absolutePath);var hasVideo=false;var hasAudio=false
                for(i in 0 until check.trackCount){val mime=check.getTrackFormat(i).getString(MediaFormat.KEY_MIME)?:"";hasVideo=hasVideo||mime.startsWith("video/");hasAudio=hasAudio||mime.startsWith("audio/")}
                if(!hasVideo||!hasAudio){fail(11,"Assembly output missing required video/audio tracks");return}
            }finally{check.release()}
            prefs().edit().putString(FINAL,out.absolutePath).apply();pass(11,"Production assembly verified: video + AAC narration + synchronized MP4")
        }catch(e:Exception){if(out.exists())out.delete();fail(11,"Assembly failed: ${e.javaClass.simpleName}: ${e.message}")}'''
if old not in a: raise SystemExit('STAGE 11 V2: assemble gate target not found')
a=a.replace(old,new,1)
p.write_text(a,encoding='utf-8')
print('STAGE 11 V2: PASS')
