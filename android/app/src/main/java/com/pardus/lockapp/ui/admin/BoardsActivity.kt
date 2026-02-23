package com.pardus.lockapp.ui.admin

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.pardus.lockapp.data.model.Board
import com.pardus.lockapp.data.model.User
import com.pardus.lockapp.databinding.ActivityBoardsBinding

class BoardsActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SERVER_URL = "server_url"
    }

    private lateinit var binding: ActivityBoardsBinding
    private val viewModel: BoardsViewModel by viewModels()
    private lateinit var adapter: BoardAdapter
    private lateinit var serverUrl: String

    // Dialog için geçici veri
    private var dialogBoard: Board? = null
    private var dialogPreviousIds: Set<Int> = emptySet()
    private var dialogTeachers: List<User> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding   = ActivityBoardsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        serverUrl = intent.getStringExtra(EXTRA_SERVER_URL) ?: ""

        adapter = BoardAdapter(
            onPermissions = { board ->
                dialogBoard = board
                viewModel.loadPermissionsForDialog(serverUrl, board.boardId)
            },
            onDelete = { board ->
                showDeleteConfirmDialog(board)
            }
        )

        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter        = adapter
        binding.btnBack.setOnClickListener  { finish() }

        viewModel.state.observe(this) { state ->
            when (state) {
                is BoardsState.Idle          -> binding.progressBar.visibility = View.GONE
                is BoardsState.Loading       -> binding.progressBar.visibility = View.VISIBLE
                is BoardsState.BoardsLoaded  -> {
                    binding.progressBar.visibility = View.GONE
                    adapter.submitList(state.boards)
                }
                is BoardsState.PermissionsReady -> {
                    binding.progressBar.visibility = View.GONE
                    dialogPreviousIds = state.assignedIds
                    dialogTeachers    = state.allTeachers
                    showPermissionsDialog(state.boardId, state.assignedIds, state.allTeachers)
                    viewModel.resetState()
                }
                is BoardsState.ActionSuccess -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this, state.message, Toast.LENGTH_SHORT).show()
                    viewModel.loadBoards(serverUrl)
                }
                is BoardsState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this, state.message, Toast.LENGTH_LONG).show()
                    viewModel.resetState()
                }
            }
        }

        viewModel.loadBoards(serverUrl)
    }

    private fun showDeleteConfirmDialog(board: Board) {
        AlertDialog.Builder(this)
            .setTitle("Tahtayı Sil")
            .setMessage("\"${board.boardId}\" tahtasını silmek istediğinize emin misiniz? Bu işlem geri alınamaz.")
            .setPositiveButton("Sil") { _, _ ->
                viewModel.deleteBoard(serverUrl, board.boardId)
            }
            .setNegativeButton("İptal", null)
            .show()
    }

    private fun showPermissionsDialog(
        boardId: String,
        assignedIds: Set<Int>,
        teachers: List<User>
    ) {
        if (teachers.isEmpty()) {
            AlertDialog.Builder(this)
                .setTitle("Tahta: $boardId")
                .setMessage("Sistemde öğretmen hesabı bulunmuyor.")
                .setPositiveButton("Tamam", null)
                .show()
            return
        }

        val names     = teachers.map { it.fullName }.toTypedArray()
        val checked   = teachers.map { it.id in assignedIds }.toBooleanArray()
        val selected  = checked.copyOf()   // kullanıcı değiştirir

        AlertDialog.Builder(this)
            .setTitle("Tahta Yetkileri: $boardId")
            .setMultiChoiceItems(names, checked) { _, which, isChecked ->
                selected[which] = isChecked
            }
            .setPositiveButton("Kaydet") { _, _ ->
                val newIds = teachers
                    .filterIndexed { i, _ -> selected[i] }
                    .map { it.id }.toSet()
                viewModel.savePermissions(serverUrl, boardId, teachers, newIds, assignedIds)
            }
            .setNegativeButton("İptal", null)
            .show()
    }
}
