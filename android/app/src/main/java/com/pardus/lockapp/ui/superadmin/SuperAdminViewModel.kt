package com.pardus.lockapp.ui.superadmin

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pardus.lockapp.data.api.ApiClient
import com.pardus.lockapp.data.model.*
import kotlinx.coroutines.launch

sealed class SaState {
    object Idle    : SaState()
    object Loading : SaState()
    data class LoginSuccess(val username: String) : SaState()
    data class DashboardLoaded(
        val licenses:     List<License>,
        val schoolAdmins: List<SchoolAdmin>,
        val boards:       List<SaBoard>
    ) : SaState()
    data class ActionSuccess(val message: String) : SaState()
    data class Error(val message: String)         : SaState()
}

class SuperAdminViewModel : ViewModel() {

    private val _state = MutableLiveData<SaState>(SaState.Idle)
    val state: LiveData<SaState> = _state

    fun login(serverUrl: String, username: String, password: String) {
        _state.value = SaState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).saLogin(SaLoginRequest(username, password))
                if (resp.isSuccessful && resp.body()?.status == "ok") {
                    _state.value = SaState.LoginSuccess(resp.body()?.username ?: username)
                } else {
                    _state.value = SaState.Error(ApiClient.parseErrorMessage(resp, "Giriş başarısız"))
                }
            } catch (e: Exception) {
                _state.value = SaState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun logout(serverUrl: String, onDone: () -> Unit) {
        viewModelScope.launch {
            try { ApiClient.getService(serverUrl).saLogout() } catch (_: Exception) {}
            onDone()
        }
    }

    fun loadDashboard(serverUrl: String) {
        _state.value = SaState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).getSaDashboard()
                val body = resp.body()
                if (resp.isSuccessful && body?.status == "ok") {
                    _state.value = SaState.DashboardLoaded(body.licenses, body.schoolAdmins, body.boards)
                } else {
                    _state.value = SaState.Error(ApiClient.parseErrorMessage(resp, "Dashboard yüklenemedi"))
                }
            } catch (e: Exception) {
                _state.value = SaState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun addLicense(serverUrl: String, schoolCode: String, schoolName: String, startDate: String, durationMonths: Int) {
        _state.value = SaState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).addLicense(
                    AddLicenseRequest(schoolCode, schoolName, startDate, durationMonths)
                )
                if (resp.isSuccessful && resp.body()?.status == "ok") {
                    _state.value = SaState.ActionSuccess("Lisans eklendi")
                } else {
                    _state.value = SaState.Error(ApiClient.parseErrorMessage(resp, "Lisans eklenemedi"))
                }
            } catch (e: Exception) {
                _state.value = SaState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun toggleLicense(serverUrl: String, licenseId: Int) {
        viewModelScope.launch {
            try {
                ApiClient.getService(serverUrl).toggleLicense(licenseId)
                loadDashboard(serverUrl)
            } catch (e: Exception) {
                _state.value = SaState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun deleteLicense(serverUrl: String, licenseId: Int) {
        _state.value = SaState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).deleteLicense(licenseId)
                if (resp.isSuccessful) {
                    _state.value = SaState.ActionSuccess("Lisans silindi")
                } else {
                    _state.value = SaState.Error(ApiClient.parseErrorMessage(resp, "Silinemedi"))
                }
            } catch (e: Exception) {
                _state.value = SaState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun addSchoolAdmin(serverUrl: String, username: String, password: String, fullName: String, schoolCode: String) {
        _state.value = SaState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).addSchoolAdmin(
                    AddSchoolAdminRequest(username, password, fullName, schoolCode)
                )
                if (resp.isSuccessful && resp.body()?.status == "ok") {
                    _state.value = SaState.ActionSuccess("Okul admini eklendi")
                } else {
                    _state.value = SaState.Error(ApiClient.parseErrorMessage(resp, "Eklenemedi"))
                }
            } catch (e: Exception) {
                _state.value = SaState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun deleteSchoolAdmin(serverUrl: String, userId: Int) {
        _state.value = SaState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).deleteSchoolAdmin(userId)
                if (resp.isSuccessful) {
                    _state.value = SaState.ActionSuccess("Admin silindi")
                } else {
                    _state.value = SaState.Error(ApiClient.parseErrorMessage(resp, "Silinemedi"))
                }
            } catch (e: Exception) {
                _state.value = SaState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun assignBoard(serverUrl: String, boardId: String, schoolCode: String) {
        _state.value = SaState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).assignBoard(AssignBoardRequest(boardId, schoolCode))
                if (resp.isSuccessful && resp.body()?.status == "ok") {
                    _state.value = SaState.ActionSuccess("Tahta atandı")
                } else {
                    _state.value = SaState.Error(ApiClient.parseErrorMessage(resp, "Atama başarısız"))
                }
            } catch (e: Exception) {
                _state.value = SaState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun deleteSaBoard(serverUrl: String, boardId: String) {
        _state.value = SaState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).deleteSaBoard(boardId)
                if (resp.isSuccessful) {
                    _state.value = SaState.ActionSuccess("Tahta silindi")
                } else {
                    _state.value = SaState.Error(ApiClient.parseErrorMessage(resp, "Silinemedi"))
                }
            } catch (e: Exception) {
                _state.value = SaState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun resetState() { _state.value = SaState.Idle }
}
