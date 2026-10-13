package com.knoc.interview.util

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

val Context.dataStore by preferencesDataStore(name = "knoc_session")

object SessionManager {

    private val TOKEN_KEY = stringPreferencesKey("access_token")
    private val USER_NAME_KEY = stringPreferencesKey("user_name")
    private val USER_EMAIL_KEY = stringPreferencesKey("user_email")

    suspend fun saveToken(context: Context, token: String) {
        context.dataStore.edit { it[TOKEN_KEY] = token }
    }

    suspend fun getToken(context: Context): String? {
        return context.dataStore.data.map { it[TOKEN_KEY] }.first()
    }

    suspend fun saveUser(context: Context, name: String?, email: String?) {
        context.dataStore.edit {
            if (name != null) it[USER_NAME_KEY] = name
            if (email != null) it[USER_EMAIL_KEY] = email
        }
    }

    suspend fun getUserName(context: Context): String? =
        context.dataStore.data.map { it[USER_NAME_KEY] }.first()

    suspend fun getUserEmail(context: Context): String? =
        context.dataStore.data.map { it[USER_EMAIL_KEY] }.first()

    suspend fun clear(context: Context) {
        context.dataStore.edit { it.clear() }
    }
}