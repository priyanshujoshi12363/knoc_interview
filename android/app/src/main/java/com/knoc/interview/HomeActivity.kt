package com.knoc.interview

import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.card.MaterialCardView
import com.knoc.interview.util.SessionManager
import kotlinx.coroutines.launch

class HomeActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_home)

        val tvGreeting = findViewById<TextView>(R.id.tvGreeting)
        val cardInterview = findViewById<MaterialCardView>(R.id.cardInterviewMode)
        val cardPractice = findViewById<MaterialCardView>(R.id.cardPracticeMode)

        lifecycleScope.launch {
            val name = SessionManager.getUserName(this@HomeActivity) ?: "there"
            tvGreeting.text = "Hi, $name 👋"
        }

        cardInterview.setOnClickListener {
            startActivity(
                Intent(this, InterviewModeActivity::class.java).apply {
                    putExtra("course", "Backend Engineering")
                    putExtra("target_role", "Backend Engineer")
                    putExtra("difficulty", "intermediate")
                }
            )
        }

        cardPractice.setOnClickListener {
            Toast.makeText(this, "Practice mode coming soon", Toast.LENGTH_SHORT).show()
        }
    }
}