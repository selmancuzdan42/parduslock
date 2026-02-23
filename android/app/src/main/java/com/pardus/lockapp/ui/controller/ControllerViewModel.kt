package com.pardus.lockapp.ui.controller

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pardus.lockapp.data.api.ApiClient
import com.pardus.lockapp.data.model.SendCommandRequest
import kotlinx.coroutines.launch

sealed class CommandState {
    object Idle    : CommandState()
    object Loading : CommandState()
    data class Success(val message: String) : CommandState()
    data class Error(val message: String)   : CommandState()
}

class ControllerViewModel : ViewModel() {

    private val _commandState = MutableLiveData<CommandState>(CommandState.Idle)
    val commandState: LiveData<CommandState> = _commandState

    fun sendCommand(serverUrl: String, boardId: String, command: String) {
        _commandState.value = CommandState.Loading
        viewModelScope.launch {
            try {
                val response = ApiClient.getService(serverUrl)
                    .sendCommand(SendCommandRequest(boardId, command))
                if (response.isSuccessful && response.body()?.status == "ok") {
                    val label = when (command) {
                        "unlock" -> "Kilit açıldı"
                        "lock"   -> "Kilitlendı"
                        "next"   -> "Sonraki slayta geçildi"
                        "prev"   -> "Önceki slayta geçildi"
                        else     -> "Komut gönderildi"
                    }
                    _commandState.value = CommandState.Success(label)
                } else {
                    _commandState.value = CommandState.Error(
                        ApiClient.parseErrorMessage(response, response.body()?.message ?: "Komut gönderilemedi")
                    )
                }
            } catch (e: Exception) {
                _commandState.value = CommandState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun logout(serverUrl: String, onDone: () -> Unit) {
        viewModelScope.launch {
            try {
                ApiClient.getService(serverUrl).logout()
            } catch (_: Exception) {}
            ApiClient.clearCookies()
            onDone()
        }
    }

    fun resetState() {
        _commandState.value = CommandState.Idle
    }
}
