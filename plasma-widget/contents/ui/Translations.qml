/*
    SPDX-FileCopyrightText: 2025 izll
    SPDX-License-Identifier: GPL-3.0-or-later
*/

import QtQuick

QtObject {
    id: translations

    property string currentLanguage: "system"
    property int version: 0

    onCurrentLanguageChanged: {
        version++;
    }

    readonly property var strings: ({
        "en_US": {
            "Claude Usage": "Claude Usage",
            "Session (5hr)": "Session (5hr)",
            "Weekly (7day)": "Weekly (7day)",
            "By Model (Weekly)": "By Model (Weekly)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Resets at:",
            "Resets:": "Resets:",
            "Updated:": "Updated:",
            "Loading...": "Loading...",
            "Refresh": "Refresh",
            "Not logged in": "Not logged in",
            "Token expired": "Token expired",
            "API error": "API error",
            "Run 'claude' to log in": "Run 'claude' to log in",
            "No model breakdown available": "No model breakdown available",
            "Language:": "Language:",
            "System default": "System default",
            "d": "d",
            "h": "h",
            "m": "m",
            "Refresh interval:": "Refresh interval:",
            "minutes": "minutes"
        },
        "hu_HU": {
            "Claude Usage": "Claude használat",
            "Session (5hr)": "Munkamenet (5 óra)",
            "Weekly (7day)": "Heti (7 nap)",
            "By Model (Weekly)": "Modell szerint (Heti)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Visszaáll:",
            "Resets:": "Visszaáll:",
            "Updated:": "Frissítve:",
            "Loading...": "Betöltés...",
            "Refresh": "Frissítés",
            "Not logged in": "Nincs bejelentkezve",
            "Token expired": "Lejárt token",
            "API error": "API hiba",
            "Run 'claude' to log in": "Futtasd a 'claude' parancsot",
            "No model breakdown available": "Nincs modell bontás",
            "Language:": "Nyelv:",
            "System default": "Rendszer alapértelmezett",
            "d": "n",
            "h": "ó",
            "m": "p",
            "Refresh interval:": "Frissítési gyakoriság:",
            "minutes": "perc"
        },
        "de_DE": {
            "Claude Usage": "Claude Nutzung",
            "Session (5hr)": "Sitzung (5 Std)",
            "Weekly (7day)": "Wöchentlich (7 Tage)",
            "By Model (Weekly)": "Nach Modell (Wöchentlich)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Setzt zurück um:",
            "Resets:": "Setzt zurück:",
            "Updated:": "Aktualisiert:",
            "Loading...": "Laden...",
            "Refresh": "Aktualisieren",
            "Not logged in": "Nicht angemeldet",
            "Token expired": "Token abgelaufen",
            "API error": "API-Fehler",
            "Run 'claude' to log in": "Führen Sie 'claude' aus",
            "No model breakdown available": "Keine Modellaufschlüsselung verfügbar",
            "Language:": "Sprache:",
            "System default": "Systemstandard",
            "d": "T",
            "h": "Std",
            "m": "Min",
            "Refresh interval:": "Aktualisierungsintervall:",
            "minutes": "Minuten"
        },
        "fr_FR": {
            "Claude Usage": "Utilisation Claude",
            "Session (5hr)": "Session (5h)",
            "Weekly (7day)": "Hebdomadaire (7j)",
            "By Model (Weekly)": "Par modèle (Hebdo)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Réinitialisation à:",
            "Resets:": "Réinitialisation:",
            "Updated:": "Mis à jour:",
            "Loading...": "Chargement...",
            "Refresh": "Actualiser",
            "Not logged in": "Non connecté",
            "Token expired": "Token expiré",
            "API error": "Erreur API",
            "Run 'claude' to log in": "Exécutez 'claude' pour vous connecter",
            "No model breakdown available": "Pas de détail par modèle",
            "Language:": "Langue:",
            "System default": "Système par défaut",
            "d": "j",
            "h": "h",
            "m": "min",
            "Refresh interval:": "Intervalle de rafraîchissement:",
            "minutes": "minutes"
        },
        "es_ES": {
            "Claude Usage": "Uso de Claude",
            "Session (5hr)": "Sesión (5h)",
            "Weekly (7day)": "Semanal (7 días)",
            "By Model (Weekly)": "Por modelo (Semanal)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Se reinicia a las:",
            "Resets:": "Se reinicia:",
            "Updated:": "Actualizado:",
            "Loading...": "Cargando...",
            "Refresh": "Actualizar",
            "Not logged in": "No conectado",
            "Token expired": "Token expirado",
            "API error": "Error de API",
            "Run 'claude' to log in": "Ejecuta 'claude' para iniciar sesión",
            "No model breakdown available": "Sin desglose por modelo",
            "Language:": "Idioma:",
            "System default": "Predeterminado del sistema",
            "d": "d",
            "h": "h",
            "m": "min",
            "Refresh interval:": "Intervalo de actualización:",
            "minutes": "minutos"
        },
        "it_IT": {
            "Claude Usage": "Utilizzo Claude",
            "Session (5hr)": "Sessione (5h)",
            "Weekly (7day)": "Settimanale (7gg)",
            "By Model (Weekly)": "Per modello (Settimanale)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Si azzera alle:",
            "Resets:": "Si azzera:",
            "Updated:": "Aggiornato:",
            "Loading...": "Caricamento...",
            "Refresh": "Aggiorna",
            "Not logged in": "Non connesso",
            "Token expired": "Token scaduto",
            "API error": "Errore API",
            "Run 'claude' to log in": "Esegui 'claude' per accedere",
            "No model breakdown available": "Nessun dettaglio per modello",
            "Language:": "Lingua:",
            "System default": "Predefinito di sistema",
            "d": "g",
            "h": "h",
            "m": "min",
            "Refresh interval:": "Intervallo di aggiornamento:",
            "minutes": "minuti"
        },
        "pt_BR": {
            "Claude Usage": "Uso do Claude",
            "Session (5hr)": "Sessão (5h)",
            "Weekly (7day)": "Semanal (7 dias)",
            "By Model (Weekly)": "Por modelo (Semanal)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Reinicia às:",
            "Resets:": "Reinicia:",
            "Updated:": "Atualizado:",
            "Loading...": "Carregando...",
            "Refresh": "Atualizar",
            "Not logged in": "Não conectado",
            "Token expired": "Token expirado",
            "API error": "Erro de API",
            "Run 'claude' to log in": "Execute 'claude' para fazer login",
            "No model breakdown available": "Sem detalhamento por modelo",
            "Language:": "Idioma:",
            "System default": "Padrão do sistema",
            "d": "d",
            "h": "h",
            "m": "min",
            "Refresh interval:": "Intervalo de atualização:",
            "minutes": "minutos"
        },
        "ru_RU": {
            "Claude Usage": "Использование Claude",
            "Session (5hr)": "Сессия (5ч)",
            "Weekly (7day)": "Неделя (7 дней)",
            "By Model (Weekly)": "По модели (Неделя)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Сброс в:",
            "Resets:": "Сброс:",
            "Updated:": "Обновлено:",
            "Loading...": "Загрузка...",
            "Refresh": "Обновить",
            "Not logged in": "Не авторизован",
            "Token expired": "Токен истёк",
            "API error": "Ошибка API",
            "Run 'claude' to log in": "Запустите 'claude' для входа",
            "No model breakdown available": "Нет данных по моделям",
            "Language:": "Язык:",
            "System default": "По умолчанию системы",
            "d": "д",
            "h": "ч",
            "m": "мин",
            "Refresh interval:": "Интервал обновления:",
            "minutes": "минут"
        },
        "pl_PL": {
            "Claude Usage": "Użycie Claude",
            "Session (5hr)": "Sesja (5h)",
            "Weekly (7day)": "Tygodniowo (7 dni)",
            "By Model (Weekly)": "Wg modelu (Tygodniowo)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Resetuje o:",
            "Resets:": "Resetuje:",
            "Updated:": "Zaktualizowano:",
            "Loading...": "Ładowanie...",
            "Refresh": "Odśwież",
            "Not logged in": "Nie zalogowany",
            "Token expired": "Token wygasł",
            "API error": "Błąd API",
            "Run 'claude' to log in": "Uruchom 'claude' aby się zalogować",
            "No model breakdown available": "Brak podziału na modele",
            "Language:": "Język:",
            "System default": "Domyślny systemowy",
            "d": "d",
            "h": "g",
            "m": "min",
            "Refresh interval:": "Częstotliwość odświeżania:",
            "minutes": "minut"
        },
        "nl_NL": {
            "Claude Usage": "Claude Gebruik",
            "Session (5hr)": "Sessie (5u)",
            "Weekly (7day)": "Wekelijks (7 dagen)",
            "By Model (Weekly)": "Per model (Wekelijks)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Reset om:",
            "Resets:": "Reset:",
            "Updated:": "Bijgewerkt:",
            "Loading...": "Laden...",
            "Refresh": "Vernieuwen",
            "Not logged in": "Niet ingelogd",
            "Token expired": "Token verlopen",
            "API error": "API-fout",
            "Run 'claude' to log in": "Voer 'claude' uit om in te loggen",
            "No model breakdown available": "Geen modeluitsplitsing beschikbaar",
            "Language:": "Taal:",
            "System default": "Systeemstandaard",
            "d": "d",
            "h": "u",
            "m": "min",
            "Refresh interval:": "Vernieuwingsinterval:",
            "minutes": "minuten"
        },
        "tr_TR": {
            "Claude Usage": "Claude Kullanımı",
            "Session (5hr)": "Oturum (5sa)",
            "Weekly (7day)": "Haftalık (7 gün)",
            "By Model (Weekly)": "Modele göre (Haftalık)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "Sıfırlanma:",
            "Resets:": "Sıfırlanma:",
            "Updated:": "Güncellendi:",
            "Loading...": "Yükleniyor...",
            "Refresh": "Yenile",
            "Not logged in": "Giriş yapılmadı",
            "Token expired": "Token süresi doldu",
            "API error": "API hatası",
            "Run 'claude' to log in": "Giriş için 'claude' çalıştırın",
            "No model breakdown available": "Model dağılımı mevcut değil",
            "Language:": "Dil:",
            "System default": "Sistem varsayılanı",
            "d": "g",
            "h": "sa",
            "m": "dk",
            "Refresh interval:": "Yenileme aralığı:",
            "minutes": "dakika"
        },
        "ja_JP": {
            "Claude Usage": "Claude 使用状況",
            "Session (5hr)": "セッション (5時間)",
            "Weekly (7day)": "週間 (7日)",
            "By Model (Weekly)": "モデル別 (週間)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "リセット:",
            "Resets:": "リセット:",
            "Updated:": "更新:",
            "Loading...": "読み込み中...",
            "Refresh": "更新",
            "Not logged in": "未ログイン",
            "Token expired": "トークン期限切れ",
            "API error": "APIエラー",
            "Run 'claude' to log in": "'claude'を実行してログイン",
            "No model breakdown available": "モデル別データなし",
            "Language:": "言語:",
            "System default": "システムデフォルト",
            "d": "日",
            "h": "時",
            "m": "分",
            "Refresh interval:": "更新間隔:",
            "minutes": "分"
        },
        "ko_KR": {
            "Claude Usage": "Claude 사용량",
            "Session (5hr)": "세션 (5시간)",
            "Weekly (7day)": "주간 (7일)",
            "By Model (Weekly)": "모델별 (주간)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "초기화:",
            "Resets:": "초기화:",
            "Updated:": "업데이트:",
            "Loading...": "로딩 중...",
            "Refresh": "새로고침",
            "Not logged in": "로그인 안됨",
            "Token expired": "토큰 만료",
            "API error": "API 오류",
            "Run 'claude' to log in": "'claude'를 실행하여 로그인",
            "No model breakdown available": "모델별 데이터 없음",
            "Language:": "언어:",
            "System default": "시스템 기본값",
            "d": "일",
            "h": "시",
            "m": "분",
            "Refresh interval:": "새로고침 간격:",
            "minutes": "분"
        },
        "zh_CN": {
            "Claude Usage": "Claude 使用情况",
            "Session (5hr)": "会话 (5小时)",
            "Weekly (7day)": "每周 (7天)",
            "By Model (Weekly)": "按模型 (每周)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "重置时间:",
            "Resets:": "重置:",
            "Updated:": "更新时间:",
            "Loading...": "加载中...",
            "Refresh": "刷新",
            "Not logged in": "未登录",
            "Token expired": "令牌已过期",
            "API error": "API 错误",
            "Run 'claude' to log in": "运行 'claude' 登录",
            "No model breakdown available": "无模型明细",
            "Language:": "语言:",
            "System default": "系统默认",
            "d": "天",
            "h": "时",
            "m": "分",
            "Refresh interval:": "刷新间隔:",
            "minutes": "分钟"
        },
        "zh_TW": {
            "Claude Usage": "Claude 使用狀況",
            "Session (5hr)": "工作階段 (5小時)",
            "Weekly (7day)": "每週 (7天)",
            "By Model (Weekly)": "依模型 (每週)",
            "Sonnet": "Sonnet",
            "Opus": "Opus",
            "Resets at:": "重置時間:",
            "Resets:": "重置:",
            "Updated:": "更新時間:",
            "Loading...": "載入中...",
            "Refresh": "重新整理",
            "Not logged in": "未登入",
            "Token expired": "權杖已過期",
            "API error": "API 錯誤",
            "Run 'claude' to log in": "執行 'claude' 登入",
            "No model breakdown available": "無模型明細",
            "Language:": "語言:",
            "System default": "系統預設",
            "d": "天",
            "h": "時",
            "m": "分",
            "Refresh interval:": "重新整理間隔:",
            "minutes": "分鐘"
        }
    })

    readonly property string systemLanguage: {
        let locale = Qt.locale().name;
        return locale;
    }

    function getEffectiveLanguage() {
        if (currentLanguage === "system") {
            let sysLang = systemLanguage;
            if (strings[sysLang]) {
                return sysLang;
            }
            let langCode = sysLang.split("_")[0];
            for (let key in strings) {
                if (key.startsWith(langCode + "_")) {
                    return key;
                }
            }
            return "en_US";
        }
        return currentLanguage;
    }

    function tr(text) {
        let v = version;
        let lang = getEffectiveLanguage();

        if (strings[lang] && strings[lang][text]) {
            return strings[lang][text];
        }
        if (strings["en_US"] && strings["en_US"][text]) {
            return strings["en_US"][text];
        }
        return text;
    }
}
