# Retrofit / Gson
-keepattributes Signature
-keepattributes *Annotation*
-keep class retrofit2.** { *; }
-keep class com.google.gson.** { *; }
-keep class com.pardus.lockapp.data.model.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**
