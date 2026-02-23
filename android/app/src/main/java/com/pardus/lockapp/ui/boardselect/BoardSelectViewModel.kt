package com.pardus.lockapp.ui.boardselect

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pardus.lockapp.data.api.ApiClient
import com.pardus.lockapp.data.model.Board
import kotlinx.coroutines.launch

sealed class BoardSelectState {
    object Loading : BoardSelectState()
    data class Success(val boards: List<Board>) : BoardSelectState()
    data class Error(val message: String) : BoardSelectState()
}

class BoardSelectViewModel : ViewModel() {

    private val _state = MutableLiveData<BoardSelectState>()
    val state: LiveData<BoardSelectState> = _state

    fun loadBoards(serverUrl: String) {
        _state.value = BoardSelectState.Loading
        viewModelScope.launch {
            try {
                val response = ApiClient.getService(serverUrl).getBoards()
                if (response.isSuccessful) {
                    val body = response.body()
                    if (body?.status == "ok") {
                        _state.value = BoardSelectState.Success(body.boards ?: emptyList())
                    } else {
                        _state.value = BoardSelectState.Error("Tahtalar yüklenemedi")
                    }
                } else {
                    _state.value = BoardSelectState.Error(
                        ApiClient.parseErrorMessage(response, "Sunucu hatası")
                    )
                }
            } catch (e: Exception) {
                _state.value = BoardSelectState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }
}
