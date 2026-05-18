package com.tim.taketimeoff.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tim.taketimeoff.data.CompTimeCreditEntity
import com.tim.taketimeoff.data.HolidayEntity
import com.tim.taketimeoff.data.LeaveRepository
import com.tim.taketimeoff.data.LeaveRequestEntity
import com.tim.taketimeoff.data.LeaveRestrictionEntity
import com.tim.taketimeoff.data.LeaveYearEntity
import com.tim.taketimeoff.domain.LeaveSummary
import com.tim.taketimeoff.domain.RestrictionPart
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.ExperimentalCoroutinesApi
import java.time.LocalDate

@OptIn(ExperimentalCoroutinesApi::class)
class LeaveViewModel(private val repository: LeaveRepository) : ViewModel() {
    private val _selectedYear = MutableStateFlow(LocalDate.now().year)
    val selectedYear: StateFlow<Int> = _selectedYear

    val leaveYear = _selectedYear
        .flatMapLatest(repository::observeYear)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), LeaveYearEntity(LocalDate.now().year))

    val summaries: StateFlow<List<LeaveSummary>> = _selectedYear
        .flatMapLatest(repository::observeSummaries)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val requests = _selectedYear
        .flatMapLatest(repository::observeRequests)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val compCredits = repository.observeCompTimeCredits()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val restrictions = repository.observeRestrictions()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val holidays = _selectedYear
        .flatMapLatest(repository::observeHolidays)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _message = MutableStateFlow<String?>(null)
    val message: StateFlow<String?> = _message

    private val _isSyncingHolidays = MutableStateFlow(false)
    val isSyncingHolidays: StateFlow<Boolean> = _isSyncingHolidays

    init {
        viewModelScope.launch {
            _selectedYear.collect { repository.ensureDefaultHolidays(it) }
        }
    }

    fun selectYear(year: Int) {
        _selectedYear.value = year
    }

    fun saveAnnualDays(days: Double) = viewModelScope.launch {
        repository.saveYear(leaveYear.value.copy(year = selectedYear.value, annualLeaveDays = days))
        _message.value = "已更新 ${selectedYear.value} 年特休天數"
    }

    fun addLeaveRequest(request: LeaveRequestEntity) = viewModelScope.launch {
        val result = repository.addRequest(request)
        _message.value = if (result.allowed) "請假紀錄已新增" else result.message
    }

    fun addLeaveRequestRange(
        startDate: LocalDate,
        endDate: LocalDate,
        requestTemplate: LeaveRequestEntity,
    ) = viewModelScope.launch {
        val result = repository.addRequestRange(startDate, endDate, requestTemplate)
        _message.value = if (result.allowed) result.message else result.message
    }

    fun updateLeaveRequest(request: LeaveRequestEntity) = viewModelScope.launch {
        val result = repository.updateRequest(request)
        _message.value = if (result.allowed) "請假紀錄已更新" else result.message
    }

    fun deleteRequest(request: LeaveRequestEntity) = viewModelScope.launch {
        repository.deleteRequest(request)
        _message.value = "請假紀錄已刪除"
    }

    fun addCompTimeCredit(credit: CompTimeCreditEntity) = viewModelScope.launch {
        repository.addCompTimeCredit(credit)
        _message.value = "加班補休已新增"
    }

    fun updateCompTimeCredit(credit: CompTimeCreditEntity) = viewModelScope.launch {
        val result = repository.updateCompTimeCreditSafely(credit)
        _message.value = if (result.allowed) "加班補休已更新" else result.message
    }

    fun deleteCompTimeCredit(credit: CompTimeCreditEntity) = viewModelScope.launch {
        val result = repository.deleteCompTimeCreditSafely(credit)
        _message.value = if (result.allowed) "加班補休已刪除" else result.message
    }

    fun addRestriction(restriction: LeaveRestrictionEntity) = viewModelScope.launch {
        repository.addRestriction(restriction)
        _message.value = "不可休設定已新增"
    }

    fun addRestrictionRange(
        startDate: LocalDate,
        endDate: LocalDate,
        part: RestrictionPart,
        reason: String,
    ) = viewModelScope.launch {
        if (endDate.isBefore(startDate)) {
            _message.value = "結束日期不可早於開始日期"
            return@launch
        }
        val count = repository.addRestrictionRange(startDate, endDate, part, reason)
        _message.value = "已新增 $count 天不可休設定"
    }

    fun deleteRestriction(restriction: LeaveRestrictionEntity) = viewModelScope.launch {
        repository.deleteRestriction(restriction)
        _message.value = "不可休設定已刪除"
    }

    fun saveHoliday(holiday: HolidayEntity) = viewModelScope.launch {
        repository.saveHoliday(holiday)
        _message.value = "假日已儲存"
    }

    fun deleteHoliday(holiday: HolidayEntity) = viewModelScope.launch {
        repository.deleteHoliday(holiday)
        _message.value = "假日已刪除"
    }

    fun syncHolidays() = viewModelScope.launch {
        _isSyncingHolidays.value = true
        val result = repository.syncHolidays(selectedYear.value)
        _isSyncingHolidays.value = false
        _message.value = result.fold(
            onSuccess = { "國定假日已更新，共 $it 筆" },
            onFailure = { "無法連線，已使用本機假日資料" },
        )
    }

    fun clearMessage() {
        _message.value = null
    }
}
