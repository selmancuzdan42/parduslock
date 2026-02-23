package com.pardus.lockapp.ui.admin

import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.pardus.lockapp.data.model.DashboardBoardItem
import com.pardus.lockapp.data.model.DashboardRecentCommand
import com.pardus.lockapp.databinding.ActivityDashboardBinding
import com.pardus.lockapp.databinding.ItemDashboardBoardBinding
import com.pardus.lockapp.databinding.ItemRecentCommandBinding

class DashboardActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SERVER_URL = "server_url"
        private const val REFRESH_MS = 10_000L
    }

    private lateinit var binding: ActivityDashboardBinding
    private val viewModel: DashboardViewModel by viewModels()
    private lateinit var serverUrl: String

    private val boardAdapter    = BoardDashAdapter()
    private val commandAdapter  = CommandDashAdapter()

    private val handler = Handler(Looper.getMainLooper())
    private val refreshRunnable = object : Runnable {
        override fun run() {
            viewModel.load(serverUrl)
            handler.postDelayed(this, REFRESH_MS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding   = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        serverUrl = intent.getStringExtra(EXTRA_SERVER_URL) ?: ""

        binding.rvBoards.layoutManager         = LinearLayoutManager(this)
        binding.rvBoards.adapter               = boardAdapter
        binding.rvRecentCommands.layoutManager = LinearLayoutManager(this)
        binding.rvRecentCommands.adapter       = commandAdapter

        binding.btnBack.setOnClickListener    { finish() }
        binding.btnRefresh.setOnClickListener { viewModel.load(serverUrl) }

        viewModel.state.observe(this) { state ->
            when (state) {
                is DashboardState.Idle    -> binding.progressBar.visibility = View.GONE
                is DashboardState.Loading -> binding.progressBar.visibility = View.VISIBLE
                is DashboardState.Loaded  -> {
                    binding.progressBar.visibility = View.GONE
                    val d = state.data

                    // ── İstatistikler ──
                    binding.tvOnlineCount.text  = d.boards.online.toString()
                    binding.tvTotalBoards.text  = "${d.boards.total} tahta toplam"
                    binding.tvTeacherCount.text = d.users.teachers.toString()
                    binding.tvAdminCount.text   = "${d.users.admins} yönetici"
                    binding.tvCmdTotal.text     = d.commands.last24h.toString()
                    binding.tvCmdDone.text      = "${d.commands.done24h} başarılı"

                    // ── Listeler ──
                    boardAdapter.submitList(d.boardList)
                    commandAdapter.submitList(d.recentCommands)
                }
                is DashboardState.Error   -> {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this, state.message, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        handler.post(refreshRunnable)
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(refreshRunnable)
    }

    // ══════════════════════════════════════════
    // Tahta listesi adapter
    // ══════════════════════════════════════════
    class BoardDashAdapter : ListAdapter<DashboardBoardItem, BoardDashAdapter.VH>(DIFF) {

        class VH(private val b: ItemDashboardBoardBinding) : RecyclerView.ViewHolder(b.root) {
            fun bind(item: DashboardBoardItem) {
                val onlineColor  = Color.parseColor("#4CAF50")
                val offlineColor = Color.parseColor("#F44336")

                b.tvDot.setTextColor(if (item.isOnline) onlineColor else offlineColor)
                b.tvName.text   = item.name
                b.tvSub.text    = buildString {
                    append(item.boardId)
                    if (!item.location.isNullOrBlank()) append(" · ${item.location}")
                }
                b.tvStatus.text = if (item.isOnline) "Çevrimiçi" else "Çevrimdışı"
                b.tvStatus.setTextColor(if (item.isOnline) onlineColor else offlineColor)
            }
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemDashboardBoardBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun onBindViewHolder(holder: VH, position: Int) = holder.bind(getItem(position))

        companion object {
            private val DIFF = object : DiffUtil.ItemCallback<DashboardBoardItem>() {
                override fun areItemsTheSame(a: DashboardBoardItem, b: DashboardBoardItem) = a.boardId == b.boardId
                override fun areContentsTheSame(a: DashboardBoardItem, b: DashboardBoardItem) = a == b
            }
        }
    }

    // ══════════════════════════════════════════
    // Son komutlar adapter
    // ══════════════════════════════════════════
    class CommandDashAdapter : ListAdapter<DashboardRecentCommand, CommandDashAdapter.VH>(DIFF) {

        class VH(private val b: ItemRecentCommandBinding) : RecyclerView.ViewHolder(b.root) {
            fun bind(cmd: DashboardRecentCommand) {
                val (label, color) = when (cmd.command) {
                    "unlock" -> "🔓 Kilit Aç" to "#4CAF50"
                    "lock"   -> "🔒 Kilitle"  to "#F44336"
                    "next"   -> "▶ Sonraki"   to "#FFA726"
                    "prev"   -> "◀ Önceki"    to "#42A5F5"
                    else     -> cmd.command    to "#AABBCC"
                }
                b.tvCmd.text = label
                b.tvCmd.setTextColor(Color.parseColor(color))
                b.tvBoard.text = cmd.boardId
                b.tvUser.text  = cmd.issuedBy ?: "—"

                val (statusLabel, statusColor) = when (cmd.status) {
                    "done"       -> "✓ Tamam"      to "#4CAF50"
                    "failed"     -> "✗ Başarısız"  to "#F44336"
                    "expired"    -> "⏱ Süresi Doldu" to "#FFA726"
                    "pending"    -> "⏳ Bekliyor"   to "#AABBCC"
                    "processing" -> "⚙ İşleniyor"  to "#42A5F5"
                    else         -> cmd.status       to "#AABBCC"
                }
                b.tvStatus.text = statusLabel
                b.tvStatus.setTextColor(Color.parseColor(statusColor))

                // "YYYY-MM-DD HH:MM:SS" → "HH:MM"
                b.tvTime.text = if (cmd.issuedAt.length >= 16) cmd.issuedAt.substring(11, 16) else cmd.issuedAt
            }
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemRecentCommandBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun onBindViewHolder(holder: VH, position: Int) = holder.bind(getItem(position))

        companion object {
            private val DIFF = object : DiffUtil.ItemCallback<DashboardRecentCommand>() {
                override fun areItemsTheSame(a: DashboardRecentCommand, b: DashboardRecentCommand) = a.id == b.id
                override fun areContentsTheSame(a: DashboardRecentCommand, b: DashboardRecentCommand) = a == b
            }
        }
    }
}
