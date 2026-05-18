package com.tim.taketimeoff

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.tim.taketimeoff.ui.LeaveApp
import com.tim.taketimeoff.ui.LeaveViewModel
import com.tim.taketimeoff.ui.theme.TakeTimeOffTheme

class MainActivity : ComponentActivity() {
    private val viewModel by viewModels<LeaveViewModel> {
        val app = application as TakeTimeOffApplication
        object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                return LeaveViewModel(app.repository) as T
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TakeTimeOffTheme {
                LeaveApp(viewModel)
            }
        }
    }
}
