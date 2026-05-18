package com.tim.taketimeoff.data

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Update
import kotlinx.coroutines.flow.Flow
import java.time.LocalDate

@Dao
interface LeaveDao {
    @Query("SELECT * FROM leave_years WHERE year = :year")
    fun observeYear(year: Int): Flow<LeaveYearEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveYear(year: LeaveYearEntity)

    @Query("SELECT * FROM leave_requests WHERE year = :year ORDER BY date DESC, id DESC")
    fun observeRequests(year: Int): Flow<List<LeaveRequestEntity>>

    @Query("SELECT * FROM leave_requests WHERE year = :year")
    suspend fun requestsOnYear(year: Int): List<LeaveRequestEntity>

    @Query("SELECT * FROM leave_requests WHERE date = :date")
    suspend fun requestsOn(date: LocalDate): List<LeaveRequestEntity>

    @Insert
    suspend fun addRequest(request: LeaveRequestEntity): Long

    @Update
    suspend fun updateRequest(request: LeaveRequestEntity)

    @Query("SELECT * FROM leave_requests WHERE id = :id")
    suspend fun requestById(id: Long): LeaveRequestEntity?

    @Delete
    suspend fun deleteRequest(request: LeaveRequestEntity)

    @Query("SELECT * FROM comp_time_credits ORDER BY expiresAt ASC")
    fun observeCompTimeCredits(): Flow<List<CompTimeCreditEntity>>

    @Insert
    suspend fun addCompTimeCredit(credit: CompTimeCreditEntity)

    @Update
    suspend fun updateCompTimeCredit(credit: CompTimeCreditEntity)

    @Delete
    suspend fun deleteCompTimeCredit(credit: CompTimeCreditEntity)

    @Query("SELECT * FROM comp_time_credits WHERE id = :id")
    suspend fun compTimeCredit(id: Long): CompTimeCreditEntity?

    @Query("SELECT * FROM comp_time_credits WHERE expiresAt >= :today AND usedHours < hours ORDER BY expiresAt ASC")
    suspend fun availableCompTimeCredits(today: LocalDate): List<CompTimeCreditEntity>

    @Query("SELECT * FROM comp_time_usages WHERE requestId = :requestId")
    suspend fun usagesForRequest(requestId: Long): List<CompTimeUsageEntity>

    @Insert
    suspend fun addCompTimeUsage(usage: CompTimeUsageEntity)

    @Query("DELETE FROM comp_time_usages WHERE requestId = :requestId")
    suspend fun deleteCompTimeUsagesForRequest(requestId: Long)

    @Query("SELECT * FROM leave_restrictions ORDER BY date ASC")
    fun observeRestrictions(): Flow<List<LeaveRestrictionEntity>>

    @Query("SELECT * FROM leave_restrictions WHERE date = :date")
    suspend fun restrictionsOn(date: LocalDate): List<LeaveRestrictionEntity>

    @Insert
    suspend fun addRestriction(restriction: LeaveRestrictionEntity)

    @Insert
    suspend fun addRestrictions(restrictions: List<LeaveRestrictionEntity>)

    @Delete
    suspend fun deleteRestriction(restriction: LeaveRestrictionEntity)

    @Query("SELECT * FROM holidays WHERE date BETWEEN :start AND :end ORDER BY date ASC")
    fun observeHolidays(start: LocalDate, end: LocalDate): Flow<List<HolidayEntity>>

    @Query("SELECT COUNT(*) FROM holidays WHERE date BETWEEN :start AND :end")
    suspend fun holidayCount(start: LocalDate, end: LocalDate): Int

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveHoliday(holiday: HolidayEntity)

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertHolidays(holidays: List<HolidayEntity>)

    @Delete
    suspend fun deleteHoliday(holiday: HolidayEntity)

    @Query("DELETE FROM holidays WHERE date BETWEEN :start AND :end AND isUserDefined = 0")
    suspend fun deleteSyncedHolidays(start: LocalDate, end: LocalDate)

    @Transaction
    suspend fun replaceSyncedHolidays(year: Int, holidays: List<HolidayEntity>) {
        deleteSyncedHolidays(LocalDate.of(year, 1, 1), LocalDate.of(year, 12, 31))
        insertHolidays(holidays)
    }
}
