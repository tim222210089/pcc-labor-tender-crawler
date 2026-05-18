package com.tim.taketimeoff.domain

import androidx.compose.ui.graphics.Color
import java.time.LocalDate

const val HOURS_PER_DAY = 8

enum class LeaveType(
    val title: String,
    val defaultDays: Double?,
    val color: Color,
    val countsAgainst: LeaveType? = null,
) {
    ANNUAL("特休", null, Color(0xFF0E7C7B)),
    COMP_TIME("加班補休", null, Color(0xFFE17921)),
    PERSONAL("事假", 7.0, Color(0xFF64748B)),
    FAMILY_CARE("家庭照顧假", 7.0, Color(0xFF4F6F8F), PERSONAL),
    WELLNESS("身心調適假", 3.0, Color(0xFF536DFE), PERSONAL),
    SICK("病假", 28.0, Color(0xFF2E8B57)),
    MENSTRUAL("生理假", null, Color(0xFFB85C8E), SICK),
    MARRIAGE("婚假", 14.0, Color(0xFFD18B00)),
    PRENATAL("產前假", 8.0, Color(0xFFB96B8A)),
    MATERNITY("娩假", 42.0, Color(0xFFA65E7A)),
    MISCARRIAGE("流產假", 14.0, Color(0xFF8F5C78)),
    PATERNITY("陪產檢及陪產假", 7.0, Color(0xFF7C6BC4)),
    BEREAVEMENT("喪假", 5.0, Color(0xFF475569));

    val quotaOwner: LeaveType get() = countsAgainst ?: this
}

enum class DayPart(val title: String, val hours: Int) {
    FULL_DAY("全天", 8),
    MORNING("上午", 4),
    AFTERNOON("下午", 4),
    CUSTOM("自訂", 1);
}

enum class DeductionSource(val title: String) {
    LEAVE_TYPE("該假別額度"),
    ANNUAL("扣特休"),
    COMP_TIME("扣加班補休");
}

enum class RestrictionPart(val title: String) {
    FULL_DAY("整天不可休"),
    MORNING("上午不可休"),
    AFTERNOON("下午不可休");

    fun blocks(dayPart: DayPart): Boolean = when (this) {
        FULL_DAY -> true
        MORNING -> dayPart == DayPart.MORNING || dayPart == DayPart.FULL_DAY
        AFTERNOON -> dayPart == DayPart.AFTERNOON || dayPart == DayPart.FULL_DAY
    }
}

data class LeaveSummary(
    val type: LeaveType,
    val totalHours: Int,
    val usedHours: Int,
) {
    val remainingHours: Int get() = totalHours - usedHours
    val totalDays: Double get() = totalHours.toDouble() / HOURS_PER_DAY
    val usedDays: Double get() = usedHours.toDouble() / HOURS_PER_DAY
    val remainingDays: Double get() = remainingHours.toDouble() / HOURS_PER_DAY
    val progress: Float
        get() = if (totalHours <= 0) 0f else (usedHours.toFloat() / totalHours).coerceIn(0f, 1f)
}

data class ValidationResult(
    val allowed: Boolean,
    val message: String = "",
)

fun LocalDate.isWeekend(): Boolean {
    val day = dayOfWeek.value
    return day == 6 || day == 7
}

fun Double.formatDays(): String {
    val whole = toInt()
    return if (this == whole.toDouble()) "${whole}天" else "%.1f天".format(this)
}

fun Int.formatAsDaysAndHours(): String {
    val days = this / HOURS_PER_DAY
    val hours = this % HOURS_PER_DAY
    return when {
        this <= 0 -> "0天"
        days == 0 -> "${hours}小時"
        hours == 0 -> "${days}天"
        else -> "${days}天又${hours}小時"
    }
}
