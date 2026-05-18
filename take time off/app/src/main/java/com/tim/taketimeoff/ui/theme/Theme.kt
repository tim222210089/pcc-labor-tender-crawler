package com.tim.taketimeoff.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AppColors = lightColorScheme(
    primary = Color(0xFF0E7C7B),
    onPrimary = Color.White,
    secondary = Color(0xFFE17921),
    background = Color(0xFFF6F8FA),
    surface = Color.White,
    onSurface = Color(0xFF172026),
    error = Color(0xFFBA1A1A),
)

@Composable
fun TakeTimeOffTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AppColors,
        typography = MaterialTheme.typography,
        content = content,
    )
}
