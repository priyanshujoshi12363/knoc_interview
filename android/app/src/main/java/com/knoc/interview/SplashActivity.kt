package com.knoc.interview

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.animation.AccelerateDecelerateInterpolator
import android.widget.ImageView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.knoc.interview.util.SessionManager
import kotlinx.coroutines.launch

class SplashActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_splash)

        val logo = findViewById<ImageView>(R.id.ivLogo)
        val title = findViewById<TextView>(R.id.tvSplashTitle)
        val tagline = findViewById<TextView>(R.id.tvSplashTagline)

        logo.alpha = 0f
        logo.scaleX = 0.6f
        logo.scaleY = 0.6f
        logo.animate()
            .alpha(1f)
            .scaleX(1f)
            .scaleY(1f)
            .setDuration(700)
            .setInterpolator(AccelerateDecelerateInterpolator())
            .start()

        title.alpha = 0f
        title.animate().alpha(1f).setStartDelay(400).setDuration(500).start()

        tagline.alpha = 0f
        tagline.animate().alpha(1f).setStartDelay(700).setDuration(500).start()

        Handler(Looper.getMainLooper()).postDelayed({
            lifecycleScope.launch {
                val token = SessionManager.getToken(this@SplashActivity)
                val target = if (token.isNullOrBlank()) {
                    LoginActivity::class.java
                } else {
                    HomeActivity::class.java
                }
                startActivity(Intent(this@SplashActivity, target))
                finish()
            }
        }, 1600)
    }
}