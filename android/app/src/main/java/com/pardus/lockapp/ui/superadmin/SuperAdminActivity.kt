package com.pardus.lockapp.ui.superadmin

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.pardus.lockapp.R
import com.pardus.lockapp.data.Constants
import com.pardus.lockapp.data.model.License
import com.pardus.lockapp.data.model.SaBoard
import com.pardus.lockapp.data.model.SchoolAdmin
import com.pardus.lockapp.databinding.ActivitySuperAdminBinding
import com.pardus.lockapp.ui.login.LoginActivity
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SuperAdminActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SA_USERNAME = "sa_username"
        private const val TAB_LICENSES = 0
        private const val TAB_ADMINS   = 1
        private const val TAB_BOARDS   = 2
    }

    private lateinit var binding: ActivitySuperAdminBinding
    private val viewModel: SuperAdminViewModel by viewModels()

    private val licenseAdapter  = LicenseAdapter(::onToggleLicense, ::onDeleteLicense)
    private val adminAdapter    = SchoolAdminAdapter(::onDeleteSchoolAdmin)
    private val boardAdapter    = SaBoardAdapter(::onAssignBoard, ::onDeleteSaBoard)

    private var currentTab = TAB_LICENSES

    private var cachedLicenses:     List<License>     = emptyList()
    private var cachedSchoolAdmins: List<SchoolAdmin> = emptyList()
    private var cachedBoards:       List<SaBoard>     = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySuperAdminBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val saUsername = intent.getStringExtra(EXTRA_SA_USERNAME) ?: "Süperadmin"
        binding.tvSaUsername.text = "🔑 $saUsername"

        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        switchTab(TAB_LICENSES)

        binding.btnTabLicenses.setOnClickListener { switchTab(TAB_LICENSES) }
        binding.btnTabAdmins.setOnClickListener   { switchTab(TAB_ADMINS)   }
        binding.btnTabBoards.setOnClickListener   { switchTab(TAB_BOARDS)   }

        binding.fab.setOnClickListener {
            when (currentTab) {
                TAB_LICENSES -> showAddLicenseDialog()
                TAB_ADMINS   -> showAddSchoolAdminDialog()
                TAB_BOARDS   -> { /* Tahta ekleme superadmin'in işi değil */ }
            }
        }

        binding.btnSaLogout.setOnClickListener {
            viewModel.logout(Constants.DEFAULT_SERVER_URL) {
                startActivity(Intent(this, LoginActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                })
            }
        }

        viewModel.state.observe(this) { state ->
            when (state) {
                is SaState.Idle    -> binding.progressBar.visibility = View.GONE
                is SaState.Loading -> binding.progressBar.visibility = View.VISIBLE
                is SaState.DashboardLoaded -> {
                    binding.progressBar.visibility = View.GONE
                    cachedLicenses     = state.licenses
                    cachedSchoolAdmins = state.schoolAdmins
                    cachedBoards       = state.boards
                    refreshCurrentTab()
                }
                is SaState.ActionSuccess -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this, state.message, Toast.LENGTH_SHORT).show()
                    viewModel.loadDashboard(Constants.DEFAULT_SERVER_URL)
                }
                is SaState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this, state.message, Toast.LENGTH_LONG).show()
                    viewModel.resetState()
                }
                else -> {}
            }
        }

        viewModel.loadDashboard(Constants.DEFAULT_SERVER_URL)
    }

    private fun switchTab(tab: Int) {
        currentTab = tab
        when (tab) {
            TAB_LICENSES -> binding.recyclerView.adapter = licenseAdapter
            TAB_ADMINS   -> binding.recyclerView.adapter = adminAdapter
            TAB_BOARDS   -> binding.recyclerView.adapter = boardAdapter
        }
        // FAB sadece lisans ve admin tabında göster
        binding.fab.visibility = if (tab == TAB_BOARDS) View.GONE else View.VISIBLE
        refreshCurrentTab()
    }

    private fun refreshCurrentTab() {
        when (currentTab) {
            TAB_LICENSES -> licenseAdapter.submitList(cachedLicenses.toList())
            TAB_ADMINS   -> adminAdapter.submitList(cachedSchoolAdmins.toList())
            TAB_BOARDS   -> boardAdapter.submitList(cachedBoards.toList())
        }
    }

    // --- Lisans işlemleri ---

    private fun onToggleLicense(lic: License) {
        val action = if (lic.isActive) "pasif" else "aktif"
        AlertDialog.Builder(this)
            .setTitle("Lisansı ${action.replaceFirstChar { it.uppercase() }} Yap")
            .setMessage("${lic.schoolName} lisansı $action yapılsın mı?")
            .setPositiveButton("Evet") { _, _ ->
                viewModel.toggleLicense(Constants.DEFAULT_SERVER_URL, lic.id)
            }
            .setNegativeButton("İptal", null)
            .show()
    }

    private fun onDeleteLicense(lic: License) {
        AlertDialog.Builder(this)
            .setTitle("Lisansı Sil")
            .setMessage("${lic.schoolName} lisansını kalıcı olarak silmek istediğinize emin misiniz?")
            .setPositiveButton("Sil") { _, _ ->
                viewModel.deleteLicense(Constants.DEFAULT_SERVER_URL, lic.id)
            }
            .setNegativeButton("İptal", null)
            .show()
    }

    private fun showAddLicenseDialog() {
        val view = LayoutInflater.from(this).inflate(R.layout.dialog_add_license, null)
        val etSchoolCode     = view.findViewById<EditText>(R.id.etSchoolCode)
        val etSchoolName     = view.findViewById<EditText>(R.id.etSchoolName)
        val etStartDate      = view.findViewById<EditText>(R.id.etStartDate)
        val etDuration       = view.findViewById<EditText>(R.id.etDuration)

        // Bugünün tarihini varsayılan olarak koy
        val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
        etStartDate.setText(today)
        etDuration.setText("2")

        AlertDialog.Builder(this)
            .setTitle("Yeni Lisans Ekle")
            .setView(view)
            .setPositiveButton("Ekle") { _, _ ->
                val code     = etSchoolCode.text.toString().trim()
                val name     = etSchoolName.text.toString().trim()
                val date     = etStartDate.text.toString().trim()
                val duration = etDuration.text.toString().toIntOrNull() ?: 2
                if (code.isEmpty() || name.isEmpty() || date.isEmpty()) {
                    Toast.makeText(this, "Tüm alanları doldurun", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                viewModel.addLicense(Constants.DEFAULT_SERVER_URL, code, name, date, duration)
            }
            .setNegativeButton("İptal", null)
            .show()
    }

    // --- Okul Admin işlemleri ---

    private fun onDeleteSchoolAdmin(admin: SchoolAdmin) {
        AlertDialog.Builder(this)
            .setTitle("Admin Sil")
            .setMessage("${admin.fullName} adlı admini silmek istediğinize emin misiniz?")
            .setPositiveButton("Sil") { _, _ ->
                viewModel.deleteSchoolAdmin(Constants.DEFAULT_SERVER_URL, admin.id)
            }
            .setNegativeButton("İptal", null)
            .show()
    }

    private fun showAddSchoolAdminDialog() {
        val view = LayoutInflater.from(this).inflate(R.layout.dialog_add_school_admin, null)
        val etUsername   = view.findViewById<EditText>(R.id.etUsername)
        val etPassword   = view.findViewById<EditText>(R.id.etPassword)
        val etFullName   = view.findViewById<EditText>(R.id.etFullName)
        val etSchoolCode = view.findViewById<EditText>(R.id.etSchoolCode)

        AlertDialog.Builder(this)
            .setTitle("Yeni Okul Admini Ekle")
            .setView(view)
            .setPositiveButton("Ekle") { _, _ ->
                val username   = etUsername.text.toString().trim()
                val password   = etPassword.text.toString()
                val fullName   = etFullName.text.toString().trim()
                val schoolCode = etSchoolCode.text.toString().trim()
                if (username.isEmpty() || password.isEmpty() || fullName.isEmpty() || schoolCode.isEmpty()) {
                    Toast.makeText(this, "Tüm alanları doldurun", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                if (password.length < 6) {
                    Toast.makeText(this, "Şifre en az 6 karakter olmalı", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                viewModel.addSchoolAdmin(Constants.DEFAULT_SERVER_URL, username, password, fullName, schoolCode)
            }
            .setNegativeButton("İptal", null)
            .show()
    }

    // --- Tahta işlemleri ---

    private fun onAssignBoard(board: SaBoard) {
        val etSchoolCode = EditText(this).apply {
            hint = "Okul Kodu (ör: 550292)"
            setText(board.schoolCode)
        }
        AlertDialog.Builder(this)
            .setTitle("Tahtayı Okula Ata: ${board.boardId}")
            .setView(etSchoolCode)
            .setPositiveButton("Ata") { _, _ ->
                val code = etSchoolCode.text.toString().trim()
                if (code.isEmpty()) {
                    Toast.makeText(this, "Okul kodu girin", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                viewModel.assignBoard(Constants.DEFAULT_SERVER_URL, board.boardId, code)
            }
            .setNegativeButton("İptal", null)
            .show()
    }

    private fun onDeleteSaBoard(board: SaBoard) {
        AlertDialog.Builder(this)
            .setTitle("Tahtayı Sil")
            .setMessage("\"${board.boardId}\" tahtasını kalıcı olarak silmek istediğinize emin misiniz?")
            .setPositiveButton("Sil") { _, _ ->
                viewModel.deleteSaBoard(Constants.DEFAULT_SERVER_URL, board.boardId)
            }
            .setNegativeButton("İptal", null)
            .show()
    }
}
