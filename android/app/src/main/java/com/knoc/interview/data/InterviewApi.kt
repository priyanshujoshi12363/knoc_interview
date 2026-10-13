package com.knoc.interview.data

import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

object InterviewApi {

    private const val BASE_URL = "https://knoc-interview.onrender.com"

    private val client = OkHttpClient.Builder()
        .connectTimeout(90, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val octet = "application/octet-stream".toMediaType()

    suspend fun analyzeChunk(
        token: String,
        pcmBytes: ByteArray,
        language: String = "en",
        course: String = "General",
        targetRole: String? = null,
        difficulty: String = "intermediate",
        topics: String? = null,
        recentContext: String? = "[]"
    ): AnalyzeChunkResponse = withContext(Dispatchers.IO) {
        val fileBody = pcmBytes.toRequestBody(octet)

        val builder = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("audio", "chunk.pcm", fileBody)
            .addFormDataPart("language", language)
            .addFormDataPart("course", course)
            .addFormDataPart("difficulty", difficulty)

        if (!targetRole.isNullOrBlank()) {
            builder.addFormDataPart("target_role", targetRole)
        }
        if (!topics.isNullOrBlank()) {
            builder.addFormDataPart("topics", topics)
        }
        if (!recentContext.isNullOrBlank()) {
            builder.addFormDataPart("recent_context", recentContext)
        }

        val request = Request.Builder()
            .url("$BASE_URL/api/v1/interview/analyze")
            .addHeader("Authorization", "Bearer $token")
            .post(builder.build())
            .build()

        client.newCall(request).execute().use { response ->
            val text = response.body?.string() ?: ""
            if (!response.isSuccessful) {
                throw RuntimeException("Analyze failed (${response.code}): $text")
            }
            gson.fromJson(text, AnalyzeChunkResponse::class.java)
        }
    }
}