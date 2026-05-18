package com.tim.taketimeoff.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters

@Database(
    entities = [
        LeaveYearEntity::class,
        LeaveRequestEntity::class,
        CompTimeCreditEntity::class,
        CompTimeUsageEntity::class,
        HolidayEntity::class,
        LeaveRestrictionEntity::class,
    ],
    version = 3,
    exportSchema = false,
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun leaveDao(): LeaveDao

    companion object {
        fun create(context: Context): AppDatabase =
            Room.databaseBuilder(context, AppDatabase::class.java, "take-time-off.db")
                .fallbackToDestructiveMigration()
                .build()
    }
}
