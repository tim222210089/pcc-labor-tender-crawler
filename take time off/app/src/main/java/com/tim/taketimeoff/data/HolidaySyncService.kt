package com.tim.taketimeoff.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate

class HolidaySyncService(
    private val client: OkHttpClient = OkHttpClient(),
) {
    suspend fun fetchTaiwanHolidays(year: Int): List<HolidayEntity> = withContext(Dispatchers.IO) {
        val errors = mutableListOf<Throwable>()
        HolidaySources.forEach { url ->
            try {
                val request = Request.Builder().url(url).build()
                client.newCall(request).execute().use { response ->
                    if (!response.isSuccessful) error("HTTP ${response.code}")
                    val body = response.body?.string().orEmpty()
                    val parsed = parseHolidayJson(body, year)
                    if (parsed.isNotEmpty()) return@withContext parsed
                }
            } catch (error: Throwable) {
                errors.add(error)
            }
        }
        throw IllegalStateException("Holiday sync failed", errors.lastOrNull())
    }

    private fun parseHolidayJson(body: String, year: Int): List<HolidayEntity> {
        val root = body.trim()
        val rows = if (root.startsWith("[")) collectObjects(JSONArray(root)) else collectObjects(JSONObject(root))
        return rows.mapNotNull { row ->
            val date = row.findString("date", "Date", "日期", "西元日期")?.toHolidayDate() ?: return@mapNotNull null
            if (date.year != year) return@mapNotNull null
            if (!row.findString("isholiday", "isHoliday", "是否放假") .isHolidayValue()) return@mapNotNull null
            val name = row.findString("name", "Name", "節日", "中文欄位", "紀念日節日名稱")
                ?.takeIf { it.isNotBlank() }
                ?: row.findString("description", "Description", "備註", "放假說明")
                ?.takeIf { it.isNotBlank() }
                ?: return@mapNotNull null
            if (name == "星期六" || name == "星期日" || name == "週六" || name == "週日") return@mapNotNull null
            HolidayEntity(
                date = date,
                name = name,
                isNationalHoliday = true,
                isUserDefined = false,
            )
        }.distinctBy { it.date }
    }

    private fun collectObjects(value: Any?): List<JSONObject> {
        val result = mutableListOf<JSONObject>()
        when (value) {
            is JSONObject -> {
                val keys = value.keys()
                var hasDateLikeKey = false
                while (keys.hasNext()) {
                    val key = keys.next()
                    if (key.equals("date", true) || key == "日期" || key == "西元日期") hasDateLikeKey = true
                    result.addAll(collectObjects(value.opt(key)))
                }
                if (hasDateLikeKey) result.add(value)
            }
            is JSONArray -> {
                for (index in 0 until value.length()) {
                    result.addAll(collectObjects(value.opt(index)))
                }
            }
        }
        return result
    }

    private fun JSONObject.findString(vararg keys: String): String? {
        keys.forEach { key ->
            if (has(key)) return optString(key).trim()
        }
        return null
    }

    private fun String?.isHolidayValue(): Boolean {
        val normalized = this?.trim()?.lowercase().orEmpty()
        return normalized == "true" || normalized == "2" || normalized == "是" || normalized == "yes" || normalized == "y"
    }

    private fun String.toHolidayDate(): LocalDate? {
        val digits = filter(Char::isDigit)
        return when (digits.length) {
            8 -> LocalDate.of(digits.substring(0, 4).toInt(), digits.substring(4, 6).toInt(), digits.substring(6, 8).toInt())
            7 -> LocalDate.of(digits.substring(0, 3).toInt() + 1911, digits.substring(3, 5).toInt(), digits.substring(5, 7).toInt())
            else -> runCatching { LocalDate.parse(this) }.getOrNull()
        }
    }

    companion object {
        private val HolidaySources = listOf(
            "https://data.ntpc.gov.tw/api/v1/rest/datastore/382000000A-000077-002",
        )
    }
}
