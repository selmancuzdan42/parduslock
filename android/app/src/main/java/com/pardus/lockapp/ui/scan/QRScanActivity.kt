package com.pardus.lockapp.ui.scan

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import com.pardus.lockapp.databinding.ActivityQrScanBinding
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class QRScanActivity : AppCompatActivity() {

    companion object {
        const val RESULT_BOARD_ID  = "board_id"
        const val RESULT_SERVER_URL = "server_url"
    }

    private lateinit var binding: ActivityQrScanBinding
    private lateinit var cameraExecutor: ExecutorService
    private var scanned = false

    private val cameraPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) startCamera()
            else {
                Toast.makeText(this, "Kamera izni gerekli", Toast.LENGTH_SHORT).show()
                finish()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityQrScanBinding.inflate(layoutInflater)
        setContentView(binding.root)

        cameraExecutor = Executors.newSingleThreadExecutor()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED
        ) {
            startCamera()
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }

        binding.btnCancel.setOnClickListener { finish() }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }

            val imageAnalysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { analysis ->
                    analysis.setAnalyzer(cameraExecutor) { imageProxy ->
                        processImage(imageProxy)
                    }
                }

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    imageAnalysis
                )
            } catch (e: Exception) {
                Toast.makeText(this, "Kamera başlatılamadı", Toast.LENGTH_SHORT).show()
            }
        }, ContextCompat.getMainExecutor(this))
    }

    @androidx.annotation.OptIn(ExperimentalGetImage::class)
    private fun processImage(imageProxy: ImageProxy) {
        if (scanned) {
            imageProxy.close()
            return
        }
        val mediaImage = imageProxy.image ?: run { imageProxy.close(); return }
        val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)

        BarcodeScanning.getClient().process(image)
            .addOnSuccessListener { barcodes ->
                for (barcode in barcodes) {
                    if (barcode.valueType == Barcode.TYPE_URL ||
                        barcode.valueType == Barcode.TYPE_TEXT
                    ) {
                        val raw = barcode.rawValue ?: continue
                        parseBoardId(raw)?.let { boardId ->
                            scanned = true
                            val intent = android.content.Intent().apply {
                                putExtra(RESULT_BOARD_ID, boardId)
                            }
                            setResult(RESULT_OK, intent)
                            finish()
                            return@addOnSuccessListener
                        }
                    }
                }
            }
            .addOnCompleteListener { imageProxy.close() }
    }

    /**
     * QR içeriğinden board_id'yi çıkarır.
     * Desteklenen formatlar:
     *   1. Düz metin: "ETAP1"
     *   2. URL parametresi: "http://sunucu/?board_id=ETAP1"
     */
    private fun parseBoardId(raw: String): String? {
        val trimmed = raw.trim()
        // URL formatını dene
        return try {
            val param = Uri.parse(trimmed).getQueryParameter("board_id")
            if (!param.isNullOrBlank()) param
            else if (trimmed.isNotBlank()) trimmed  // Düz metin
            else null
        } catch (e: Exception) {
            if (trimmed.isNotBlank()) trimmed else null
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
