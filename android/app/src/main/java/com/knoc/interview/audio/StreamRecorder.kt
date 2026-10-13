package com.knoc.interview.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import java.io.ByteArrayOutputStream

class StreamRecorder(
    private val sampleRate: Int = 16000,
    private val chunkSeconds: Int = 3
) {

    companion object {
        private const val TAG = "StreamRecorder"
    }

    private var audioRecord: AudioRecord? = null
    private var running = false
    private var thread: Thread? = null

    private val _chunks = MutableSharedFlow<ByteArray>(
        replay = 0,
        extraBufferCapacity = 8
    )
    val chunks: SharedFlow<ByteArray> = _chunks.asSharedFlow()

    @SuppressLint("MissingPermission")
    fun start() {
        if (running) return

        val minBuf = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )
        if (minBuf <= 0) throw RuntimeException("Bad buffer size: $minBuf")

        val record = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            minBuf * 4
        )

        if (record.state != AudioRecord.STATE_INITIALIZED) {
            record.release()
            throw RuntimeException("AudioRecord init failed")
        }

        audioRecord = record
        running = true
        record.startRecording()

        val bytesPerSecond = sampleRate * 2
        val chunkBytes = bytesPerSecond * chunkSeconds

        thread = Thread {
            val readBuf = ByteArray(minBuf)
            val chunkBuf = ByteArrayOutputStream(chunkBytes + minBuf)

            while (running) {
                val read = record.read(readBuf, 0, readBuf.size)
                if (read > 0) {
                    chunkBuf.write(readBuf, 0, read)
                    if (chunkBuf.size() >= chunkBytes) {
                        val raw = chunkBuf.toByteArray()
                        chunkBuf.reset()

                        if (!AudioFilter.hasSpeech(raw, sampleRate)) {
                            Log.d(TAG, "Skipping — no speech")
                            continue
                        }

                        val filtered = AudioFilter.process(raw, sampleRate)
                        Log.d(TAG, "Emitting chunk: ${filtered.size} bytes")
                        _chunks.tryEmit(filtered)
                    }
                } else if (read < 0) {
                    Log.e(TAG, "AudioRecord error: $read")
                    break
                }
            }
            chunkBuf.close()
        }.also { it.start() }
    }

    fun stop() {
        running = false
        try { thread?.join(1000) } catch (_: InterruptedException) {}
        thread = null
        try { audioRecord?.stop() } catch (_: Exception) {}
        try { audioRecord?.release() } catch (_: Exception) {}
        audioRecord = null
    }
}