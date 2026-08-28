package com.kunal.universalvideo

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.media.MediaRecorder
import android.speech.tts.TextToSpeech
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.PI
import kotlin.math.sin

/**
 * Local, deterministic production asset layer.
 * No copyrighted media is downloaded: music and backgrounds are generated locally.
 * Voice uses the device TTS voice selected by Android, with conservative character/emotion shaping.
 */
object ProductionAssetEngine {
    enum class Emotion { NEUTRAL, HAPPY, SAD, CRYING, ANGRY, FEAR, SHOCKING, CALM }

    data class CharacterVoice(
        val id: String,
        val language: String = "en-US",
        val rate: Float = 1.0f,
        val pitch: Float = 1.0f
    )

    fun detectEmotion(text: String): Emotion {
        val s = text.lowercase()
        return when {
            listOf("shock", "shocking", "suddenly", "surprise", "surprised", "boom").any(s::contains) -> Emotion.SHOCKING
            listOf("cry", "crying", "tears", "wept", "sob", "sobbing").any(s::contains) -> Emotion.CRYING
            listOf("fear", "afraid", "scared", "terrified", "horror").any(s::contains) -> Emotion.FEAR
            listOf("angry", "rage", "furious", "shout", "fight").any(s::contains) -> Emotion.ANGRY
            listOf("sad", "sadness", "lost", "alone", "heartbroken").any(s::contains) -> Emotion.SAD
            listOf("happy", "laugh", "funny", "smile", "joy").any(s::contains) -> Emotion.HAPPY
            listOf("calm", "peace", "quiet").any(s::contains) -> Emotion.CALM
            else -> Emotion.NEUTRAL
        }
    }

    fun voiceFor(characterId: String, emotion: Emotion): CharacterVoice {
        val seed = characterId.hashCode().absoluteValue % 5
        val basePitch = 0.92f + seed * 0.045f
        val baseRate = 0.94f + (seed % 3) * 0.04f
        val (r, p) = when (emotion) {
            Emotion.HAPPY -> 1.06f to 1.10f
            Emotion.SAD -> 0.88f to 0.93f
            Emotion.CRYING -> 0.82f to 0.88f
            Emotion.ANGRY -> 1.08f to 0.92f
            Emotion.FEAR -> 1.12f to 1.08f
            Emotion.SHOCKING -> 1.18f to 1.12f
            Emotion.CALM -> 0.90f to 0.96f
            Emotion.NEUTRAL -> 1.0f to 1.0f
        }
        return CharacterVoice(characterId, rate = (baseRate * r).coerceIn(0.70f, 1.35f), pitch = (basePitch * p).coerceIn(0.65f, 1.35f))
    }

    fun configure(tts: TextToSpeech, voice: CharacterVoice) {
        tts.language = java.util.Locale.forLanguageTag(voice.language)
        tts.setSpeechRate(voice.rate)
        tts.setPitch(voice.pitch)
    }

    fun generateMusic(emotion: Emotion, durationMs: Long, out: File): Boolean {
        val duration = durationMs.coerceIn(1500L, 120000L)
        val sampleRate = 22050
        val frames = (duration * sampleRate / 1000L).toInt()
        val root = when (emotion) {
            Emotion.HAPPY -> 261.63
            Emotion.SAD, Emotion.CRYING -> 196.00
            Emotion.ANGRY -> 146.83
            Emotion.FEAR -> 110.00
            Emotion.SHOCKING -> 329.63
            Emotion.CALM -> 220.00
            Emotion.NEUTRAL -> 220.00
        }
        val chord = doubleArrayOf(root, root * 1.25, root * 1.5)
        FileOutputStream(out).use { fos ->
            writeWavHeader(fos, sampleRate, frames)
            val buf = ByteArray(4096)
            var i = 0
            while (i < frames) {
                var p = 0
                while (p + 1 < buf.size && i < frames) {
                    val t = i.toDouble() / sampleRate
                    val fade = minOf(1.0, t * 4.0, (duration / 1000.0 - t) * 4.0).coerceAtLeast(0.0)
                    val tremolo = 0.72 + 0.28 * sin(2.0 * PI * 0.7 * t)
                    val sample = chord.mapIndexed { idx, f -> sin(2.0 * PI * f * t + idx * 0.7) * (0.16 / (idx + 1)) }.sum() * fade * tremolo
                    val value = (sample.coerceIn(-0.95, 0.95) * Short.MAX_VALUE).toInt().toShort()
                    buf[p++] = (value.toInt() and 0xff).toByte()
                    buf[p++] = ((value.toInt() shr 8) and 0xff).toByte()
                    i++
                }
                fos.write(buf, 0, p)
            }
        }
        return out.exists() && out.length() > 44
    }

    fun generateBackground(emotion: Emotion, sceneIndex: Int, out: File): Boolean {
        val w = 1280; val h = 720
        val bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG)
        val bg = when (emotion) {
            Emotion.HAPPY -> 0xFFFFE082.toInt()
            Emotion.SAD, Emotion.CRYING -> 0xFF6B7FA3.toInt()
            Emotion.ANGRY -> 0xFF8B3A3A.toInt()
            Emotion.FEAR -> 0xFF25283D.toInt()
            Emotion.SHOCKING -> 0xFF6A4FB3.toInt()
            Emotion.CALM -> 0xFF6EA7A1.toInt()
            Emotion.NEUTRAL -> 0xFF8DA0A8.toInt()
        }
        canvas.drawColor(bg)
        paint.color = 0x55FFFFFF
        for (i in 0 until 7) {
            val x = ((sceneIndex * 137 + i * 191) % w).toFloat()
            val y = (120 + i * 83).toFloat()
            canvas.drawCircle(x, y, 45f + i * 8f, paint)
        }
        paint.color = 0xAA000000.toInt()
        canvas.drawRect(RectF(0f, h * 0.78f, w.toFloat(), h.toFloat()), paint)
        paint.color = 0xCCFFFFFF.toInt()
        paint.textSize = 42f
        canvas.drawText("KUV • SCENE $sceneIndex", 48f, 92f, paint)
        FileOutputStream(out).use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bitmap.recycle()
        return out.exists() && out.length() > 100
    }

    private fun writeWavHeader(out: FileOutputStream, sampleRate: Int, frames: Int) {
        val dataSize = frames * 2
        val total = 36 + dataSize
        val h = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
        h.put("RIFF".toByteArray()); h.putInt(total); h.put("WAVE".toByteArray())
        h.put("fmt ".toByteArray()); h.putInt(16); h.putShort(1); h.putShort(1)
        h.putInt(sampleRate); h.putInt(sampleRate * 2); h.putShort(2); h.putShort(16)
        h.put("data".toByteArray()); h.putInt(dataSize)
        out.write(h.array())
    }
}
