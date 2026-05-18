package com.tim.taketimeoff.data

import com.tim.taketimeoff.domain.DayPart
import com.tim.taketimeoff.domain.DeductionSource
import com.tim.taketimeoff.domain.HOURS_PER_DAY
import com.tim.taketimeoff.domain.LeaveSummary
import com.tim.taketimeoff.domain.LeaveType
import com.tim.taketimeoff.domain.ValidationResult
import com.tim.taketimeoff.domain.isWeekend
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import java.time.LocalDate
import java.time.Month

class LeaveRepository(
    private val dao: LeaveDao,
    private val holidaySyncService: HolidaySyncService = HolidaySyncService(),
) {
    fun observeYear(year: Int): Flow<LeaveYearEntity> =
        dao.observeYear(year).map { it ?: LeaveYearEntity(year = year) }

    fun observeRequests(year: Int): Flow<List<LeaveRequestEntity>> = dao.observeRequests(year)

    fun observeCompTimeCredits(): Flow<List<CompTimeCreditEntity>> = dao.observeCompTimeCredits()

    fun observeRestrictions(): Flow<List<LeaveRestrictionEntity>> = dao.observeRestrictions()

    fun observeHolidays(year: Int): Flow<List<HolidayEntity>> =
        dao.observeHolidays(LocalDate.of(year, 1, 1), LocalDate.of(year, 12, 31))

    fun observeSummaries(year: Int): Flow<List<LeaveSummary>> =
        combine(observeYear(year), observeRequests(year), observeCompTimeCredits()) { leaveYear, requests, credits ->
            val annualTotal = (leaveYear.annualLeaveDays * leaveYear.hoursPerDay).toInt()
            val compTotal = credits.sumOf { it.hours }
            LeaveType.entries
                .filterNot { it == LeaveType.COMP_TIME }
                .map { type ->
                    val total = when (type) {
                        LeaveType.ANNUAL -> annualTotal
                        else -> ((type.defaultDays ?: 0.0) * HOURS_PER_DAY).toInt()
                    }
                    val used = requests
                        .filter { it.leaveType == type || it.leaveType.quotaOwner == type }
                        .filter { it.deductionSource != DeductionSource.COMP_TIME }
                        .sumOf { it.hours }
                    LeaveSummary(type, total, used)
                }
                .toMutableList()
                .also { list ->
                    list.add(
                        1,
                        LeaveSummary(
                            LeaveType.COMP_TIME,
                            compTotal,
                            credits.sumOf { it.usedHours },
                        )
                    )
                }
        }

    suspend fun saveYear(year: LeaveYearEntity) = dao.saveYear(year)

    suspend fun addCompTimeCredit(credit: CompTimeCreditEntity) = dao.addCompTimeCredit(credit)

    suspend fun updateCompTimeCreditSafely(credit: CompTimeCreditEntity): ValidationResult {
        val original = dao.compTimeCredit(credit.id) ?: return ValidationResult(false, "找不到補休批次")
        if (credit.hours < original.usedHours) {
            return ValidationResult(false, "補休總時數不可小於已使用 ${original.usedHours} 小時")
        }
        dao.updateCompTimeCredit(credit.copy(usedHours = original.usedHours))
        return ValidationResult(true)
    }

    suspend fun deleteCompTimeCreditSafely(credit: CompTimeCreditEntity): ValidationResult {
        val current = dao.compTimeCredit(credit.id) ?: return ValidationResult(false, "找不到補休批次")
        if (current.usedHours > 0) {
            return ValidationResult(false, "此補休已被請假使用，不能刪除")
        }
        dao.deleteCompTimeCredit(current)
        return ValidationResult(true)
    }

    suspend fun addRestriction(restriction: LeaveRestrictionEntity) = dao.addRestriction(restriction)

    suspend fun addRestrictionRange(
        startDate: LocalDate,
        endDate: LocalDate,
        part: com.tim.taketimeoff.domain.RestrictionPart,
        reason: String,
    ): Int {
        if (endDate.isBefore(startDate)) return 0
        val restrictions = buildList {
            var cursor = startDate
            while (!cursor.isAfter(endDate)) {
                add(LeaveRestrictionEntity(date = cursor, part = part, reason = reason))
                cursor = cursor.plusDays(1)
            }
        }
        dao.addRestrictions(restrictions)
        return restrictions.size
    }

    suspend fun deleteRestriction(restriction: LeaveRestrictionEntity) = dao.deleteRestriction(restriction)

    suspend fun saveHoliday(holiday: HolidayEntity) = dao.saveHoliday(holiday)

    suspend fun deleteHoliday(holiday: HolidayEntity) = dao.deleteHoliday(holiday)

    suspend fun ensureDefaultHolidays(year: Int) {
        val start = LocalDate.of(year, 1, 1)
        val end = LocalDate.of(year, 12, 31)
        if (dao.holidayCount(start, end) == 0) {
            dao.insertHolidays(defaultTaiwanHolidays(year))
        }
    }

    suspend fun syncHolidays(year: Int): Result<Int> = runCatching {
        val holidays = holidaySyncService.fetchTaiwanHolidays(year)
        if (holidays.isEmpty()) error("No holiday rows")
        dao.replaceSyncedHolidays(year, holidays)
        holidays.size
    }

    suspend fun deleteRequest(request: LeaveRequestEntity) {
        restoreCompTimeUsages(request.id)
        dao.deleteCompTimeUsagesForRequest(request.id)
        dao.deleteRequest(request)
    }

    suspend fun addRequest(request: LeaveRequestEntity): ValidationResult {
        val validation = validateRequest(request, excludedRequestId = null)
        if (!validation.allowed) return validation

        val requestId = dao.addRequest(request)
        if (request.deductionSource == DeductionSource.COMP_TIME) {
            consumeCompTime(requestId, request.hours) ?: return ValidationResult(false, "加班補休時數不足或已到期")
        }
        return ValidationResult(true)
    }

    suspend fun addRequestRange(
        startDate: LocalDate,
        endDate: LocalDate,
        requestTemplate: LeaveRequestEntity,
    ): ValidationResult {
        if (endDate.isBefore(startDate)) return ValidationResult(false, "結束日期不可早於開始日期")

        var cursor = startDate
        var added = 0
        while (!cursor.isAfter(endDate)) {
            if (!cursor.isWeekend()) {
                val result = addRequest(requestTemplate.copy(id = 0, date = cursor))
                if (!result.allowed) {
                    return ValidationResult(false, "${cursor}：${result.message}")
                }
                added += 1
            }
            cursor = cursor.plusDays(1)
        }

        return if (added == 0) {
            ValidationResult(false, "範圍內沒有可請假的工作日")
        } else {
            ValidationResult(true, "已新增 $added 天請假紀錄")
        }
    }

    suspend fun updateRequest(request: LeaveRequestEntity): ValidationResult {
        val original = dao.requestById(request.id) ?: return ValidationResult(false, "找不到原本的請假紀錄")
        val validation = validateRequest(request, excludedRequestId = request.id)
        if (!validation.allowed) return validation

        if (original.deductionSource == DeductionSource.COMP_TIME) {
            restoreCompTimeUsages(original.id)
            dao.deleteCompTimeUsagesForRequest(original.id)
        }
        dao.updateRequest(request)
        if (request.deductionSource == DeductionSource.COMP_TIME) {
            consumeCompTime(request.id, request.hours) ?: return ValidationResult(false, "加班補休時數不足或已到期")
        }
        return ValidationResult(true)
    }

    private suspend fun validateRequest(request: LeaveRequestEntity, excludedRequestId: Long?): ValidationResult {
        if (request.date.isWeekend()) return ValidationResult(false, "週六週日不可選為請假日期")

        val sameDayHours = dao.requestsOn(request.date)
            .filterNot { it.id == excludedRequestId }
            .sumOf { it.hours } + request.hours
        if (sameDayHours > HOURS_PER_DAY) return ValidationResult(false, "同一天請假不可超過 8 小時")

        val restriction = dao.restrictionsOn(request.date).firstOrNull { it.part.blocks(request.dayPart) }
        if (restriction != null) {
            val reason = restriction.reason.ifBlank { restriction.part.title }
            return ValidationResult(false, "此時段不可休：$reason")
        }

        if (request.deductionSource == DeductionSource.COMP_TIME) {
            val ownUsage = excludedRequestId?.let { dao.usagesForRequest(it).sumOf { usage -> usage.hours } } ?: 0
            val available = dao.availableCompTimeCredits(LocalDate.now()).sumOf { it.hours - it.usedHours } + ownUsage
            if (available < request.hours) return ValidationResult(false, "加班補休剩餘不足")
        } else {
            val yearSnapshot = dao.observeYear(request.year).first() ?: LeaveYearEntity(request.year)
            val total = when (val owner = request.leaveType.quotaOwner) {
                LeaveType.ANNUAL -> (yearSnapshot.annualLeaveDays * yearSnapshot.hoursPerDay).toInt()
                else -> ((owner.defaultDays ?: 0.0) * HOURS_PER_DAY).toInt()
            }
            val owner = request.leaveType.quotaOwner
            val used = dao.requestsOnYear(request.year)
                .filterNot { it.id == excludedRequestId }
                .filter { it.deductionSource != DeductionSource.COMP_TIME }
                .filter { it.leaveType == owner || it.leaveType.quotaOwner == owner }
                .sumOf { it.hours }
            if (total > 0 && used + request.hours > total) {
                return ValidationResult(false, "${owner.title} 剩餘時數不足")
            }
        }

        return ValidationResult(true)
    }

    private suspend fun consumeCompTime(requestId: Long, hours: Int): Boolean? {
        var remaining = hours
        val credits = dao.availableCompTimeCredits(LocalDate.now())
        if (credits.sumOf { it.hours - it.usedHours } < hours) return null
        credits.forEach { credit ->
            if (remaining <= 0) return@forEach
            val available = credit.hours - credit.usedHours
            val used = minOf(available, remaining)
            dao.updateCompTimeCredit(credit.copy(usedHours = credit.usedHours + used))
            dao.addCompTimeUsage(CompTimeUsageEntity(requestId = requestId, creditId = credit.id, hours = used))
            remaining -= used
        }
        return remaining == 0
    }

    private suspend fun restoreCompTimeUsages(requestId: Long) {
        dao.usagesForRequest(requestId).forEach { usage ->
            val credit = dao.compTimeCredit(usage.creditId) ?: return@forEach
            dao.updateCompTimeCredit(credit.copy(usedHours = (credit.usedHours - usage.hours).coerceAtLeast(0)))
        }
    }

    private fun defaultTaiwanHolidays(year: Int): List<HolidayEntity> =
        when (year) {
            2026 -> buildList {
                addHoliday("2026-01-01", "元旦")
                addRange("2026-02-14", "2026-02-22", "農曆除夕及春節")
                addRange("2026-02-27", "2026-03-01", "和平紀念日")
                addRange("2026-04-03", "2026-04-06", "兒童節及清明節")
                addHoliday("2026-05-01", "勞動節")
                addRange("2026-06-19", "2026-06-21", "端午節")
                addRange("2026-09-25", "2026-09-29", "中秋節及教師節")
                addRange("2026-10-09", "2026-10-11", "國慶日")
                addRange("2026-10-24", "2026-10-26", "臺灣光復節")
                addRange("2026-12-25", "2026-12-27", "行憲紀念日")
            }
            else -> listOf(
                HolidayEntity(LocalDate.of(year, Month.JANUARY, 1), "元旦"),
            )
        }

    private fun MutableList<HolidayEntity>.addHoliday(date: String, name: String) {
        add(HolidayEntity(date = LocalDate.parse(date), name = name))
    }

    private fun MutableList<HolidayEntity>.addRange(start: String, end: String, name: String) {
        var cursor = LocalDate.parse(start)
        val last = LocalDate.parse(end)
        while (!cursor.isAfter(last)) {
            add(HolidayEntity(date = cursor, name = name))
            cursor = cursor.plusDays(1)
        }
    }
}
