package com.aegis

import android.os.Bundle
import android.app.Activity
import android.widget.TextView
import uniffi.aegis_engine.MobileVault

class MainActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val textView = TextView(this)
        textView.text = "Initializing Aegis Vault..."
        setContentView(textView)

        try {
            // Initialize the Vault
            // Note: In a real app, the key would come from the Keystore/KeyChain
            // and the path would be the app's files directory.
            val filesDir = this.filesDir.absolutePath
            val key = ByteArray(32) { 0x01 } // Mock key

            val vault = MobileVault(filesDir, key)

            textView.text = "Aegis Vault Initialized!\nPath: $filesDir"

        } catch (e: Exception) {
            textView.text = "Error initializing Vault: ${e.message}"
        }
    }
}
