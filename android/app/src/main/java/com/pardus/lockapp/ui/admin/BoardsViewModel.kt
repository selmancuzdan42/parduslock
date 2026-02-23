package com.pardus.lockapp.ui.admin

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.pardus.lockapp.data.api.ApiClient
import com.pardus.lockapp.data.model.Board
import com.pardus.lockapp.data.model.BulkBoardPermissionRequest
import com.pardus.lockapp.data.model.User
import kotlinx.coroutines.async
import kotlinx.coroutines.launch

sealed class BoardsState {
    object Idle    : BoardsState()
    object Loading : BoardsState()
    data class BoardsLoaded(val boards: List<Board>) : BoardsState()
    data class PermissionsReady(
        val boardId: String,
        val assignedIds: Set<Int>,
        val allTeachers: List<User>
    ) : BoardsState()
    data class ActionSuccess(val message: String) : BoardsState()
    data class Error(val message: String)         : BoardsState()
}

class BoardsViewModel : ViewModel() {

    private val _state = MutableLiveData<BoardsState>(BoardsState.Idle)
    val state: LiveData<BoardsState> = _state

    fun loadBoards(serverUrl: String) {
        _state.value = BoardsState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).getBoards()
                if (resp.isSuccessful && resp.body()?.status == "ok") {
                    _state.value = BoardsState.BoardsLoaded(resp.body()?.boards ?: emptyList())
                } else {
                    _state.value = BoardsState.Error(
                        ApiClient.parseErrorMessage(resp, "Tahtalar yüklenemedi")
                    )
                }
            } catch (e: Exception) {
                _state.value = BoardsState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    /** Yetki dialogu için: mevcut izinler + tüm öğretmenler paralel yüklenir. */
    fun loadPermissionsForDialog(serverUrl: String, boardId: String) {
        _state.value = BoardsState.Loading
        viewModelScope.launch {
            try {
                val service        = ApiClient.getService(serverUrl)
                val permsDeferred  = async { service.getBoardPermissions(boardId) }
                val usersDeferred  = async { service.getUsers() }

                val permsResp  = permsDeferred.await()
                val usersResp  = usersDeferred.await()

                val assignedIds = permsResp.body()?.users
                    ?.map { it.id }?.toSet() ?: emptySet()

                val allTeachers = usersResp.body()?.users
                    ?.filter { it.role == "teacher" } ?: emptyList()

                _state.value = BoardsState.PermissionsReady(boardId, assignedIds, allTeachers)
            } catch (e: Exception) {
                _state.value = BoardsState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    /**
     * Checkbox seçimlerine göre izinleri günceller.
     * selectedIds: dialog'da işaretlenen öğretmen ID'leri
     * previousIds: diyalog açılmadan önceki atanmış ID'ler
     * allTeachers: tüm öğretmen listesi
     */
    fun savePermissions(
        serverUrl: String,
        boardId: String,
        allTeachers: List<User>,
        selectedIds: Set<Int>,
        previousIds: Set<Int>
    ) {
        viewModelScope.launch {
            try {
                val service = ApiClient.getService(serverUrl)
                // Bulk endpoint: replace=true → tek istekte tüm izinleri güncelle
                service.bulkBoardPermissions(
                    boardId,
                    BulkBoardPermissionRequest(userIds = selectedIds.toList(), replace = true)
                )
                _state.value = BoardsState.ActionSuccess("Yetkiler güncellendi")
            } catch (e: Exception) {
                _state.value = BoardsState.Error("Yetki kaydedilemedi: ${e.message}")
            }
        }
    }

    fun deleteBoard(serverUrl: String, boardId: String) {
        _state.value = BoardsState.Loading
        viewModelScope.launch {
            try {
                val resp = ApiClient.getService(serverUrl).deleteBoard(boardId)
                if (resp.isSuccessful) {
                    _state.value = BoardsState.ActionSuccess("Tahta silindi")
                } else {
                    _state.value = BoardsState.Error(
                        ApiClient.parseErrorMessage(resp, "Tahta silinemedi")
                    )
                }
            } catch (e: Exception) {
                _state.value = BoardsState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun resetState() {
        _state.value = BoardsState.Idle
    }
}
