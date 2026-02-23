package com.pardus.lockapp.data.model

import com.google.gson.annotations.SerializedName

data class User(
    val id: Int,
    val username: String,
    @SerializedName("full_name") val fullName: String,
    val role: String,
    @SerializedName("school_code") val schoolCode: String = ""
) {
    val isAdmin: Boolean      get() = role == "admin"
    val isSuperAdmin: Boolean get() = role == "superadmin"
    val roleBadge: String     get() = when (role) {
        "superadmin" -> "SÜPER ADMİN"
        "admin"      -> "YÖNETİCİ"
        else         -> "ÖĞRETMEN"
    }
}

// --- Request bodies ---

data class LoginRequest(
    val username: String,
    val password: String
)

data class SendCommandRequest(
    @SerializedName("board_id") val boardId: String,
    val command: String
)

data class AddUserRequest(
    val username: String,
    val password: String,
    @SerializedName("full_name") val fullName: String,
    val role: String
)

data class ChangePasswordRequest(
    @SerializedName("user_id") val userId: Int,
    @SerializedName("new_password") val newPassword: String
)

data class AddPermissionRequest(
    @SerializedName("user_id") val userId: Int
)

// --- Response bodies ---

data class LoginResponse(
    val status: String,
    val user: User?,
    val message: String?
)

data class MeResponse(
    val user: User?
)

data class StatusResponse(
    val status: String,
    val message: String?
)

data class UsersResponse(
    val users: List<User>
)

data class Board(
    @SerializedName("board_id") val boardId: String,
    val name: String,
    val location: String?,
    @SerializedName("is_online") val isOnline: Boolean,
    @SerializedName("is_active") val isActive: Boolean
)

data class BoardsResponse(
    val status: String,
    val boards: List<Board>?
)

data class BoardPermissionsResponse(
    val status: String,
    @SerializedName("board_id") val boardId: String?,
    val users: List<User>?
)

// --- Bulk Permission Requests ---

data class BulkBoardPermissionRequest(
    @SerializedName("user_ids") val userIds: List<Int>,
    val replace: Boolean = false
)

// --- Dashboard ---

data class DashboardBoardStats(
    val total: Int,
    val online: Int,
    val offline: Int
)

data class DashboardUserStats(
    val total: Int,
    val admins: Int,
    val teachers: Int
)

data class DashboardCommandStats(
    @SerializedName("last_24h")    val last24h: Int,
    @SerializedName("done_24h")    val done24h: Int,
    @SerializedName("failed_24h")  val failed24h: Int,
    @SerializedName("expired_24h") val expired24h: Int
)

data class DashboardBoardItem(
    @SerializedName("board_id")  val boardId: String,
    val name: String,
    val location: String?,
    @SerializedName("is_online") val isOnline: Boolean,
    @SerializedName("last_seen") val lastSeen: String?,
    @SerializedName("is_active") val isActive: Boolean
)

data class DashboardRecentCommand(
    val id: Int,
    @SerializedName("board_id")  val boardId: String,
    val command: String,
    val status: String,
    @SerializedName("issued_at") val issuedAt: String,
    @SerializedName("issued_by") val issuedBy: String?
)

// --- Süperadmin ---

data class SaLoginRequest(val username: String, val password: String)

data class SaLoginResponse(
    val status: String,
    val username: String?,
    val message: String?
)

data class License(
    val id: Int,
    @SerializedName("school_code")     val schoolCode: String,
    @SerializedName("school_name")     val schoolName: String,
    @SerializedName("start_date")      val startDate: String,
    @SerializedName("end_date")        val endDate: String,
    @SerializedName("duration_months") val durationMonths: Int,
    val active: Int,
    val notes: String?
) {
    val isActive: Boolean get() = active == 1
}

data class SchoolAdmin(
    val id: Int,
    val username: String,
    @SerializedName("full_name")   val fullName: String,
    @SerializedName("school_code") val schoolCode: String
)

data class SaBoard(
    @SerializedName("board_id")    val boardId: String,
    val name: String,
    val location: String?,
    @SerializedName("school_code") val schoolCode: String,
    @SerializedName("is_active")   val isActive: Boolean
)

data class SaDashboardResponse(
    val status: String,
    val licenses: List<License>,
    @SerializedName("school_admins") val schoolAdmins: List<SchoolAdmin>,
    val boards: List<SaBoard>
)

data class AddLicenseRequest(
    @SerializedName("school_code")     val schoolCode: String,
    @SerializedName("school_name")     val schoolName: String,
    @SerializedName("start_date")      val startDate: String,
    @SerializedName("duration_months") val durationMonths: Int,
    val notes: String = ""
)

data class AddSchoolAdminRequest(
    val username: String,
    val password: String,
    @SerializedName("full_name")   val fullName: String,
    @SerializedName("school_code") val schoolCode: String
)

data class AssignBoardRequest(
    @SerializedName("board_id")    val boardId: String,
    @SerializedName("school_code") val schoolCode: String
)

data class DashboardResponse(
    val status: String,
    val boards: DashboardBoardStats,
    val users: DashboardUserStats,
    val commands: DashboardCommandStats,
    @SerializedName("board_list")        val boardList: List<DashboardBoardItem>,
    @SerializedName("recent_commands")   val recentCommands: List<DashboardRecentCommand>
)
