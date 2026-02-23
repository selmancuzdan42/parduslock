package com.pardus.lockapp.ui.login

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.pardus.lockapp.data.Constants
import com.pardus.lockapp.data.SessionManager
import com.pardus.lockapp.databinding.ActivityLoginBinding
import com.pardus.lockapp.ui.scan.QRScanActivity
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLoginBinding
    private lateinit var sessionManager: SessionManager
    private val viewModel: LoginViewModel by viewModels()

    private val qrScanLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val boardId     = result.data?.getStringExtra(QRScanActivity.RESULT_BOARD_ID) ?: ""
            val pendingUser = viewModel.loggedInUser
            if (pendingUser != null && boardId.isNotEmpty()) {
                startController(boardId, pendingUser.fullName, pendingUser.role, pendingUser.id)
            } else {
                Toast.makeText(this, "QR okunamadı veya geçersiz tahta ID", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        sessionManager = SessionManager(this)

        // Kayıtlı bilgileri alanları doldur (otomatik giriş yapmaz)
        lifecycleScope.launch {
            val creds = sessionManager.credentialsFlow.first()
            if (creds.remember && creds.username.isNotEmpty()) {
                binding.etUsername.setText(creds.username)
                binding.etPassword.setText(creds.password)
                binding.cbRememberMe.isChecked = true
            }
        }

        binding.btnLogin.setOnClickListener {
            val user = binding.etUsername.text.toString().trim()
            val pass = binding.etPassword.text.toString()

            if (user.isEmpty()) { binding.tilUsername.error = "Boş olamaz"; return@setOnClickListener }
            if (pass.isEmpty()) { binding.tilPassword.error = "Boş olamaz"; return@setOnClickListener }

            binding.tilUsername.error = null
            binding.tilPassword.error = null

            viewModel.login(Constants.DEFAULT_SERVER_URL, user, pass)
        }

        viewModel.state.observe(this) { state ->
            when (state) {
                is LoginState.Idle    -> setLoading(false)
                is LoginState.Loading -> setLoading(true)
                is LoginState.Success -> {
                    setLoading(false)
                    lifecycleScope.launch {
                        if (binding.cbRememberMe.isChecked) {
                            sessionManager.saveCredentials(
                                binding.etUsername.text.toString().trim(),
                                binding.etPassword.text.toString()
                            )
                        } else {
                            sessionManager.clearCredentials()
                        }
                    }
                    // Herkes QR taramaya gider
                    qrScanLauncher.launch(Intent(this, QRScanActivity::class.java))
                }
                is LoginState.Error -> {
                    setLoading(false)
                    Toast.makeText(this, state.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun setLoading(loading: Boolean) {
        binding.btnLogin.isEnabled = !loading
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }

    private fun startController(boardId: String, fullName: String, role: String, userId: Int = -1) {
        val intent = Intent(this, com.pardus.lockapp.ui.controller.ControllerActivity::class.java).apply {
            putExtra(com.pardus.lockapp.ui.controller.ControllerActivity.EXTRA_SERVER_URL, Constants.DEFAULT_SERVER_URL)
            putExtra(com.pardus.lockapp.ui.controller.ControllerActivity.EXTRA_BOARD_ID,   boardId)
            putExtra(com.pardus.lockapp.ui.controller.ControllerActivity.EXTRA_FULL_NAME,  fullName)
            putExtra(com.pardus.lockapp.ui.controller.ControllerActivity.EXTRA_ROLE,       role)
            putExtra(com.pardus.lockapp.ui.admin.AdminActivity.EXTRA_CURRENT_USER_ID,      userId)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        startActivity(intent)
    }
}
