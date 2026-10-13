package com.knoc.interview

import android.content.Intent
import android.os.Bundle
import android.util.Patterns
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.knoc.interview.data.AuthApi
import com.knoc.interview.util.SessionManager
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var etEmail: TextInputEditText
    private lateinit var etPassword: TextInputEditText
    private lateinit var btnSignIn: MaterialButton
    private lateinit var progress: ProgressBar
    private lateinit var tvError: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        etEmail = findViewById(R.id.etEmail)
        etPassword = findViewById(R.id.etPassword)
        btnSignIn = findViewById(R.id.btnSignIn)
        progress = findViewById(R.id.progressLogin)
        tvError = findViewById(R.id.tvLoginError)

        btnSignIn.setOnClickListener { attemptLogin() }
    }

    private fun attemptLogin() {
        val email = etEmail.text?.toString()?.trim().orEmpty()
        val password = etPassword.text?.toString().orEmpty()

        tvError.visibility = View.GONE

        if (email.isBlank() || !Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            showError("Enter a valid email")
            return
        }
        if (password.length < 6) {
            showError("Password must be at least 6 characters")
            return
        }

        setLoading(true)

        lifecycleScope.launch {
            try {
                val response = AuthApi.login(email, password)

                SessionManager.saveToken(this@LoginActivity, response.accessToken)
                SessionManager.saveUser(
                    this@LoginActivity,
                    response.user?.name ?: email.substringBefore("@"),
                    response.user?.email ?: email,
                )

                Toast.makeText(
                    this@LoginActivity,
                    "Welcome back!",
                    Toast.LENGTH_SHORT
                ).show()

                startActivity(
                    Intent(this@LoginActivity, HomeActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                )
                finish()
            } catch (e: Exception) {
                showError(e.message ?: "Login failed")
                setLoading(false)
            }
        }
    }

    private fun setLoading(loading: Boolean) {
        btnSignIn.isEnabled = !loading
        btnSignIn.text = if (loading) "" else "Sign in"
        progress.visibility = if (loading) View.VISIBLE else View.GONE
    }

    private fun showError(message: String) {
        tvError.text = message
        tvError.visibility = View.VISIBLE
    }
}