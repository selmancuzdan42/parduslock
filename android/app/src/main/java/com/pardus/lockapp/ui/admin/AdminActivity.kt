package com.pardus.lockapp.ui.admin

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.*
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.pardus.lockapp.R
import com.pardus.lockapp.data.model.User
import com.pardus.lockapp.databinding.ActivityAdminBinding
import com.pardus.lockapp.databinding.BottomSheetAddUserBinding

class AdminActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SERVER_URL    = "server_url"
        const val EXTRA_CURRENT_USER_ID = "current_user_id"
    }

    private lateinit var binding: ActivityAdminBinding
    private val viewModel: AdminViewModel by viewModels()
    private lateinit var adapter: UserAdapter
    private lateinit var serverUrl: String
    private var currentUserId: Int = -1

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAdminBinding.inflate(layoutInflater)
        setContentView(binding.root)

        serverUrl     = intent.getStringExtra(EXTRA_SERVER_URL)      ?: ""
        currentUserId = intent.getIntExtra(EXTRA_CURRENT_USER_ID, -1)

        adapter = UserAdapter(
            currentUserId = currentUserId,
            onDelete       = { user -> confirmDelete(user) },
            onChangePassword = { user -> showChangePasswordDialog(user) }
        )

        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = adapter

        binding.fabAddUser.setOnClickListener { showAddUserSheet() }
        binding.btnBack.setOnClickListener    { finish() }
        binding.btnBoards.setOnClickListener  {
            startActivity(
                android.content.Intent(this, BoardsActivity::class.java).apply {
                    putExtra(BoardsActivity.EXTRA_SERVER_URL, serverUrl)
                }
            )
        }
        binding.btnDashboard.setOnClickListener {
            startActivity(
                android.content.Intent(this, DashboardActivity::class.java).apply {
                    putExtra(DashboardActivity.EXTRA_SERVER_URL, serverUrl)
                }
            )
        }

        viewModel.state.observe(this) { state ->
            when (state) {
                is AdminState.Idle          -> binding.progressBar.visibility = View.GONE
                is AdminState.Loading       -> binding.progressBar.visibility = View.VISIBLE
                is AdminState.UsersLoaded   -> {
                    binding.progressBar.visibility = View.GONE
                    adapter.submitList(state.users)
                }
                is AdminState.ActionSuccess -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this, state.message, Toast.LENGTH_SHORT).show()
                    viewModel.loadUsers(serverUrl)
                }
                is AdminState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this, state.message, Toast.LENGTH_LONG).show()
                    viewModel.resetState()
                }
            }
        }

        viewModel.loadUsers(serverUrl)
    }

    private fun confirmDelete(user: User) {
        AlertDialog.Builder(this)
            .setTitle("Kullanıcı Sil")
            .setMessage("${user.fullName} adlı kullanıcıyı silmek istediğinize emin misiniz?")
            .setPositiveButton("Sil") { _, _ -> viewModel.deleteUser(serverUrl, user.id) }
            .setNegativeButton("İptal", null)
            .show()
    }

    private fun showChangePasswordDialog(user: User) {
        val view  = LayoutInflater.from(this).inflate(R.layout.dialog_change_password, null)
        val etNew = view.findViewById<EditText>(R.id.etNewPassword)

        AlertDialog.Builder(this)
            .setTitle("Şifre Değiştir — ${user.fullName}")
            .setView(view)
            .setPositiveButton("Kaydet") { _, _ ->
                val newPass = etNew.text.toString()
                if (newPass.length < 6) {
                    Toast.makeText(this, "Şifre en az 6 karakter olmalı", Toast.LENGTH_SHORT).show()
                } else {
                    viewModel.changePassword(serverUrl, user.id, newPass)
                }
            }
            .setNegativeButton("İptal", null)
            .show()
    }

    private fun showAddUserSheet() {
        val dialog  = BottomSheetDialog(this)
        val sheetBinding = BottomSheetAddUserBinding.inflate(layoutInflater)
        dialog.setContentView(sheetBinding.root)

        sheetBinding.btnAdd.setOnClickListener {
            val username  = sheetBinding.etUsername.text.toString().trim()
            val password  = sheetBinding.etPassword.text.toString()
            val fullName  = sheetBinding.etFullName.text.toString().trim()
            val role      = if (sheetBinding.rbAdmin.isChecked) "admin" else "teacher"

            if (username.isEmpty() || password.isEmpty() || fullName.isEmpty()) {
                Toast.makeText(this, "Tüm alanları doldurun", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (password.length < 6) {
                Toast.makeText(this, "Şifre en az 6 karakter olmalı", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            viewModel.addUser(serverUrl, username, password, fullName, role)
            dialog.dismiss()
        }

        sheetBinding.btnCancel.setOnClickListener { dialog.dismiss() }
        dialog.show()
    }
}
