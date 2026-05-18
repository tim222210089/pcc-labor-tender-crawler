package com.tim.taketimeoff.data

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.tim.taketimeoff.domain.DayPart
import com.tim.taketimeoff.domain.DeductionSource
import com.tim.taketimeoff.domain.LeaveType
import com.tim.taketimeoff.domain.RestrictionPart
import java.time.LocalDate

@Entity(tableName = "leave_years")
data class LeaveYearEntity(
    @PrimaryKey val year: Int,
    val annualLeaveDays: Double = 14.0,
    val hoursPerDay: Int = 8,
)

@Entity(tableName = "leave_requests")
data class LeaveRequestEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val year: Int,
    val date: LocalDate,
    val leaveType: LeaveType,
    val dayPart: DayPart,
    val hours: Int,
    val deductionSource: DeductionSource,
    val note: String = "",
)

@Entity(tableName = "comp_time_credits")
data class CompTimeCreditEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val overtimeDate: LocalDate,
    val hours: Int,
    val usedHours: Int = 0,
    val expiresAt: LocalDate,
    val note: String = "",
)

@Entity(tableName = "comp_time_usages")
data class CompTimeUsageEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val requestId: Long,
    val creditId: Long,
    val hours: Int,
)

@Entity(tableName = "holidays")
data class HolidayEntity(
    @PrimaryKey val date: LocalDate,
    val name: String,
    val isNationalHoliday: Boolean = true,
    val isUserDefined: Boolean = false,
)

@Entity(tableName = "leave_restrictions")
data class LeaveRestrictionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val date: LocalDate,
    val part: RestrictionPart,
    val reason: String = "",
)
