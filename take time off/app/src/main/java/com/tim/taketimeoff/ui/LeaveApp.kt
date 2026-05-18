package com.tim.taketimeoff.ui

import android.app.DatePickerDialog
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Block
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.EventAvailable
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.ListAlt
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tim.taketimeoff.data.CompTimeCreditEntity
import com.tim.taketimeoff.data.HolidayEntity
import com.tim.taketimeoff.data.LeaveRequestEntity
import com.tim.taketimeoff.data.LeaveRestrictionEntity
import com.tim.taketimeoff.domain.DayPart
import com.tim.taketimeoff.domain.DeductionSource
import com.tim.taketimeoff.domain.LeaveSummary
import com.tim.taketimeoff.domain.LeaveType
import com.tim.taketimeoff.domain.RestrictionPart
import com.tim.taketimeoff.domain.formatAsDaysAndHours
import com.tim.taketimeoff.domain.formatDays
import com.tim.taketimeoff.domain.isWeekend
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeFormatter

private enum class AppTab(val title: String, val icon: ImageVector) {
    DASHBOARD("總覽", Icons.Default.EventAvailable),
    ADD_LEAVE("新增", Icons.Default.Add),
    RECORDS("紀錄", Icons.Default.ListAlt),
    COMP_TIME("補休", Icons.Default.HourglassTop),
    RESTRICTION("限制", Icons.Default.Block),
    SETTINGS("設定", Icons.Default.Settings),
}

private val DateText = DateTimeFormatter.ofPattern("yyyy/MM/dd")
private val MonthText = DateTimeFormatter.ofPattern("yyyy 年 M 月")

private enum class RecordMode(val title: String) {
    CALENDAR("行事曆"),
    LIST("清單"),
}

@Composable
fun LeaveApp(viewModel: LeaveViewModel) {
    var tab by remember { mutableStateOf(AppTab.DASHBOARD) }
    var editingRequest by remember { mutableStateOf<LeaveRequestEntity?>(null) }
    var recordFilter by remember { mutableStateOf<LeaveType?>(null) }
    val snackbarHostState = remember { SnackbarHostState() }
    val message by viewModel.message.collectAsState()

    LaunchedEffect(message) {
        val current = message ?: return@LaunchedEffect
        snackbarHostState.showSnackbar(current)
        viewModel.clearMessage()
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            NavigationBar {
                AppTab.entries.forEach { item ->
                    NavigationBarItem(
                        selected = tab == item,
                        onClick = { tab = item },
                        icon = { Icon(item.icon, contentDescription = item.title) },
                        label = { Text(item.title) },
                    )
                }
            }
        },
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(padding)
        ) {
            when (tab) {
                AppTab.DASHBOARD -> DashboardScreen(
                    viewModel = viewModel,
                    onOpenType = {
                        recordFilter = it
                        tab = AppTab.RECORDS
                    },
                    onEdit = {
                        editingRequest = it
                        tab = AppTab.ADD_LEAVE
                    },
                )
                AppTab.ADD_LEAVE -> AddLeaveScreen(
                    viewModel = viewModel,
                    editingRequest = editingRequest,
                    onFinished = {
                        editingRequest = null
                        tab = AppTab.RECORDS
                    },
                )
                AppTab.RECORDS -> RecordsScreen(
                    viewModel = viewModel,
                    selectedType = recordFilter,
                    onTypeChange = { recordFilter = it },
                    onEdit = {
                        editingRequest = it
                        tab = AppTab.ADD_LEAVE
                    },
                )
                AppTab.COMP_TIME -> CompTimeScreen(viewModel)
                AppTab.RESTRICTION -> RestrictionScreen(viewModel)
                AppTab.SETTINGS -> SettingsScreen(viewModel)
            }
        }
    }
}

@Composable
private fun ScreenColumn(content: LazyListScope.() -> Unit) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
        content = content,
    )
}

@Composable
private fun PageTitle(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, fontSize = 32.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
        Text(subtitle, fontSize = 15.sp, color = Color(0xFF607080))
    }
}

