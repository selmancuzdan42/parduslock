package com.pardus.lockapp.ui.admin

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pardus.lockapp.data.api.ApiClient
import com.pardus.lockapp.data.model.AddUserRequest
import com.pardus.lockapp.data.model.ChangePasswordRequest
import com.pardus.lockapp.data.model.User
import kotlinx.coroutines.launch

sealed class AdminState {
    object Idle : AdminState()
    object Loading : AdminState()
    data class UsersLoaded(val users: List<User>) : AdminState()
    data class ActionSuccess(val message: String) : AdminState()
    data class Error(val message: String) : AdminState()
}

class AdminViewModel : ViewModel() {

    private val _state = MutableLiveData<AdminState>(AdminState.Idle)
    val state: LiveData<AdminState> = _state

    fun loadUsers(serverUrl: String) {
        _state.value = AdminState.Loading
        viewModelScope.launch {
            try {
                val response = ApiClient.getService(serverUrl).getUsers()
                if (response.isSuccessful && response.body() != null) {
                    _state.value = AdminState.UsersLoaded(response.body()!!.users)
                } else {
                    _state.value = AdminState.Error(
                        ApiClient.parseErrorMessage(response, "Kullanıcılar yüklenemedi")
                    )
                }
            } catch (e: Exception) {
                _state.value = AdminState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun addUser(serverUrl: String, username: String, password: String, fullName: String, role: String) {
        _state.value = AdminState.Loading
        viewModelScope.launch {
            try {
                val response = ApiClient.getService(serverUrl)
                    .addUser(AddUserRequest(username, password, fullName, role))
                if (response.isSuccessful && response.body()?.status == "ok") {
                    _state.value = AdminState.ActionSuccess("Kullanıcı eklendi")
                } else {
                    _state.value = AdminState.Error(
                        ApiClient.parseErrorMessage(response, "Kullanıcı eklenemedi")
                    )
                }
            } catch (e: Exception) {
                _state.value = AdminState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun deleteUser(serverUrl: String, userId: Int) {
        _state.value = AdminState.Loading
        viewModelScope.launch {
            try {
                val response = ApiClient.getService(serverUrl).deleteUser(userId)
                if (response.isSuccessful && response.body()?.status == "ok") {
                    _state.value = AdminState.ActionSuccess("Kullanıcı silindi")
                } else {
                    _state.value = AdminState.Error(
                        ApiClient.parseErrorMessage(response, "Kullanıcı silinemedi")
                    )
                }
            } catch (e: Exception) {
                _state.value = AdminState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun changePassword(serverUrl: String, userId: Int, newPassword: String) {
        _state.value = AdminState.Loading
        viewModelScope.launch {
            try {
                val response = ApiClient.getService(serverUrl)
                    .changePassword(ChangePasswordRequest(userId, newPassword))
                if (response.isSuccessful && response.body()?.status == "ok") {
                    _state.value = AdminState.ActionSuccess("Şifre değiştirildi")
                } else {
                    _state.value = AdminState.Error(
                        ApiClient.parseErrorMessage(response, "Şifre değiştirilemedi")
                    )
                }
            } catch (e: Exception) {
                _state.value = AdminState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun resetState() {
        _state.value = AdminState.Idle
    }
}
