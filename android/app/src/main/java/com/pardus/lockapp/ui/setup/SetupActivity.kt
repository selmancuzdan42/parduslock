package com.pardus.lockapp.ui.setup

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.pardus.lockapp.data.Constants
import com.pardus.lockapp.data.SessionManager
import com.pardus.lockapp.data.api.ApiClient
import com.pardus.lockapp.databinding.ActivitySetupBinding
import com.pardus.lockapp.ui.login.LoginActivity
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

// Bu ekran artık kullanılmıyor — launcher LoginActivity'dir.
// İleride sunucu URL değiştirme ayarı için kullanılabilir.
class SetupActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySetupBinding
    private lateinit var sessionManager: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySetupBinding.inflate(layoutInflater)
        setContentView(binding.root)

        sessionManager = SessionManager(this)

        lifecycleScope.launch {
            binding.etServerUrl.setText(sessionManager.serverUrlFlow.first())
        }

        binding.btnConnect.setOnClickListener {
            val url = binding.etServerUrl.text.toString().trim()
            if (url.isEmpty()) {
                binding.tilServerUrl.error = "Sunucu adresi boş olamaz"
                return@setOnClickListener
            }
            binding.tilServerUrl.error = null
            testConnection(url)
        }
    }

    private fun testConnection(url: String) {
        binding.btnConnect.isEnabled = false
        binding.progressBar.visibility = View.VISIBLE

        lifecycleScope.launch {
            try {
                ApiClient.getService(url).me()
                sessionManager.saveServerUrl(url)
                startActivity(Intent(this@SetupActivity, LoginActivity::class.java))
            } catch (e: Exception) {
                Toast.makeText(this@SetupActivity, "Bağlantı kurulamadı: ${e.message}", Toast.LENGTH_LONG).show()
            } finally {
                binding.btnConnect.isEnabled = true
                binding.progressBar.visibility = View.GONE
            }
        }
    }
}