@Composable
private fun DashboardScreen(
    viewModel: LeaveViewModel,
    onOpenType: (LeaveType) -> Unit,
    onEdit: (LeaveRequestEntity) -> Unit,
) {
    val selectedYear by viewModel.selectedYear.collectAsState()
    val summaries by viewModel.summaries.collectAsState()
    val requests by viewModel.requests.collectAsState()
    val compCredits by viewModel.compCredits.collectAsState()
    val annual = summaries.firstOrNull { it.type == LeaveType.ANNUAL }
    val compTime = summaries.firstOrNull { it.type == LeaveType.COMP_TIME }
    val soonExpiring = compCredits.filter {
        !it.expiresAt.isBefore(LocalDate.now()) && it.expiresAt.minusDays(30).isBefore(LocalDate.now())
    }.sumOf { it.hours - it.usedHours }

    ScreenColumn {
        item {
            PageTitle("我的特休總覽", "$selectedYear 年度假別與剩餘額度")
        }
        item {
            YearSelector(selectedYear, onPrevious = { viewModel.selectYear(selectedYear - 1) }, onNext = { viewModel.selectYear(selectedYear + 1) })
        }
        annual?.let {
            item { HeroSummaryCard(it, onClick = { onOpenType(it.type) }) }
        }
        compTime?.let {
            item { CompSummaryCard(it, soonExpiring, onClick = { onOpenType(it.type) }) }
        }
        item { SectionTitle("其他假別") }
        items(summaries.filterNot { it.type == LeaveType.ANNUAL || it.type == LeaveType.COMP_TIME }) {
            LeaveSummaryCard(it, onClick = { onOpenType(it.type) })
        }
        item { SectionTitle("請假紀錄") }
        if (requests.isEmpty()) {
            item { EmptyCard("目前沒有請假紀錄") }
        } else {
            items(requests.take(8)) { request ->
                RequestRow(
                    request = request,
                    onEdit = { onEdit(request) },
                    onDelete = { viewModel.deleteRequest(request) },
                )
            }
        }
    }
}

@Composable
private fun YearSelector(year: Int, onPrevious: () -> Unit, onNext: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        OutlinedButton(onClick = onPrevious) { Text("上一年") }
        Text("$year", fontSize = 22.sp, fontWeight = FontWeight.Bold)
        OutlinedButton(onClick = onNext) { Text("下一年") }
    }
}

@Composable
private fun HeroSummaryCard(summary: LeaveSummary, onClick: () -> Unit) {
    ElevatedCard(
        colors = CardDefaults.elevatedCardColors(containerColor = Color(0xFF0E7C7B)),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("特休剩餘", color = Color.White.copy(alpha = 0.86f), fontWeight = FontWeight.SemiBold)
            Text(
                text = "${summary.remainingHours} 小時 / ${summary.remainingHours.formatAsDaysAndHours()}",
                color = Color.White,
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            LinearProgressIndicator(
                progress = { 1f - summary.progress },
                modifier = Modifier.fillMaxWidth(),
                color = Color.White,
                trackColor = Color.White.copy(alpha = 0.24f),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                SmallMetric("總額", "${summary.totalHours} 小時")
                SmallMetric("已請", "${summary.usedHours} 小時")
            }
        }
    }
}

@Composable
private fun CompSummaryCard(summary: LeaveSummary, soonExpiring: Int, onClick: () -> Unit) {
    LeaveSummaryCard(summary, extra = "30 天內到期 $soonExpiring 小時", onClick = onClick)
}

@Composable
private fun SmallMetric(label: String, value: String) {
    Column {
        Text(label, color = Color.White.copy(alpha = 0.72f), fontSize = 12.sp)
        Text(value, color = Color.White, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun LeaveSummaryCard(summary: LeaveSummary, extra: String? = null, onClick: (() -> Unit)? = null) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, Color(0xFFE6EBEF)),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(12.dp).background(summary.type.color))
                Spacer(Modifier.width(10.dp))
                Text(summary.type.title, fontSize = 19.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                Text("${summary.remainingHours} 小時", fontWeight = FontWeight.Bold, color = summary.type.color)
            }
            Text("剩餘 ${summary.remainingDays.formatDays()} / 總額 ${summary.totalDays.formatDays()} / 已請 ${summary.usedHours} 小時", color = Color(0xFF5E6B76))
            LinearProgressIndicator(
                progress = { summary.progress },
                modifier = Modifier.fillMaxWidth(),
                color = summary.type.color,
                trackColor = Color(0xFFE9EEF2),
            )
            if (extra != null) Text(extra, color = Color(0xFFE17921), fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun SectionTitle(title: String) {
    Text(title, fontSize = 22.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 8.dp))
}

@Composable
private fun EmptyCard(text: String) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Text(text, Modifier.padding(18.dp), color = Color(0xFF6B7785))
    }
}

