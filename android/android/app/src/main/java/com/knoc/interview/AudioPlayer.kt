package com.knoc.interview

import android.media.MediaPlayer
import android.util.Base64
import java.io.File
import java.io.FileOutputStream

object AudioPlayer {

    private var player: MediaPlayer? = null

    fun playBase64Wav(context: android.content.Context, audioB64: String, onDone: () -> Unit = {}) {
        stop()
        val bytes = Base64.decode(audioB64, Base64.DEFAULT)
        val tmp = File(context.cacheDir, "tts_${System.currentTimeMillis()}.wav")
        FileOutputStream(tmp).use { it.write(bytes) }

        val mp = MediaPlayer()
        player = mp
        mp.setDataSource(tmp.absolutePath)
        mp.setOnCompletionListener {
            onDone()
            tmp.delete()
            stop()
        }
        mp.setOnErrorListener { _, _, _ ->
            tmp.delete()
            stop()
            onDone()
            true
        }
        mp.prepare()
        mp.start()
    }

    fun stop() {
        try {
            player?.stop()
            player?.release()
        } catch (_: Exception) {}
        player = null
    }
}
