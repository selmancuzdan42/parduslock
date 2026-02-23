package com.pardus.lockapp.data.api

import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Singleton Retrofit/OkHttp istemcisi.
 * Sunucu URL'i değiştirilebildiği için [rebuild] ile yeniden oluşturulabilir.
 */
object ApiClient {

    private val cookieStore = mutableMapOf<String, MutableList<Cookie>>()

    private val cookieJar = object : CookieJar {
        override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
            cookieStore[url.host] = cookies.toMutableList()
        }
        override fun loadForRequest(url: HttpUrl): List<Cookie> {
            return cookieStore[url.host] ?: emptyList()
        }
    }

    private fun buildOkHttp(): OkHttpClient = OkHttpClient.Builder()
        .cookieJar(cookieJar)
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    @Volatile
    private var _service: ApiService? = null
    private var _baseUrl: String = ""

    fun getService(baseUrl: String): ApiService {
        val normalizedUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        if (_service == null || _baseUrl != normalizedUrl) {
            synchronized(this) {
                if (_service == null || _baseUrl != normalizedUrl) {
                    _baseUrl = normalizedUrl
                    _service = Retrofit.Builder()
                        .baseUrl(normalizedUrl)
                        .client(buildOkHttp())
                        .addConverterFactory(GsonConverterFactory.create())
                        .build()
                        .create(ApiService::class.java)
                }
            }
        }
        return _service!!
    }

    /** Oturum çerezlerini temizler (çıkış sonrası). */
    fun clearCookies() {
        cookieStore.clear()
    }

    /** Hatalı yanıttan sunucu mesajını okur. */
    fun parseErrorMessage(response: retrofit2.Response<*>, fallback: String): String {
        return try {
            val body = response.errorBody()?.string()
            if (!body.isNullOrEmpty()) {
                org.json.JSONObject(body).optString("message", "").ifEmpty { fallback }
            } else fallback
        } catch (e: Exception) { fallback }
    }
}
