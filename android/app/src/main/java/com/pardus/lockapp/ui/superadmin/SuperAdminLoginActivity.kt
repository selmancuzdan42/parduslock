package com.pardus.lockapp.ui.superadmin

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import com.pardus.lockapp.data.Constants
import com.pardus.lockapp.databinding.ActivitySuperAdminLoginBinding

class SuperAdminLoginActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySuperAdminLoginBinding
    private val viewModel: SuperAdminViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySuperAdminLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnLogin.setOnClickListener {
            val username = binding.etUsername.text.toString().trim()
            val password = binding.etPassword.text.toString()

            if (username.isEmpty()) { binding.tilUsername.error = "Boş olamaz"; return@setOnClickListener }
            if (password.isEmpty()) { binding.tilPassword.error = "Boş olamaz"; return@setOnClickListener }
            binding.tilUsername.error = null
            binding.tilPassword.error = null

            viewModel.login(Constants.DEFAULT_SERVER_URL, username, password)
        }

        binding.btnBack.setOnClickListener { finish() }

        viewModel.state.observe(this) { state ->
            when (state) {
                is SaState.Loading -> setLoading(true)
                is SaState.LoginSuccess -> {
                    setLoading(false)
                    startActivity(Intent(this, SuperAdminActivity::class.java).apply {
                        putExtra(SuperAdminActivity.EXTRA_SA_USERNAME, state.username)
                    })
                    finish()
                }
                is SaState.Error -> {
                    setLoading(false)
                    Toast.makeText(this, state.message, Toast.LENGTH_LONG).show()
                    viewModel.resetState()
                }
                else -> setLoading(false)
            }
        }
    }

    private fun setLoading(loading: Boolean) {
        binding.btnLogin.isEnabled          = !loading
        binding.progressBar.visibility = if (loading) View.VISIBLE else View.GONE
    }
}
