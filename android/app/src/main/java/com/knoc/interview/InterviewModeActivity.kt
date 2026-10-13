package com.knoc.interview

import android.Manifest
import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.view.View
import android.view.animation.AccelerateDecelerateInterpolator
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import com.google.gson.Gson
import com.knoc.interview.audio.StreamRecorder
import com.knoc.interview.data.AnalyzeChunkResponse
import com.knoc.interview.data.InterviewApi
import com.knoc.interview.util.SessionManager
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class InterviewModeActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "InterviewMode"
        private const val RECORD_PERM = 201
    }

    private lateinit var viewDot: View
    private lateinit var tvStatus: TextView
    private lateinit var tvCourse: TextView
    private lateinit var tvTranscript: TextView
    private lateinit var tvQuestion: TextView
    private lateinit var tvAnswer: TextView
    private lateinit var cardHint: MaterialCardView
    private lateinit var btnCopy: ImageButton
    private lateinit var btnStop: MaterialButton
    private lateinit var llEmpty: View

    private lateinit var recorder: StreamRecorder
    private var isListening = false
    private var processJob: Job? = null

    private var token: String? = null
    private var course: String = "Backend Engineering"
    private var targetRole: String? = "Backend Engineer"
    private var difficulty: String = "intermediate"

    private val recentContext = mutableListOf<Map<String, String>>()
    private val gson = Gson()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_interview_mode)

        bindViews()
        readIntent()
        setupListeners()
        animateDot()
        ensurePermissionThenStart()
    }

    private fun bindViews() {
        viewDot = findViewById(R.id.viewListeningDot)
        tvStatus = findViewById(R.id.tvListeningStatus)
        tvCourse = findViewById(R.id.tvCourse)
        tvTranscript = findViewById(R.id.tvTranscript)
        tvQuestion = findViewById(R.id.tvQuestion)
        tvAnswer = findViewById(R.id.tvAnswer)
        cardHint = findViewById(R.id.cardHint)
        btnCopy = findViewById(R.id.btnCopyAnswer)
        btnStop = findViewById(R.id.btnStop)
        llEmpty = findViewById(R.id.llEmpty)
    }

    private fun readIntent() {
        course = intent.getStringExtra("course") ?: "Backend Engineering"
        targetRole = intent.getStringExtra("target_role") ?: "Backend Engineer"
        difficulty = intent.getStringExtra("difficulty") ?: "intermediate"
        tvCourse.text = course
    }

    private fun setupListeners() {
        btnStop.setOnClickListener { stopListeningAndFinish() }
        btnCopy.setOnClickListener { copyAnswer() }
    }

    private fun animateDot() {
        val pulse = ObjectAnimator.ofFloat(viewDot, "alpha", 1f, 0.3f).apply {
            duration = 900
            repeatCount = ValueAnimator.INFINITE
            repeatMode = ValueAnimator.REVERSE
            interpolator = AccelerateDecelerateInterpolator()
        }
        pulse.start()
    }

    private fun ensurePermissionThenStart() {
        val granted = ContextCompat.checkSelfPermission(
            this, Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

        if (granted) startListening()
        else ActivityCompat.requestPermissions(
            this, arrayOf(Manifest.permission.RECORD_AUDIO), RECORD_PERM
        )
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == RECORD_PERM && grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED
        ) startListening()
        else {
            Toast.makeText(this, "Mic permission required", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    private fun startListening() {
        lifecycleScope.launch {
            token = SessionManager.getToken(this@InterviewModeActivity)
            if (token.isNullOrBlank()) {
                Toast.makeText(
                    this@InterviewModeActivity,
                    "Please sign in first",
                    Toast.LENGTH_LONG
                ).show()
                finish()
                return@launch
            }

            recorder = StreamRecorder(sampleRate = 16000, chunkSeconds = 4)

            processJob = lifecycleScope.launch {
                recorder.chunks.collectLatest { chunk -> analyzeChunk(chunk) }
            }

            try {
                recorder.start()
                isListening = true
                llEmpty.visibility = View.VISIBLE
                cardHint.visibility = View.GONE
                tvStatus.text = "Listening..."
            } catch (e: Exception) {
                Log.e(TAG, "Recorder failed", e)
                Toast.makeText(
                    this@InterviewModeActivity,
                    "Recorder error: ${e.message}",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }

    private fun analyzeChunk(pcm: ByteArray) {
        val t = token ?: return

        lifecycleScope.launch {
            try {
                tvStatus.text = "Analyzing..."
                val result: AnalyzeChunkResponse = InterviewApi.analyzeChunk(
                    token = t,
                    pcmBytes = pcm,
                    language = "en",
                    course = course,
                    targetRole = targetRole,
                    difficulty = difficulty,
                    recentContext = gson.toJson(recentContext)
                )

                tvStatus.text = "Listening..."

                if (!result.transcript.isNullOrBlank()) {
                    tvTranscript.text = "Heard: \"${result.transcript}\""
                }

                if (result.shouldRespond == true &&
                    !result.question.isNullOrBlank() &&
                    !result.answer.isNullOrBlank()
                ) {
                    showHint(result)

                    recentContext.add(mapOf("role" to "interviewer", "content" to result.question))
                    recentContext.add(mapOf("role" to "candidate", "content" to result.answer))
                    while (recentContext.size > 10) recentContext.removeAt(0)
                }
            } catch (e: Exception) {
                Log.e(TAG, "analyze failed", e)
                tvStatus.text = "Error — retrying..."
                delay(1000)
                tvStatus.text = "Listening..."
            }
        }
    }

    private fun showHint(result: AnalyzeChunkResponse) {
        runOnUiThread {
            llEmpty.visibility = View.GONE
            cardHint.visibility = View.VISIBLE

            tvQuestion.text = result.question.orEmpty()
            tvAnswer.text = result.answer.orEmpty()

            cardHint.alpha = 0f
            cardHint.translationY = 60f
            cardHint.animate()
                .alpha(1f)
                .translationY(0f)
                .setDuration(450)
                .setInterpolator(AccelerateDecelerateInterpolator())
                .start()
        }
    }

    private fun copyAnswer() {
        val text = tvAnswer.text?.toString() ?: return
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("AI Answer", text))
        Toast.makeText(this, "Copied", Toast.LENGTH_SHORT).show()
    }

    private fun stopListeningAndFinish() {
        if (isListening) {
            try { recorder.stop() } catch (_: Exception) {}
        }
        processJob?.cancel()
        isListening = false
        finish()
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isListening) {
            try { recorder.stop() } catch (_: Exception) {}
        }
        processJob?.cancel()
    }
}