@Composable
private fun RequestRow(request: LeaveRequestEntity, onEdit: () -> Unit, onDelete: () -> Unit) {
    var confirmDelete by remember { mutableStateOf(false) }

    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("刪除請假紀錄") },
            text = { Text("確定要刪除 ${request.date.format(DateText)} 的 ${request.leaveType.title} ${request.hours} 小時嗎？") },
            confirmButton = {
                TextButton(
                    onClick = {
                        confirmDelete = false
                        onDelete()
                    },
                ) { Text("刪除") }
            },
            dismissButton = {
                TextButton(onClick = { confirmDelete = false }) { Text("取消") }
            },
        )
    }

    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("${request.leaveType.title} · ${request.hours} 小時", fontWeight = FontWeight.Bold)
                Text("${request.date.format(DateText)} ${request.dayPart.title} · ${request.deductionSource.title}", color = Color(0xFF607080))
                if (request.note.isNotBlank()) Text(request.note, color = Color(0xFF607080))
            }
            IconButton(onClick = onEdit) {
                Icon(Icons.Default.Edit, contentDescription = "編輯")
            }
            IconButton(onClick = { confirmDelete = true }) {
                Icon(Icons.Default.Delete, contentDescription = "刪除")
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun RecordsScreen(
    viewModel: LeaveViewModel,
    selectedType: LeaveType?,
    onTypeChange: (LeaveType?) -> Unit,
    onEdit: (LeaveRequestEntity) -> Unit,
) {
    val year by viewModel.selectedYear.collectAsState()
    val requests by viewModel.requests.collectAsState()
    val holidays by viewModel.holidays.collectAsState()
    val restrictions by viewModel.restrictions.collectAsState()
    val isSyncingHolidays by viewModel.isSyncingHolidays.collectAsState()
    var mode by remember { mutableStateOf(RecordMode.CALENDAR) }
    var visibleMonth by remember(year) { mutableStateOf(YearMonth.of(year, LocalDate.now().monthValue)) }
    var selectedDate by remember(visibleMonth) { mutableStateOf<LocalDate?>(null) }
    val visibleRequests = requests.filter { request ->
        selectedType == null ||
            request.leaveType == selectedType ||
            request.leaveType.quotaOwner == selectedType
    }
    val title = selectedType?.let { "${it.title}請假日期" } ?: "請假紀錄"

    ScreenColumn {
        item { PageTitle(title, "$year 年度每筆請假日期、時段與時數") }
        item { YearSelector(year, onPrevious = { viewModel.selectYear(year - 1) }, onNext = { viewModel.selectYear(year + 1) }) }
        item {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                RecordMode.entries.forEach {
                    FilterChip(selected = mode == it, onClick = { mode = it }, label = { Text(it.title) })
                }
            }
        }
        item {
            EnumDropdown(
                label = "假別篩選",
                selected = selectedType,
                options = listOf<LeaveType?>(null) + LeaveType.entries.filterNot { it == LeaveType.COMP_TIME },
                title = { it?.title ?: "全部假別" },
                onSelected = onTypeChange,
            )
        }
        if (mode == RecordMode.CALENDAR) {
            item {
                Button(
                    onClick = { viewModel.syncHolidays() },
                    enabled = !isSyncingHolidays,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(if (isSyncingHolidays) "更新中..." else "更新國定假日")
                }
            }
            item {
                CalendarMonthView(
                    month = visibleMonth,
                    requests = requests,
                    holidays = holidays,
                    restrictions = restrictions,
                    selectedDate = selectedDate,
                    onPreviousMonth = { visibleMonth = visibleMonth.minusMonths(1) },
                    onNextMonth = { visibleMonth = visibleMonth.plusMonths(1) },
                    onSelectDate = { selectedDate = it },
                )
            }
            val dayRequests = selectedDate?.let { date -> visibleRequests.filter { it.date == date } }.orEmpty()
            val holiday = selectedDate?.let { date -> holidays.firstOrNull { it.date == date } }
            val dayRestrictions = selectedDate?.let { date -> restrictions.filter { it.date == date } }.orEmpty()
            if (selectedDate != null) {
                item { SelectedDateHeader(selectedDate!!, holiday, dayRestrictions) }
                if (dayRequests.isEmpty()) {
                    item { EmptyCard("這一天沒有請假紀錄") }
                } else {
                    items(dayRequests) { request ->
                        RequestRow(
                            request = request,
                            onEdit = { onEdit(request) },
                            onDelete = { viewModel.deleteRequest(request) },
                        )
                    }
                }
            } else {
                item { EmptyCard("點選日期後，這裡會顯示當天請了哪些假") }
            }
            item { HolidayEditor(viewModel) }
        } else if (visibleRequests.isEmpty()) {
            item { EmptyCard(selectedType?.let { "目前沒有${it.title}紀錄" } ?: "目前沒有請假紀錄") }
        } else {
            items(visibleRequests) { request ->
                RequestRow(
                    request = request,
                    onEdit = { onEdit(request) },
                    onDelete = { viewModel.deleteRequest(request) },
                )
            }
        }
    }
}

