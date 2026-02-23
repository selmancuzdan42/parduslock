package com.pardus.lockapp.ui.login

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pardus.lockapp.data.api.ApiClient
import com.pardus.lockapp.data.model.LoginRequest
import com.pardus.lockapp.data.model.User
import kotlinx.coroutines.launch
import org.json.JSONObject

sealed class LoginState {
    object Idle : LoginState()
    object Loading : LoginState()
    data class Success(val user: User) : LoginState()
    data class Error(val message: String) : LoginState()
}

class LoginViewModel : ViewModel() {

    private val _state = MutableLiveData<LoginState>(LoginState.Idle)
    val state: LiveData<LoginState> = _state

    /** Giriş başarılıysa QR tarama dönüşünde kullanmak için saklanır. */
    var loggedInUser: User? = null
        private set

    fun login(serverUrl: String, username: String, password: String) {
        _state.value = LoginState.Loading
        viewModelScope.launch {
            try {
                val response = ApiClient.getService(serverUrl)
                    .login(LoginRequest(username, password))
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body?.status == "ok" && body.user != null) {
                        loggedInUser = body.user
                        _state.value = LoginState.Success(body.user)
                    } else {
                        _state.value = LoginState.Error(
                            body?.message ?: "Giriş başarısız"
                        )
                    }
                } else {
                    // Sunucudan gelen hata mesajını göster (askıya alındı vb.)
                    val errorMsg = try {
                        val errBody = response.errorBody()?.string()
                        if (!errBody.isNullOrEmpty()) {
                            JSONObject(errBody).optString("message", "")
                        } else ""
                    } catch (e: Exception) { "" }
                    _state.value = LoginState.Error(
                        errorMsg.ifEmpty { "Kullanıcı adı veya şifre hatalı" }
                    )
                }
            } catch (e: Exception) {
                _state.value = LoginState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }
}
