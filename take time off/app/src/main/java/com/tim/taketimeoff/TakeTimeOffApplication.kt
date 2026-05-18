package com.tim.taketimeoff

import android.app.Application
import com.tim.taketimeoff.data.AppDatabase
import com.tim.taketimeoff.data.LeaveRepository

class TakeTimeOffApplication : Application() {
    val database by lazy { AppDatabase.create(this) }
    val repository by lazy { LeaveRepository(database.leaveDao()) }
}
