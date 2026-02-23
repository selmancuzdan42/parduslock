package com.pardus.lockapp.ui.admin

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pardus.lockapp.data.api.ApiClient
import com.pardus.lockapp.data.model.DashboardResponse
import kotlinx.coroutines.launch

sealed class DashboardState {
    object Idle    : DashboardState()
    object Loading : DashboardState()
    data class Loaded(val data: DashboardResponse) : DashboardState()
    data class Error(val message: String)          : DashboardState()
}

class DashboardViewModel : ViewModel() {

    private val _state = MutableLiveData<DashboardState>(DashboardState.Idle)
    val state: LiveData<DashboardState> = _state

    fun load(serverUrl: String) {
        _state.value = DashboardState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).getDashboard()
                if (resp.isSuccessful && resp.body()?.status == "ok") {
                    _state.value = DashboardState.Loaded(resp.body()!!)
                } else {
                    _state.value = DashboardState.Error("Dashboard yüklenemedi")
                }
            } catch (e: Exception) {
                _state.value = DashboardState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }
}
