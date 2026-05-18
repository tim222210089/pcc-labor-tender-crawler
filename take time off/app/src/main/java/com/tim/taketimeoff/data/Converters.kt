package com.tim.taketimeoff.data

import androidx.room.TypeConverter
import com.tim.taketimeoff.domain.DayPart
import com.tim.taketimeoff.domain.DeductionSource
import com.tim.taketimeoff.domain.LeaveType
import com.tim.taketimeoff.domain.RestrictionPart
import java.time.LocalDate

class Converters {
    @TypeConverter
    fun fromDate(value: LocalDate?): String? = value?.toString()

    @TypeConverter
    fun toDate(value: String?): LocalDate? = value?.let(LocalDate::parse)

    @TypeConverter
    fun fromLeaveType(value: LeaveType?): String? = value?.name

    @TypeConverter
    fun toLeaveType(value: String?): LeaveType? = value?.let(LeaveType::valueOf)

    @TypeConverter
    fun fromDayPart(value: DayPart?): String? = value?.name

    @TypeConverter
    fun toDayPart(value: String?): DayPart? = value?.let(DayPart::valueOf)

    @TypeConverter
    fun fromDeductionSource(value: DeductionSource?): String? = value?.name

    @TypeConverter
    fun toDeductionSource(value: String?): DeductionSource? = value?.let(DeductionSource::valueOf)

    @TypeConverter
    fun fromRestrictionPart(value: RestrictionPart?): String? = value?.name

    @TypeConverter
    fun toRestrictionPart(value: String?): RestrictionPart? = value?.let(RestrictionPart::valueOf)
}
