package com.pardus.lockapp.ui.controller

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import com.pardus.lockapp.R
import com.pardus.lockapp.databinding.ActivityControllerBinding
import com.pardus.lockapp.ui.admin.AdminActivity
import com.pardus.lockapp.ui.login.LoginActivity

class ControllerActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SERVER_URL = "server_url"
        const val EXTRA_BOARD_ID   = "board_id"
        const val EXTRA_FULL_NAME  = "full_name"
        const val EXTRA_ROLE       = "role"
    }

    private lateinit var binding: ActivityControllerBinding
    private val viewModel: ControllerViewModel by viewModels()
    private val statusHideHandler = Handler(Looper.getMainLooper())

    private lateinit var serverUrl: String
    private lateinit var boardId:   String
    private lateinit var role:      String

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityControllerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        serverUrl = intent.getStringExtra(EXTRA_SERVER_URL) ?: ""
        boardId   = intent.getStringExtra(EXTRA_BOARD_ID)   ?: ""
        val fullName  = intent.getStringExtra(EXTRA_FULL_NAME) ?: ""
        role          = intent.getStringExtra(EXTRA_ROLE)        ?: "teacher"
        val currentUserId = intent.getIntExtra(AdminActivity.EXTRA_CURRENT_USER_ID, -1)

        binding.tvFullName.text  = fullName
        binding.tvRoleBadge.text = when (role) {
            "superadmin" -> "SÜPER ADMİN"
            "admin"      -> "YÖNETİCİ"
            else         -> "ÖĞRETMEN"
        }

        if (boardId.isNotEmpty()) {
            binding.tvToken.text    = boardId
            binding.tvBoardDot.setTextColor(Color.parseColor("#4CAF50"))
        } else {
            binding.tvToken.text    = "Tahta seçilmedi — QR tarayın"
            binding.tvBoardDot.setTextColor(Color.parseColor("#F44336"))
        }

        binding.btnAdminPanel.visibility =
            if (role == "admin" || role == "superadmin") View.VISIBLE else View.GONE

        binding.btnUnlock.setOnClickListener { send("unlock") }
        binding.btnLock.setOnClickListener   { send("lock")   }
        binding.btnPrev.setOnClickListener   { send("prev")   }
        binding.btnNext.setOnClickListener   { send("next")   }

        binding.btnAdminPanel.setOnClickListener {
            startActivity(Intent(this, AdminActivity::class.java).apply {
                putExtra(AdminActivity.EXTRA_SERVER_URL,       serverUrl)
                putExtra(AdminActivity.EXTRA_CURRENT_USER_ID, currentUserId)
            })
        }

        binding.btnLogout.setOnClickListener {
            viewModel.logout(serverUrl) {
                val intent = Intent(this, LoginActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                }
                startActivity(intent)
            }
        }

        viewModel.commandState.observe(this) { state ->
            when (state) {
                is CommandState.Idle    -> setButtonsEnabled(true)
                is CommandState.Loading -> {
                    setButtonsEnabled(false)
                    showStatus("⏳", "Gönderiliyor...", "#4CA1AF")
                }
                is CommandState.Success -> {
                    setButtonsEnabled(true)
                    showStatus("✓", state.message, "#4CAF50")
                    autoHideStatus(3000)
                    viewModel.resetState()
                }
                is CommandState.Error -> {
                    setButtonsEnabled(true)
                    showStatus("✗", state.message, "#F44336")
                    autoHideStatus(4000)
                    viewModel.resetState()
                }
            }
        }
    }

    private fun showStatus(icon: String, text: String, hexColor: String) {
        statusHideHandler.removeCallbacksAndMessages(null)
        binding.tvStatusIcon.text = icon
        binding.tvStatusIcon.setTextColor(Color.parseColor(hexColor))
        binding.tvStatusText.text = text
        binding.cardStatus.visibility = View.VISIBLE
    }

    private fun autoHideStatus(delayMs: Long) {
        statusHideHandler.postDelayed({
            binding.cardStatus.visibility = View.GONE
        }, delayMs)
    }

    private fun send(command: String) {
        if (boardId.isEmpty()) {
            Toast.makeText(this, "Tahta seçilmedi. Lütfen QR tarayın.", Toast.LENGTH_SHORT).show()
            return
        }
        viewModel.sendCommand(serverUrl, boardId, command)
    }

    private fun setButtonsEnabled(enabled: Boolean) {
        binding.btnUnlock.isEnabled     = enabled
        binding.btnLock.isEnabled       = enabled
        binding.btnPrev.isEnabled       = enabled
        binding.btnNext.isEnabled       = enabled
        binding.btnAdminPanel.isEnabled = enabled
        binding.btnLogout.isEnabled     = enabled
    }

    override fun onDestroy() {
        super.onDestroy()
        statusHideHandler.removeCallbacksAndMessages(null)
    }
}
