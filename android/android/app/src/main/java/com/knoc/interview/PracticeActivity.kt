package com.knoc.interview

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class PracticeActivity : AppCompatActivity() {

    private val TAG = "PracticeActivity"
    private val RECORD_PERM = 101

    private lateinit var tvStatus: TextView
    private lateinit var tvQuestion: TextView
    private lateinit var tvTranscript: TextView
    private lateinit var tvScore: TextView
    private lateinit var tvFeedback: TextView
    private lateinit var btnRecord: Button

    private val recorder = PcmRecorder()
    private var isRecording = false

    private var token: String? = null
    private var sessionId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_practice)

        tvStatus = findViewById(R.id.tvStatus)
        tvQuestion = findViewById(R.id.tvQuestion)
        tvTranscript = findViewById(R.id.tvTranscript)
        tvScore = findViewById(R.id.tvScore)
        tvFeedback = findViewById(R.id.tvFeedback)
        btnRecord = findViewById(R.id.btnRecord)

        btnRecord.isEnabled = false
        btnRecord.setOnClickListener { toggleRecording() }

        ensurePermissionThenBootstrap()
    }

    private fun ensurePermissionThenBootstrap() {
        val granted = ContextCompat.checkSelfPermission(
            this, Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

        if (granted) {
            bootstrapSession()
        } else {
            ActivityCompat.requestPermissions(
                this, arrayOf(Manifest.permission.RECORD_AUDIO), RECORD_PERM
            )
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == RECORD_PERM && grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED
        ) {
            bootstrapSession()
        } else {
            tvStatus.text = "Microphone permission denied."
        }
    }

    private fun bootstrapSession() {
        lifecycleScope.launch {
            try {
                tvStatus.text = "Logging in..."
                val login = ApiClient.login("priyanshu@123gmail.com", "12345678")
                token = login.accessToken
                Log.d(TAG, "Logged in as ${login.user?.email}")

                tvStatus.text = "Creating practice session..."
                val session = ApiClient.createSession(
                    token!!,
                    CreateSessionRequest(
                        topic = "System Design",
                        targetRole = "Backend Engineer",
                        difficulty = "intermediate",
                        questionCount = 3,
                        language = "en"
                    )
                )
                sessionId = session.id
                Log.d(TAG, "Session: ${session.id}")

                tvStatus.text = "Starting session..."
                val start = ApiClient.startSession(token!!, sessionId!!)
                showQuestion(start.firstQuestion)

                btnRecord.isEnabled = true
                btnRecord.text = "Start Recording"
            } catch (e: Exception) {
                Log.e(TAG, "Bootstrap failed", e)
                tvStatus.text = "Error: ${e.message}"
            }
        }
    }

    private fun showQuestion(q: PracticeQuestion) {
        tvQuestion.text = "Q${q.number}: ${q.text}"
        tvTranscript.text = ""
        tvScore.text = ""
        tvFeedback.text = ""

        if (!q.audioB64.isNullOrBlank()) {
            tvStatus.text = "Playing AI question..."
            AudioPlayer.playBase64Wav(this, q.audioB64) {
                runOnUiThread { tvStatus.text = "Your turn — tap Record" }
            }
        } else {
            tvStatus.text = "Your turn — tap Record"
        }
    }

    private fun toggleRecording() {
        if (!isRecording) {
            startRecording()
        } else {
            stopAndSend()
        }
    }

    private fun startRecording() {
        try {
            recorder.start()
            isRecording = true
            btnRecord.text = "Stop & Send"
            tvStatus.text = "Recording... speak your answer"
        } catch (e: Exception) {
            Toast.makeText(this, "Recorder error: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun stopAndSend() {
        val pcm = recorder.stop()
        isRecording = false
        btnRecord.text = "Start Recording"
        btnRecord.isEnabled = false

        if (pcm.isEmpty()) {
            tvStatus.text = "Empty recording."
            btnRecord.isEnabled = true
            return
        }

        lifecycleScope.launch {
            try {
                tvStatus.text = "Uploading (${pcm.size} bytes)..."
                val resp = ApiClient.submitAnswer(token!!, sessionId!!, pcm)

                tvTranscript.text = "You said: ${resp.transcript ?: ""}"
                resp.evaluation?.let { ev ->
                    tvScore.text = "Score: ${ev.score?.toInt() ?: 0}/100"
                    tvFeedback.text = buildString {
                        ev.correctness?.let { append("Correctness: $it\n") }
                        ev.completeness?.let { append("Completeness: $it\n") }
                        ev.feedback?.let { append("Feedback: $it\n") }
                    }
                }

                if (resp.interviewCompleted == true) {
                    tvStatus.text = "Interview completed! Final score: ${resp.finalScore?.toInt()}"
                    tvQuestion.text = "🎉 Done"
                    tvFeedback.append("\n\nFinal summary:\n${resp.finalSummary ?: ""}")
                } else {
                    resp.nextQuestion?.let { showQuestion(it) }
                    btnRecord.isEnabled = true
                }
            } catch (e: Exception) {
                Log.e(TAG, "Submit failed", e)
                tvStatus.text = "Error: ${e.message}"
                btnRecord.isEnabled = true
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isRecording) recorder.stop()
        AudioPlayer.stop()
    }
}
