package com.knoc.interview.data

import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

object AuthApi {

    private const val BASE_URL = "https://knoc-interview.onrender.com"

    private val client = OkHttpClient.Builder()
        .connectTimeout(90, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .writeTimeout(90, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    suspend fun login(email: String, password: String): LoginResponse =
        withContext(Dispatchers.IO) {
            val body = gson.toJson(LoginRequest(email, password))
                .toRequestBody(jsonMedia)

            val request = Request.Builder()
                .url("$BASE_URL/api/v1/auth/login")
                .post(body)
                .build()

            client.newCall(request).execute().use { response ->
                val text = response.body?.string() ?: ""
                if (!response.isSuccessful) {
                    throw RuntimeException(parseError(response.code, text))
                }
                gson.fromJson(text, LoginResponse::class.java)
            }
        }

    private fun parseError(code: Int, body: String): String {
        return try {
            val json = gson.fromJson(body, Map::class.java)
            val detail = json["detail"]
            when (detail) {
                is String -> "Login failed: $detail"
                is List<*> -> "Login failed: ${detail.firstOrNull()}"
                else -> "Login failed ($code)"
            }
        } catch (_: Exception) {
            "Login failed ($code)"
        }
    }
}