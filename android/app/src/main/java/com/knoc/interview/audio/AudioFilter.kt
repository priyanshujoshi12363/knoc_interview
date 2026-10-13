package com.knoc.interview.audio

import kotlin.math.abs
import kotlin.math.sqrt

object AudioFilter {

    private const val DC_ALPHA = 0.995f
    private const val HPF_CUTOFF = 80.0f
    private const val PREEMPHASIS_ALPHA = 0.97f
    private const val NOISE_GATE_RMS = 250.0
    private const val AGC_TARGET_RMS = 3000.0
    private const val AGC_MAX_GAIN = 6.0f
    private const val AGC_MIN_GAIN = 0.5f
    private const val VAD_MIN_SPEECH_MS = 400

    fun process(
        pcm: ByteArray,
        sampleRate: Int = 16000
    ): ByteArray {
        if (pcm.size < 4) return pcm

        val samples = bytesToShorts(pcm)
        if (samples.isEmpty()) return pcm

        removeDcOffset(samples)
        applyHighPassFilter(samples, sampleRate)
        applyNoiseGate(samples)
        applyAgc(samples, sampleRate)
        applyPreEmphasis(samples)

        return shortsToBytes(samples)
    }

    fun hasSpeech(
        pcm: ByteArray,
        sampleRate: Int = 16000
    ): Boolean {
        if (pcm.size < 4) return false

        val samples = bytesToShorts(pcm)
        val minSamples = (sampleRate * VAD_MIN_SPEECH_MS / 1000)

        var speechCount = 0
        val windowSize = sampleRate / 50

        var i = 0
        while (i + windowSize <= samples.size) {
            var sum = 0.0
            for (j in i until i + windowSize) {
                val s = samples[j].toDouble()
                sum += s * s
            }
            val rms = sqrt(sum / windowSize)

            if (rms > 350.0) speechCount += windowSize

            i += windowSize
        }

        return speechCount >= minSamples
    }

    private fun bytesToShorts(pcm: ByteArray): ShortArray {
        val out = ShortArray(pcm.size / 2)
        var i = 0
        var j = 0
        while (i + 1 < pcm.size) {
            val lo = pcm[i].toInt() and 0xFF
            val hi = pcm[i + 1].toInt()
            out[j] = ((hi shl 8) or lo).toShort()
            i += 2
            j++
        }
        return out
    }

    private fun shortsToBytes(samples: ShortArray): ByteArray {
        val out = ByteArray(samples.size * 2)
        var i = 0
        for (s in samples) {
            out[i] = (s.toInt() and 0xFF).toByte()
            out[i + 1] = ((s.toInt() shr 8) and 0xFF).toByte()
            i += 2
        }
        return out
    }

    private fun removeDcOffset(samples: ShortArray) {
        var prev = 0f
        for (i in samples.indices) {
            val x = samples[i].toFloat()
            val y = x - prev + DC_ALPHA * prev
            samples[i] = y.toInt().coerceIn(-32768, 32767).toShort()
            prev = y
        }
    }

    private fun applyHighPassFilter(samples: ShortArray, sampleRate: Int) {
        val rc = 1.0 / (2.0 * Math.PI * HPF_CUTOFF)
        val dt = 1.0 / sampleRate
        val alpha = (rc / (rc + dt)).toFloat()

        var prevIn = samples[0].toFloat()
        var prevOut = 0f

        for (i in samples.indices) {
            val x = samples[i].toFloat()
            val y = alpha * (prevOut + x - prevIn)
            samples[i] = y.toInt().coerceIn(-32768, 32767).toShort()
            prevIn = x
            prevOut = y
        }
    }

    private fun applyNoiseGate(samples: ShortArray) {
        val windowSize = 160
        var i = 0
        while (i + windowSize <= samples.size) {
            var sum = 0.0
            for (j in i until i + windowSize) {
                val s = samples[j].toDouble()
                sum += s * s
            }
            val rms = sqrt(sum / windowSize)

            if (rms < NOISE_GATE_RMS) {
                for (j in i until i + windowSize) {
                    samples[j] = (samples[j] * 0.05f).toInt().toShort()
                }
            }
            i += windowSize
        }
    }

    private fun applyAgc(samples: ShortArray, sampleRate: Int) {
        val windowSize = sampleRate / 10
        var i = 0
        while (i + windowSize <= samples.size) {
            var sum = 0.0
            for (j in i until i + windowSize) {
                val s = samples[j].toDouble()
                sum += s * s
            }
            val rms = sqrt(sum / windowSize)

            if (rms > 100.0) {
                var gain = (AGC_TARGET_RMS / rms).toFloat()
                gain = gain.coerceIn(AGC_MIN_GAIN, AGC_MAX_GAIN)

                for (j in i until i + windowSize) {
                    val amplified = samples[j] * gain
                    samples[j] = amplified.toInt()
                        .coerceIn(-32768, 32767).toShort()
                }
            }
            i += windowSize
        }
    }

    private fun applyPreEmphasis(samples: ShortArray) {
        if (samples.isEmpty()) return
        var prev = samples[0].toFloat()
        for (i in 1 until samples.size) {
            val x = samples[i].toFloat()
            val y = x - PREEMPHASIS_ALPHA * prev
            samples[i] = y.toInt().coerceIn(-32768, 32767).toShort()
            prev = x
        }
    }
}