@Composable
private fun CalendarMonthView(
    month: YearMonth,
    requests: List<LeaveRequestEntity>,
    holidays: List<HolidayEntity>,
    restrictions: List<LeaveRestrictionEntity>,
    selectedDate: LocalDate?,
    onPreviousMonth: () -> Unit,
    onNextMonth: () -> Unit,
    onSelectDate: (LocalDate) -> Unit,
) {
    val monthStart = month.atDay(1)
    val leadingEmptyCells = monthStart.dayOfWeek.value - 1
    val days = (1..month.lengthOfMonth()).map(month::atDay)
    val cells = List(leadingEmptyCells) { null } + days
    val rows = cells.chunked(7)
    val holidayByDate = holidays.associateBy { it.date }
    val requestsByDate = requests.groupBy { it.date }
    val restrictedDates = restrictions.map { it.date }.toSet()

    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedButton(onClick = onPreviousMonth) { Text("上個月") }
                Text(month.atDay(1).format(MonthText), fontSize = 20.sp, fontWeight = FontWeight.Bold)
                OutlinedButton(onClick = onNextMonth) { Text("下個月") }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                listOf("一", "二", "三", "四", "五", "六", "日").forEach {
                    Text(it, modifier = Modifier.weight(1f), fontWeight = FontWeight.Bold, color = Color(0xFF607080))
                }
            }
            rows.forEach { row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    row.forEach { date ->
                        CalendarDayCell(
                            date = date,
                            holiday = date?.let { holidayByDate[it] },
                            requests = date?.let { requestsByDate[it].orEmpty() }.orEmpty(),
                            isRestricted = date in restrictedDates,
                            isSelected = date == selectedDate,
                            onClick = { if (date != null) onSelectDate(date) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                    repeat(7 - row.size) {
                        Spacer(Modifier.weight(1f))
                    }
                }
            }
        }
    }
}

@Composable
private fun CalendarDayCell(
    date: LocalDate?,
    holiday: HolidayEntity?,
    requests: List<LeaveRequestEntity>,
    isRestricted: Boolean,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val isHoliday = date?.isWeekend() == true || holiday != null
    val background = when {
        date == null -> Color.Transparent
        isSelected -> Color(0xFFE0F2F1)
        isHoliday -> Color(0xFFFFE4EC)
        else -> Color.White
    }
    val borderColor = if (isSelected) Color(0xFF0E7C7B) else Color(0xFFE6EBEF)

    Card(
        modifier = modifier.clickable(enabled = date != null, onClick = onClick),
        colors = CardDefaults.cardColors(containerColor = background),
        border = BorderStroke(1.dp, borderColor),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .height(86.dp)
                .padding(6.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            if (date == null) {
                Text(" ", fontSize = 14.sp)
            } else {
                Text("${date.dayOfMonth}", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                CalendarMetaLabel(
                    text = when {
                        holiday != null -> holiday.name
                        date.isWeekend() -> "假日"
                        isRestricted -> "禁"
                        else -> ""
                    },
                    color = if (isRestricted && holiday == null && !date.isWeekend()) Color(0xFFBA1A1A) else Color(0xFFB32656),
                )
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f),
                    contentAlignment = Alignment.Center,
                ) {
                    CalendarLeaveSummaryTag(requests)
                }
            }
        }
    }
}

