package com.knoc.interview

import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

object ApiClient {

    private val client = OkHttpClient.Builder()
        .connectTimeout(NetworkConfig.CONNECT_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .readTimeout(NetworkConfig.READ_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .writeTimeout(NetworkConfig.WRITE_TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val jsonMedia = "application/json; charset=utf-8".toMediaType()
    private val octetMedia = "application/octet-stream".toMediaType()

    suspend fun login(email: String, password: String): LoginResponse = withContext(Dispatchers.IO) {
        val body = gson.toJson(LoginRequest(email, password)).toRequestBody(jsonMedia)
        val request = Request.Builder()
            .url("${NetworkConfig.BASE_URL}/api/v1/auth/login")
            .post(body)
            .build()
        client.newCall(request).execute().use { response ->
            val text = response.body?.string() ?: ""
            if (!response.isSuccessful) {
                throw RuntimeException("Login failed (${response.code}): $text")
            }
            gson.fromJson(text, LoginResponse::class.java)
        }
    }

    suspend fun createSession(token: String, req: CreateSessionRequest): PracticeSessionResponse = withContext(Dispatchers.IO) {
        val body = gson.toJson(req).toRequestBody(jsonMedia)
        val request = Request.Builder()
            .url("${NetworkConfig.BASE_URL}/api/v1/practice/sessions")
            .addHeader("Authorization", "Bearer $token")
            .post(body)
            .build()
        client.newCall(request).execute().use { response ->
            val text = response.body?.string() ?: ""
            if (!response.isSuccessful) {
                throw RuntimeException("Create session failed (${response.code}): $text")
            }
            gson.fromJson(text, PracticeSessionResponse::class.java)
        }
    }

    suspend fun startSession(token: String, sessionId: String): StartPracticeResponse = withContext(Dispatchers.IO) {
        val empty = "".toRequestBody(jsonMedia)
        val request = Request.Builder()
            .url("${NetworkConfig.BASE_URL}/api/v1/practice/sessions/$sessionId/start")
            .addHeader("Authorization", "Bearer $token")
            .post(empty)
            .build()
        client.newCall(request).execute().use { response ->
            val text = response.body?.string() ?: ""
            if (!response.isSuccessful) {
                throw RuntimeException("Start failed (${response.code}): $text")
            }
            gson.fromJson(text, StartPracticeResponse::class.java)
        }
    }

    suspend fun submitAnswer(token: String, sessionId: String, pcmBytes: ByteArray): SubmitAnswerResponse = withContext(Dispatchers.IO) {
        val fileBody = pcmBytes.toRequestBody(octetMedia)
        val multipart = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("audio", "chunk.pcm", fileBody)
            .build()
        val request = Request.Builder()
            .url("${NetworkConfig.BASE_URL}/api/v1/practice/sessions/$sessionId/answer")
            .addHeader("Authorization", "Bearer $token")
            .post(multipart)
            .build()
        client.newCall(request).execute().use { response ->
            val text = response.body?.string() ?: ""
            if (!response.isSuccessful) {
                throw RuntimeException("Answer failed (${response.code}): $text")
            }
            gson.fromJson(text, SubmitAnswerResponse::class.java)
        }
    }
}
