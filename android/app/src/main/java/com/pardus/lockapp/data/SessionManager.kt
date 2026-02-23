package com.pardus.lockapp.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "session")

data class SavedCredentials(
    val username: String,
    val password: String,
    val remember: Boolean
)

class SessionManager(private val context: Context) {

    companion object {
        private val SERVER_URL_KEY = stringPreferencesKey(Constants.DATASTORE_SERVER_URL_KEY)
        private val USERNAME_KEY   = stringPreferencesKey("saved_username")
        private val PASSWORD_KEY   = stringPreferencesKey("saved_password")
        private val REMEMBER_KEY   = booleanPreferencesKey("remember_me")
    }

    val serverUrlFlow: Flow<String> = context.dataStore.data
        .map { prefs -> prefs[SERVER_URL_KEY] ?: Constants.DEFAULT_SERVER_URL }

    val credentialsFlow: Flow<SavedCredentials> = context.dataStore.data
        .map { prefs ->
            SavedCredentials(
                username = prefs[USERNAME_KEY] ?: "",
                password = prefs[PASSWORD_KEY] ?: "",
                remember = prefs[REMEMBER_KEY] ?: false
            )
        }

    suspend fun saveServerUrl(url: String) {
        context.dataStore.edit { prefs ->
            prefs[SERVER_URL_KEY] = url.trimEnd('/')
        }
    }

    suspend fun saveCredentials(username: String, password: String) {
        context.dataStore.edit { prefs ->
            prefs[USERNAME_KEY] = username
            prefs[PASSWORD_KEY] = password
            prefs[REMEMBER_KEY] = true
        }
    }

    suspend fun clearCredentials() {
        context.dataStore.edit { prefs ->
            prefs.remove(USERNAME_KEY)
            prefs.remove(PASSWORD_KEY)
            prefs[REMEMBER_KEY] = false
        }
    }
}