@Composable
private fun CalendarMetaLabel(text: String, color: Color) {
    Text(
        text = text.ifBlank { " " },
        fontSize = 10.sp,
        color = color,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun CalendarLeaveSummaryTag(requests: List<LeaveRequestEntity>) {
    if (requests.isEmpty()) return
    val types = requests.map { it.leaveType }.distinct()
    val overflowCount = (types.size - 3).coerceAtLeast(0)
    val text = buildString {
        append(types.take(3).joinToString(" ") { it.title })
        if (overflowCount > 0) append(" +$overflowCount")
    }
    Text(
        text = text,
        fontSize = 10.sp,
        fontWeight = FontWeight.SemiBold,
        color = Color.White,
        maxLines = 1,
        overflow = TextOverflow.Ellipsis,
        textAlign = TextAlign.Center,
        modifier = Modifier
            .fillMaxWidth()
            .height(18.dp)
            .background(types.first().color)
            .padding(horizontal = 3.dp),
    )
}

@Composable
private fun SelectedDateHeader(date: LocalDate, holiday: HolidayEntity?, restrictions: List<LeaveRestrictionEntity>) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        SectionTitle("${date.format(DateText)} 明細")
        if (holiday != null) {
            Text("${holiday.name} · 國定假日", color = Color(0xFFB32656), fontWeight = FontWeight.SemiBold)
        } else if (date.isWeekend()) {
            Text("週末假日", color = Color(0xFFB32656), fontWeight = FontWeight.SemiBold)
        }
        restrictions.forEach {
            val reason = it.reason.ifBlank { "未填原因" }
            Text("${it.part.title}：$reason", color = Color(0xFFBA1A1A), fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun HolidayEditor(viewModel: LeaveViewModel) {
    val holidays by viewModel.holidays.collectAsState()
    var date by remember { mutableStateOf(LocalDate.now()) }
    var name by remember { mutableStateOf("") }

    ElevatedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("自訂國定假日", fontSize = 20.sp, fontWeight = FontWeight.Bold)
            DateButton("假日日期", date, onDateChange = { date = it })
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("假日名稱") },
                modifier = Modifier.fillMaxWidth(),
            )
            Button(
                onClick = {
                    viewModel.saveHoliday(
                        HolidayEntity(
                            date = date,
                            name = name.ifBlank { "自訂假日" },
                            isNationalHoliday = true,
                            isUserDefined = true,
                        )
                    )
                    name = ""
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("新增或更新假日") }
            holidays.filter { it.isUserDefined }.take(5).forEach { holiday ->
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text("${holiday.date.format(DateText)} ${holiday.name}", modifier = Modifier.weight(1f))
                    IconButton(onClick = { viewModel.deleteHoliday(holiday) }) {
                        Icon(Icons.Default.Delete, contentDescription = "刪除假日")
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun AddLeaveScreen(
    viewModel: LeaveViewModel,
    editingRequest: LeaveRequestEntity?,
    onFinished: () -> Unit,
) {
    val year by viewModel.selectedYear.collectAsState()
    val editKey = editingRequest?.id ?: 0L
    var startDate by remember(editKey) { mutableStateOf(editingRequest?.date ?: nextWeekday(LocalDate.now())) }
    var endDate by remember(editKey) { mutableStateOf(editingRequest?.date ?: nextWeekday(LocalDate.now())) }
    var leaveType by remember(editKey) { mutableStateOf(editingRequest?.leaveType ?: LeaveType.ANNUAL) }
    var dayPart by remember(editKey) { mutableStateOf(editingRequest?.dayPart ?: DayPart.FULL_DAY) }
    var customHours by remember(editKey) { mutableStateOf((editingRequest?.hours ?: 1).toString()) }
    var source by remember(editKey) { mutableStateOf(editingRequest?.deductionSource ?: DeductionSource.ANNUAL) }
    var note by remember(editKey) { mutableStateOf(editingRequest?.note ?: "") }
    val sourceOptions = if (leaveType == LeaveType.ANNUAL) {
        listOf(DeductionSource.ANNUAL, DeductionSource.COMP_TIME)
    } else {
        listOf(DeductionSource.LEAVE_TYPE)
    }
    val hours = if (dayPart == DayPart.CUSTOM) customHours.toIntOrNull() ?: 1 else dayPart.hours
    val rangeError = editingRequest == null && endDate.isBefore(startDate)
    val workdayCount = if (rangeError) 0 else countWeekdays(startDate, endDate)
    val conflictText = when {
        editingRequest != null && startDate.isWeekend() -> "週六週日不可選為請假日期"
        rangeError -> "結束日期不可早於開始日期"
        editingRequest == null && workdayCount == 0 -> "範圍內沒有可請假的工作日"
        hours !in 1..8 -> "時數必須介於 1 到 8 小時"
        else -> null
    }

    LaunchedEffect(leaveType, editKey) {
        if (source !in sourceOptions) source = sourceOptions.first()
    }

    ScreenColumn {
        item {
            PageTitle(
                if (editingRequest == null) "新增請假" else "編輯請假",
                "選日期、假別、時數與扣抵來源",
            )
        }
        if (editingRequest == null) {
            item { DateButton("開始日期", startDate, weekdayOnly = true, onDateChange = { startDate = it }) }
            item { DateButton("結束日期", endDate, weekdayOnly = true, onDateChange = { endDate = it }) }
            item { Text("將新增 $workdayCount 個工作日請假紀錄，週六週日會自動跳過", color = Color(0xFF607080)) }
        } else {
            item { DateButton("請假日期", startDate, weekdayOnly = true, onDateChange = { startDate = it; endDate = it }) }
        }
        item {
            EnumDropdown("假別", leaveType, LeaveType.entries.filterNot { it == LeaveType.COMP_TIME }, { it.title }) { leaveType = it }
        }
        item {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                DayPart.entries.forEach {
                    FilterChip(selected = dayPart == it, onClick = { dayPart = it }, label = { Text(it.title) })
                }
            }
        }
        if (dayPart == DayPart.CUSTOM) {
            item {
                    OutlinedTextField(
                        value = customHours,
                    onValueChange = { customHours = it.filter { char -> char.isDigit() }.take(1) },
                    label = { Text("自訂時數，1 小時為單位") },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
        item {
            EnumDropdown(
                "扣抵來源",
                source,
                sourceOptions,
                { it.title },
            ) { source = it }
        }
        item {
            OutlinedTextField(value = note, onValueChange = { note = it }, label = { Text("備註") }, modifier = Modifier.fillMaxWidth())
        }
        conflictText?.let {
            item { Text(it, color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.SemiBold) }
        }
        item {
            Button(
                enabled = conflictText == null,
                onClick = {
                    val request = LeaveRequestEntity(
                        id = editingRequest?.id ?: 0,
                        year = year,
                        date = startDate,
                        leaveType = leaveType,
                        dayPart = dayPart,
                        hours = hours,
                        deductionSource = source,
                        note = note,
                    )
                    if (editingRequest == null) {
                        viewModel.addLeaveRequestRange(startDate, endDate, request)
                    } else {
                        viewModel.updateLeaveRequest(request)
                    }
                    onFinished()
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (editingRequest == null) "新增請假範圍" else "更新請假紀錄")
            }
        }
    }
}

@Composable
private fun CompTimeScreen(viewModel: LeaveViewModel) {
    val credits by viewModel.compCredits.collectAsState()
    var editingCredit by remember { mutableStateOf<CompTimeCreditEntity?>(null) }
    val editKey = editingCredit?.id ?: 0L
    var overtimeDate by remember(editKey) { mutableStateOf(editingCredit?.overtimeDate ?: LocalDate.now()) }
    var expiresAt by remember(editKey) { mutableStateOf(editingCredit?.expiresAt ?: LocalDate.now().plusMonths(6)) }
    var hours by remember(editKey) { mutableStateOf((editingCredit?.hours ?: 1).toString()) }
    var note by remember(editKey) { mutableStateOf(editingCredit?.note ?: "") }
    val parsedHours = hours.toIntOrNull() ?: 0
    val usedHours = editingCredit?.usedHours ?: 0
    val hourError = parsedHours <= 0 || parsedHours < usedHours

    ScreenColumn {
        item { PageTitle("加班補休", if (editingCredit == null) "新增補休時數並追蹤到期日" else "編輯補休批次") }
        item { DateButton("加班日期", overtimeDate, onDateChange = { overtimeDate = it }) }
        item { DateButton("到期日", expiresAt, onDateChange = { expiresAt = it }) }
        item {
            OutlinedTextField(
                value = hours,
                onValueChange = { hours = it.filter { char -> char.isDigit() }.take(2) },
                label = { Text("補休時數") },
                modifier = Modifier.fillMaxWidth(),
            )
        }
        item { OutlinedTextField(value = note, onValueChange = { note = it }, label = { Text("備註") }, modifier = Modifier.fillMaxWidth()) }
        if (hourError) {
            item {
                Text(
                    if (parsedHours <= 0) "補休時數必須大於 0" else "補休總時數不可小於已使用 $usedHours 小時",
                    color = MaterialTheme.colorScheme.error,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
        item {
            Button(
                enabled = !hourError,
                onClick = {
                    val credit = CompTimeCreditEntity(
                        id = editingCredit?.id ?: 0,
                        overtimeDate = overtimeDate,
                        expiresAt = expiresAt,
                        hours = parsedHours,
                        usedHours = editingCredit?.usedHours ?: 0,
                        note = note,
                    )
                    if (editingCredit == null) {
                        viewModel.addCompTimeCredit(credit)
                    } else {
                        viewModel.updateCompTimeCredit(credit)
                    }
                    editingCredit = null
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (editingCredit == null) "新增補休" else "更新補休") }
        }
        if (editingCredit != null) {
            item {
                OutlinedButton(
                    onClick = { editingCredit = null },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("取消編輯") }
            }
        }
        item { SectionTitle("補休批次") }
        if (credits.isEmpty()) item { EmptyCard("尚未新增加班補休") }
        items(credits) { credit ->
            CompTimeCreditRow(
                credit = credit,
                onEdit = { editingCredit = credit },
                onDelete = { viewModel.deleteCompTimeCredit(credit) },
            )
        }
    }
}

@Composable
private fun CompTimeCreditRow(
    credit: CompTimeCreditEntity,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
) {
    var confirmDelete by remember { mutableStateOf(false) }

    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text("刪除補休批次") },
            text = { Text("確定要刪除 ${credit.overtimeDate.format(DateText)} 的 ${credit.hours} 小時補休嗎？") },
            confirmButton = {
                TextButton(
                    onClick = {
                        confirmDelete = false
                        onDelete()
                    },
                ) { Text("刪除") }
            },
            dismissButton = {
                TextButton(onClick = { confirmDelete = false }) { Text("取消") }
            },
        )
    }

    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("剩餘 ${credit.hours - credit.usedHours} 小時 / 總額 ${credit.hours} 小時", fontWeight = FontWeight.Bold)
                Text("加班 ${credit.overtimeDate.format(DateText)} · 到期 ${credit.expiresAt.format(DateText)}", color = Color(0xFF607080))
                if (credit.note.isNotBlank()) Text(credit.note, color = Color(0xFF607080))
            }
            IconButton(onClick = onEdit) {
                Icon(Icons.Default.Edit, contentDescription = "編輯補休")
            }
            IconButton(onClick = { confirmDelete = true }) {
                Icon(Icons.Default.Delete, contentDescription = "刪除補休")
            }
        }
    }
}

@Composable
private fun RestrictionScreen(viewModel: LeaveViewModel) {
    val restrictions by viewModel.restrictions.collectAsState()
    var startDate by remember { mutableStateOf(LocalDate.now()) }
    var endDate by remember { mutableStateOf(LocalDate.now()) }
    var part by remember { mutableStateOf(RestrictionPart.FULL_DAY) }
    var reason by remember { mutableStateOf("") }
    val rangeError = endDate.isBefore(startDate)
    val daysInRange = if (rangeError) 0 else java.time.temporal.ChronoUnit.DAYS.between(startDate, endDate).toInt() + 1

    ScreenColumn {
        item { PageTitle("不可休設定", "設定整天、上午或下午不可休") }
        item { DateButton("開始日期", startDate, onDateChange = { startDate = it }) }
        item { DateButton("結束日期", endDate, onDateChange = { endDate = it }) }
        item { EnumDropdown("限制時段", part, RestrictionPart.entries, { it.title }) { part = it } }
        item { OutlinedTextField(value = reason, onValueChange = { reason = it }, label = { Text("原因") }, modifier = Modifier.fillMaxWidth()) }
        if (rangeError) {
            item { Text("結束日期不可早於開始日期", color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.SemiBold) }
        } else {
            item { Text("將新增 $daysInRange 天不可休設定", color = Color(0xFF607080)) }
        }
        item {
            Button(
                onClick = {
                    viewModel.addRestrictionRange(startDate, endDate, part, reason)
                },
                enabled = !rangeError,
                modifier = Modifier.fillMaxWidth(),
            ) { Text("新增不可休範圍") }
        }
        item { SectionTitle("目前限制") }
        if (restrictions.isEmpty()) item { EmptyCard("尚未設定不可休日期") }
        items(restrictions) {
            Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("${it.date.format(DateText)} · ${it.part.title}", fontWeight = FontWeight.Bold)
                        if (it.reason.isNotBlank()) Text(it.reason, color = Color(0xFF607080))
                    }
                    IconButton(onClick = { viewModel.deleteRestriction(it) }) {
                        Icon(Icons.Default.Delete, contentDescription = "刪除")
                    }
                }
            }
        }
    }
}

@Composable
private fun SettingsScreen(viewModel: LeaveViewModel) {
    val year by viewModel.selectedYear.collectAsState()
    val leaveYear by viewModel.leaveYear.collectAsState()
    var annualDays by remember(leaveYear.annualLeaveDays) { mutableStateOf(leaveYear.annualLeaveDays.toString()) }

    ScreenColumn {
        item { PageTitle("年度設定", "自訂年資增加後的特休總天數") }
        item { YearSelector(year, onPrevious = { viewModel.selectYear(year - 1) }, onNext = { viewModel.selectYear(year + 1) }) }
        item {
            ElevatedCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("$year 年特休總天數", fontSize = 22.sp, fontWeight = FontWeight.Bold)
                    OutlinedTextField(
                        value = annualDays,
                        onValueChange = { annualDays = it.filter { char -> char.isDigit() || char == '.' }.take(5) },
                        label = { Text("特休天數") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Text("系統會以 1 天 = 8 小時換算，目前為 ${(annualDays.toDoubleOrNull() ?: 0.0) * 8} 小時")
                    Button(
                        onClick = { viewModel.saveAnnualDays(annualDays.toDoubleOrNull() ?: leaveYear.annualLeaveDays) },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("儲存年度特休") }
                }
            }
        }
    }
}

@Composable
private fun DateButton(label: String, date: LocalDate, weekdayOnly: Boolean = false, onDateChange: (LocalDate) -> Unit) {
    val context = LocalContext.current
    OutlinedButton(
        onClick = {
            DatePickerDialog(
                context,
                { _, y, m, d ->
                    val picked = LocalDate.of(y, m + 1, d)
                    onDateChange(if (weekdayOnly) nextWeekday(picked) else picked)
                },
                date.year,
                date.monthValue - 1,
                date.dayOfMonth,
            ).show()
        },
        modifier = Modifier.fillMaxWidth(),
    ) {
        Icon(Icons.Default.CalendarMonth, contentDescription = null)
        Spacer(Modifier.width(8.dp))
        Text("$label：${date.format(DateText)}")
    }
}

private fun nextWeekday(date: LocalDate): LocalDate {
    var cursor = date
    while (cursor.isWeekend()) cursor = cursor.plusDays(1)
    return cursor
}

private fun countWeekdays(startDate: LocalDate, endDate: LocalDate): Int {
    if (endDate.isBefore(startDate)) return 0
    var cursor = startDate
    var count = 0
    while (!cursor.isAfter(endDate)) {
        if (!cursor.isWeekend()) count += 1
        cursor = cursor.plusDays(1)
    }
    return count
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun <T> EnumDropdown(
    label: String,
    selected: T,
    options: List<T>,
    title: (T) -> String,
    onSelected: (T) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded }) {
        OutlinedTextField(
            value = title(selected),
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            modifier = Modifier.menuAnchor().fillMaxWidth(),
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(title(option)) },
                    onClick = {
                        onSelected(option)
                        expanded = false
                    },
                )
            }
        }
    }
}
