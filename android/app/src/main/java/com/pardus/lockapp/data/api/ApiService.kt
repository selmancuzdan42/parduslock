package com.pardus.lockapp.data.api

import com.pardus.lockapp.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    @POST("api/login")
    suspend fun login(@Body body: LoginRequest): Response<LoginResponse>

    @POST("api/logout")
    suspend fun logout(): Response<StatusResponse>

    @GET("api/me")
    suspend fun me(): Response<MeResponse>

    @POST("api/send_command")
    suspend fun sendCommand(@Body body: SendCommandRequest): Response<StatusResponse>

    @GET("api/admin/users")
    suspend fun getUsers(): Response<UsersResponse>

    @POST("api/admin/add_user")
    suspend fun addUser(@Body body: AddUserRequest): Response<StatusResponse>

    @DELETE("api/admin/users/{user_id}")
    suspend fun deleteUser(@Path("user_id") userId: Int): Response<StatusResponse>

    @POST("api/admin/change_password")
    suspend fun changePassword(@Body body: ChangePasswordRequest): Response<StatusResponse>

    // --- Tahta Yönetimi ---

    @GET("api/admin/boards")
    suspend fun getBoards(): Response<BoardsResponse>

    @GET("api/admin/boards/{board_id}/permissions")
    suspend fun getBoardPermissions(
        @Path("board_id") boardId: String
    ): Response<BoardPermissionsResponse>

    @POST("api/admin/boards/{board_id}/permissions")
    suspend fun addBoardPermission(
        @Path("board_id") boardId: String,
        @Body body: AddPermissionRequest
    ): Response<StatusResponse>

    @DELETE("api/admin/boards/{board_id}/permissions/{user_id}")
    suspend fun removeBoardPermission(
        @Path("board_id") boardId: String,
        @Path("user_id") userId: Int
    ): Response<StatusResponse>

    @POST("api/admin/boards/{board_id}/permissions/bulk")
    suspend fun bulkBoardPermissions(
        @Path("board_id") boardId: String,
        @Body body: BulkBoardPermissionRequest
    ): Response<StatusResponse>

    @DELETE("api/admin/boards/{board_id}")
    suspend fun deleteBoard(
        @Path("board_id") boardId: String
    ): Response<StatusResponse>

    // --- Dashboard ---

    @GET("api/admin/dashboard")
    suspend fun getDashboard(): Response<DashboardResponse>

    // --- Süperadmin ---

    @POST("api/sa/login")
    suspend fun saLogin(@Body body: SaLoginRequest): Response<SaLoginResponse>

    @POST("api/sa/logout")
    suspend fun saLogout(): Response<StatusResponse>

    @GET("api/sa/dashboard")
    suspend fun getSaDashboard(): Response<SaDashboardResponse>

    @POST("api/sa/license/add")
    suspend fun addLicense(@Body body: AddLicenseRequest): Response<StatusResponse>

    @POST("api/sa/license/{id}/toggle")
    suspend fun toggleLicense(@Path("id") id: Int): Response<StatusResponse>

    @DELETE("api/sa/license/{id}")
    suspend fun deleteLicense(@Path("id") id: Int): Response<StatusResponse>

    @POST("api/sa/school_admin/add")
    suspend fun addSchoolAdmin(@Body body: AddSchoolAdminRequest): Response<StatusResponse>

    @DELETE("api/sa/school_admin/{id}")
    suspend fun deleteSchoolAdmin(@Path("id") id: Int): Response<StatusResponse>

    @POST("api/sa/board/assign")
    suspend fun assignBoard(@Body body: AssignBoardRequest): Response<StatusResponse>

    @DELETE("api/sa/board/{board_id}")
    suspend fun deleteSaBoard(@Path("board_id") boardId: String): Response<StatusResponse>
}
