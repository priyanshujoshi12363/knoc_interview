package com.knoc.interview

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import java.io.ByteArrayOutputStream

class PcmRecorder {

    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var recordThread: Thread? = null
    private val buffer = ByteArrayOutputStream()

    @SuppressLint("MissingPermission")
    fun start() {
        val minBuf = AudioRecord.getMinBufferSize(
            NetworkConfig.SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )
        if (minBuf == AudioRecord.ERROR || minBuf == AudioRecord.ERROR_BAD_VALUE) {
            throw RuntimeException("AudioRecord buffer size failed")
        }

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            NetworkConfig.SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            minBuf * 2
        )

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            throw RuntimeException("AudioRecord init failed")
        }

        buffer.reset()
        isRecording = true
        audioRecord?.startRecording()

        recordThread = Thread {
            val chunk = ByteArray(minBuf)
            while (isRecording) {
                val read = audioRecord?.read(chunk, 0, chunk.size) ?: 0
                if (read > 0) {
                    synchronized(buffer) {
                        buffer.write(chunk, 0, read)
                    }
                }
            }
        }.also { it.start() }
    }

    fun stop(): ByteArray {
        isRecording = false
        try { recordThread?.join(500) } catch (_: InterruptedException) {}
        recordThread = null
        try { audioRecord?.stop() } catch (_: Exception) {}
        try { audioRecord?.release() } catch (_: Exception) {}
        audioRecord = null
        synchronized(buffer) {
            return buffer.toByteArray()
        }
    }
}
