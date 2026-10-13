package com.knoc.interview.data

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val email: String,
    val password: String
)

data class RegisterRequest(
    val name: String,
    val email: String,
    val password: String
)

data class User(
    val id: String?,
    val name: String?,
    val email: String?,
    @SerializedName("avatar_url") val avatarUrl: String?,
    val bio: String?,
    val education: String?,
    @SerializedName("target_role") val targetRole: String?,
    val skills: List<String>?,
    val preferences: Map<String, Any>?
)

data class LoginResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("refresh_token") val refreshToken: String?,
    @SerializedName("token_type") val tokenType: String?,
    @SerializedName("expires_in") val expiresIn: Int?,
    val user: User?
)

data class RegisterResponse(
    val id: String?,
    val name: String?,
    val email: String?,
    @SerializedName("access_token") val accessToken: String?,
    @SerializedName("refresh_token") val refreshToken: String?
)

data class CreateSessionRequest(
    val topic: String,
    @SerializedName("target_role") val targetRole: String?,
    val difficulty: String,
    @SerializedName("question_count") val questionCount: Int,
    val language: String
)

data class PracticeSessionResponse(
    val id: String,
    @SerializedName("user_id") val userId: String?,
    val topic: String?,
    @SerializedName("target_role") val targetRole: String?,
    val difficulty: String?,
    val status: String?,
    @SerializedName("question_count") val questionCount: Int?,
    @SerializedName("questions_asked") val questionsAsked: Int?,
    val language: String?,
    val score: Double?,
    @SerializedName("final_summary") val finalSummary: String?,
    @SerializedName("created_at") val createdAt: String?,
    @SerializedName("updated_at") val updatedAt: String?,
    @SerializedName("started_at") val startedAt: String?,
    @SerializedName("ended_at") val endedAt: String?
)

data class PracticeQuestion(
    val text: String,
    val number: Int,
    @SerializedName("is_follow_up") val isFollowUp: Boolean?,
    @SerializedName("audio_b64") val audioB64: String?
)

data class StartPracticeResponse(
    @SerializedName("session_id") val sessionId: String,
    val status: String?,
    val message: String?,
    @SerializedName("first_question") val firstQuestion: PracticeQuestion
)

data class PracticeEvaluation(
    val score: Double?,
    val correctness: String?,
    val completeness: String?,
    val reasoning: String?,
    val feedback: String?,
    val strengths: List<String>?,
    val weaknesses: List<String>?
)

data class SubmitAnswerResponse(
    @SerializedName("session_id") val sessionId: String,
    val transcript: String?,
    val evaluation: PracticeEvaluation?,
    @SerializedName("next_question") val nextQuestion: PracticeQuestion?,
    @SerializedName("interview_completed") val interviewCompleted: Boolean?,
    @SerializedName("final_summary") val finalSummary: String?,
    @SerializedName("final_score") val finalScore: Double?,
    val action: String?
)

data class AnalyzeChunkResponse(
    val transcript: String?,
    @SerializedName("should_respond") val shouldRespond: Boolean?,
    val question: String?,
    val answer: String?
)

data class ExplainCodeRequest(
    val code: String,
    val language: String? = null,
    val question: String? = null
)

data class LineExplanation(
    val lines: String?,
    val explanation: String?
)

data class ExplainCodeResponse(
    @SerializedName("num_chunks") val numChunks: Int?,
    @SerializedName("total_lines") val totalLines: Int?,
    val summary: String?,
    val approach: String?,
    @SerializedName("key_concepts") val keyConcepts: List<String>?,
    val complexity: String?,
    @SerializedName("potential_issues") val potentialIssues: List<String>?,
    val improvements: List<String>?,
    @SerializedName("line_by_line") val lineByLine: List<LineExplanation>?,
    val answer: String?,
    @SerializedName("code_references") val codeReferences: List<String>?
)

data class Hint(
    val question: String,
    val answer: String,
    val timestamp: Long = System.currentTimeMillis()
)