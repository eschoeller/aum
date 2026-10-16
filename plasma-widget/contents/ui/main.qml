import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasma5support as Plasma5Support

PlasmoidItem {
    id: root

    // Translations
    Translations {
        id: i18n
        currentLanguage: Plasmoid.configuration.language || "system"
    }

    property real sessionUsagePercent: 0
    property real weeklyUsagePercent: 0
    property real sonnetWeeklyPercent: 0
    property real opusWeeklyPercent: 0
    property real fableWeeklyPercent: 0
    property string lastUpdate: ""
    property string planName: ""
    property string sessionReset: ""
    property string weeklyReset: ""
    property string errorMsg: ""
    property string accessToken: ""
    property bool isLoading: false
    property var sessionResetTime: null
    property var weeklyResetTime: null

    readonly property string usageApiUrl: "https://api.anthropic.com/api/oauth/usage"

    // Data source for reading credentials file
    Plasma5Support.DataSource {
        id: fileReader
        engine: "executable"
        connectedSources: []

        onNewData: function(sourceName, data) {
            var stdout = data["stdout"] || ""
            disconnectSource(sourceName)

            console.log("Claude Usage: Got credentials, length:", stdout.length)

            if (stdout.length > 10) {
                try {
                    var creds = JSON.parse(stdout)
                    var oauth = creds.claudeAiOauth || {}
                    root.accessToken = oauth.accessToken || ""

                    // Get plan name from tier
                    var tier = oauth.rateLimitTier || "default_claude_pro"
                    var planMap = {
                        "default_claude_pro": "Pro",
                        "default_claude_max_5x": "Max 5x",
                        "default_claude_max_20x": "Max 20x"
                    }
                    root.planName = planMap[tier] || tier

                    console.log("Claude Usage: Token found, plan:", root.planName)

                    if (root.accessToken) {
                        fetchUsageFromApi()
                    } else {
                        root.errorMsg = i18n.tr("Not logged in")
                        root.isLoading = false
                    }
                } catch (e) {
                    console.log("Claude Usage: Failed to parse credentials:", e)
                    root.errorMsg = "Not logged in"
                    root.isLoading = false
                }
            } else {
                console.log("Claude Usage: No credentials file found")
                root.errorMsg = "Not logged in"
                root.isLoading = false
            }
        }
    }

    function loadCredentials() {
        root.isLoading = true
        root.errorMsg = ""
        // Use $HOME environment variable
        fileReader.connectSource("cat $HOME/.claude/.credentials.json 2>/dev/null")
    }

    function fetchUsageFromApi() {
        var xhr = new XMLHttpRequest()
        xhr.open("GET", usageApiUrl)
        xhr.setRequestHeader("Authorization", "Bearer " + root.accessToken)
        xhr.setRequestHeader("Content-Type", "application/json")
        xhr.setRequestHeader("anthropic-beta", "oauth-2025-04-20")

        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                root.isLoading = false

                if (xhr.status === 200) {
                    try {
                        var data = JSON.parse(xhr.responseText)

                        // Parse the limits array (current API) with
                        // fallback to top-level keys (legacy API).
                        var limits = data.limits || []
                        root.sessionUsagePercent = 0
                        root.weeklyUsagePercent = 0
                        root.sonnetWeeklyPercent = 0
                        root.opusWeeklyPercent = 0
                        root.fableWeeklyPercent = 0

                        if (limits.length > 0) {
                            for (var i = 0; i < limits.length; i++) {
                                var lim = limits[i]
                                var pct = lim.percent || 0
                                if (lim.kind === "session") {
                                    root.sessionUsagePercent = pct
                                } else if (lim.kind === "weekly_all") {
                                    root.weeklyUsagePercent = pct
                                } else if (lim.kind === "weekly_scoped" && lim.scope && lim.scope.model) {
                                    var modelName = (lim.scope.model.display_name || "").toLowerCase()
                                    if (modelName === "fable") root.fableWeeklyPercent = pct
                                    else if (modelName === "sonnet") root.sonnetWeeklyPercent = pct
                                    else if (modelName === "opus") root.opusWeeklyPercent = pct
                                }
                            }
                        } else {
                            var fiveHour = data.five_hour || {}
                            var sevenDay = data.seven_day || {}
                            root.sessionUsagePercent = fiveHour.utilization || 0
                            root.weeklyUsagePercent = sevenDay.utilization || 0
                        }

                        if (limits.length > 0) {
                            for (var j = 0; j < limits.length; j++) {
                                if (limits[j].kind === "session" && limits[j].resets_at) {
                                    root.sessionResetTime = new Date(limits[j].resets_at)
                                    root.sessionReset = Qt.formatTime(root.sessionResetTime, "hh:mm")
                                } else if (limits[j].kind === "weekly_all" && limits[j].resets_at) {
                                    root.weeklyResetTime = new Date(limits[j].resets_at)
                                    root.weeklyReset = Qt.formatDateTime(root.weeklyResetTime, "MMM d, hh:mm")
                                }
                            }
                        } else {
                            var fiveHour = data.five_hour || {}
                            var sevenDay = data.seven_day || {}
                            if (fiveHour.resets_at) {
                                root.sessionResetTime = new Date(fiveHour.resets_at)
                                root.sessionReset = Qt.formatTime(root.sessionResetTime, "hh:mm")
                            }
                            if (sevenDay.resets_at) {
                                root.weeklyResetTime = new Date(sevenDay.resets_at)
                                root.weeklyReset = Qt.formatDateTime(root.weeklyResetTime, "MMM d, hh:mm")
                            }
                        }

                        root.lastUpdate = Qt.formatTime(new Date(), "hh:mm:ss")
                        root.errorMsg = ""

                        console.log("Claude Usage: API success - session:", root.sessionUsagePercent, "weekly:", root.weeklyUsagePercent, "fable:", root.fableWeeklyPercent, "limits_count:", limits.length)
                    } catch (e) {
                        console.log("Claude Usage: JSON parse error:", e)
                        root.errorMsg = "Parse error"
                    }
                } else if (xhr.status === 401) {
                    root.errorMsg = i18n.tr("Token expired")
                    console.log("Claude Usage: 401 Unauthorized")
                } else {
                    root.errorMsg = i18n.tr("API error") + " (" + xhr.status + ")"
                    console.log("Claude Usage: API error:", xhr.status, xhr.statusText)
                }
            }
        }

        xhr.send()
    }

    function refresh() {
        loadCredentials()
    }

    // Compact representation (panel) - shows both percentages
    compactRepresentation: Item {
        Layout.minimumWidth: usageRow.implicitWidth + Kirigami.Units.largeSpacing * 2
        Layout.minimumHeight: Kirigami.Units.iconSizes.medium
        Layout.preferredWidth: usageRow.implicitWidth + Kirigami.Units.largeSpacing * 2

        MouseArea {
            anchors.fill: parent
            onClicked: root.expanded = !root.expanded
        }

        RowLayout {
            id: usageRow
            anchors.centerIn: parent
            spacing: Kirigami.Units.smallSpacing

            // Error state
            PlasmaComponents.Label {
                visible: root.errorMsg !== ""
                text: "⚠"
                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize
                color: Kirigami.Theme.negativeTextColor
            }

            // Normal state
            Rectangle {
                visible: root.errorMsg === ""
                Layout.preferredWidth: 10
                Layout.preferredHeight: 10
                radius: 5
                color: getUsageColor(root.sessionUsagePercent)
            }

            PlasmaComponents.Label {
                visible: root.errorMsg === ""
                text: Math.round(root.sessionUsagePercent) + "%"
                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize
                font.bold: true
            }

            PlasmaComponents.Label {
                visible: root.errorMsg === ""
                text: "|"
                opacity: 0.5
                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize
            }

            Rectangle {
                visible: root.errorMsg === ""
                Layout.preferredWidth: 10
                Layout.preferredHeight: 10
                radius: 5
                color: getUsageColor(root.weeklyUsagePercent)
            }

            PlasmaComponents.Label {
                visible: root.errorMsg === ""
                text: Math.round(root.weeklyUsagePercent) + "%"
                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize
                font.bold: true
            }

            PlasmaComponents.Label {
                visible: root.errorMsg === "" && root.fableWeeklyPercent > 0
                text: "|"
                opacity: 0.5
                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize
            }

            Rectangle {
                visible: root.errorMsg === "" && root.fableWeeklyPercent > 0
                Layout.preferredWidth: 10
                Layout.preferredHeight: 10
                radius: 5
                color: getUsageColor(root.fableWeeklyPercent)
            }

            PlasmaComponents.Label {
                visible: root.errorMsg === "" && root.fableWeeklyPercent > 0
                text: Math.round(root.fableWeeklyPercent) + "%"
                font.pixelSize: Kirigami.Theme.defaultFont.pixelSize
                font.bold: true
            }

            // Error text
            PlasmaComponents.Label {
                visible: root.errorMsg !== ""
                text: root.errorMsg
                font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                color: Kirigami.Theme.negativeTextColor
            }
        }
    }

    // Full representation (popup)
    fullRepresentation: Item {
        Layout.minimumWidth: Kirigami.Units.gridUnit * 14
        Layout.minimumHeight: Kirigami.Units.gridUnit * 16
        Layout.preferredWidth: Kirigami.Units.gridUnit * 16
        Layout.preferredHeight: Kirigami.Units.gridUnit * 18

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.mediumSpacing

            // Header
            RowLayout {
                Layout.fillWidth: true
                PlasmaComponents.Label {
                    text: i18n.tr("Claude Usage")
                    font.bold: true
                    font.pixelSize: Kirigami.Theme.defaultFont.pixelSize * 1.3
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: planLabel.implicitWidth + Kirigami.Units.smallSpacing * 2
                    Layout.preferredHeight: planLabel.implicitHeight + Kirigami.Units.smallSpacing
                    radius: 3
                    color: Kirigami.Theme.highlightColor
                    PlasmaComponents.Label {
                        id: planLabel
                        anchors.centerIn: parent
                        text: root.planName
                        font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                        color: Kirigami.Theme.highlightedTextColor
                    }
                }
            }

            // Error message
            Rectangle {
                visible: root.errorMsg !== ""
                Layout.fillWidth: true
                Layout.preferredHeight: errorColumn.implicitHeight + Kirigami.Units.largeSpacing
                radius: 5
                color: Kirigami.Theme.negativeBackgroundColor

                ColumnLayout {
                    id: errorColumn
                    anchors.fill: parent
                    anchors.margins: Kirigami.Units.smallSpacing

                    PlasmaComponents.Label {
                        text: "⚠ " + root.errorMsg
                        color: Kirigami.Theme.negativeTextColor
                        font.bold: true
                    }
                    PlasmaComponents.Label {
                        text: i18n.tr("Run 'claude' to log in")
                        font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                        color: Kirigami.Theme.negativeTextColor
                    }
                }
            }

            // Separator
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Kirigami.Theme.disabledTextColor
                opacity: 0.3
            }

            // Session Usage
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                RowLayout {
                    Layout.fillWidth: true
                    PlasmaComponents.Label {
                        text: i18n.tr("Session (5hr)")
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    PlasmaComponents.Label {
                        text: root.sessionUsagePercent.toFixed(1) + "%"
                        color: getUsageColor(root.sessionUsagePercent)
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 10
                    radius: 5
                    color: Kirigami.Theme.backgroundColor
                    border.color: Kirigami.Theme.disabledTextColor
                    border.width: 1
                    Rectangle {
                        width: parent.width * Math.min(root.sessionUsagePercent / 100, 1)
                        height: parent.height
                        radius: 5
                        color: getUsageColor(root.sessionUsagePercent)
                    }
                }

                PlasmaComponents.Label {
                    visible: root.sessionReset !== ""
                    text: i18n.tr("Resets at:") + " " + root.sessionReset + (root.sessionResetTime ? " (" + formatTimeRemaining(root.sessionResetTime) + ")" : "")
                    font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                    color: Kirigami.Theme.disabledTextColor
                }
            }

            // Weekly Usage
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                RowLayout {
                    Layout.fillWidth: true
                    PlasmaComponents.Label {
                        text: i18n.tr("Weekly (7day)")
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    PlasmaComponents.Label {
                        text: root.weeklyUsagePercent.toFixed(1) + "%"
                        color: getUsageColor(root.weeklyUsagePercent)
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 10
                    radius: 5
                    color: Kirigami.Theme.backgroundColor
                    border.color: Kirigami.Theme.disabledTextColor
                    border.width: 1
                    Rectangle {
                        width: parent.width * Math.min(root.weeklyUsagePercent / 100, 1)
                        height: parent.height
                        radius: 5
                        color: getUsageColor(root.weeklyUsagePercent)
                    }
                }

                PlasmaComponents.Label {
                    visible: root.weeklyReset !== ""
                    text: i18n.tr("Resets:") + " " + root.weeklyReset + (root.weeklyResetTime ? " (" + formatTimeRemaining(root.weeklyResetTime) + ")" : "")
                    font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                    color: Kirigami.Theme.disabledTextColor
                }
            }

            // Separator
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Kirigami.Theme.disabledTextColor
                opacity: 0.3
            }

            // Model breakdown
            PlasmaComponents.Label {
                text: i18n.tr("By Model (Weekly)")
                font.bold: true
                font.pixelSize: Kirigami.Theme.smallFont.pixelSize
            }

            // Fable
            RowLayout {
                Layout.fillWidth: true
                visible: root.fableWeeklyPercent > 0

                PlasmaComponents.Label {
                    text: i18n.tr("Fable")
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: 60
                    height: 8
                    radius: 3
                    color: Kirigami.Theme.backgroundColor
                    border.color: Kirigami.Theme.disabledTextColor
                    border.width: 1
                    Rectangle {
                        width: parent.width * Math.min(root.fableWeeklyPercent / 100, 1)
                        height: parent.height
                        radius: 3
                        color: getUsageColor(root.fableWeeklyPercent)
                    }
                }
                PlasmaComponents.Label {
                    text: root.fableWeeklyPercent.toFixed(0) + "%"
                    Layout.preferredWidth: 40
                    horizontalAlignment: Text.AlignRight
                }
            }

            // Sonnet
            RowLayout {
                Layout.fillWidth: true
                visible: root.sonnetWeeklyPercent > 0

                PlasmaComponents.Label {
                    text: i18n.tr("Sonnet")
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: 60
                    height: 8
                    radius: 3
                    color: Kirigami.Theme.backgroundColor
                    border.color: Kirigami.Theme.disabledTextColor
                    border.width: 1
                    Rectangle {
                        width: parent.width * Math.min(root.sonnetWeeklyPercent / 100, 1)
                        height: parent.height
                        radius: 3
                        color: getUsageColor(root.sonnetWeeklyPercent)
                    }
                }
                PlasmaComponents.Label {
                    text: root.sonnetWeeklyPercent.toFixed(0) + "%"
                    Layout.preferredWidth: 40
                    horizontalAlignment: Text.AlignRight
                }
            }

            // Opus
            RowLayout {
                Layout.fillWidth: true
                visible: root.opusWeeklyPercent > 0

                PlasmaComponents.Label {
                    text: i18n.tr("Opus")
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: 60
                    height: 8
                    radius: 3
                    color: Kirigami.Theme.backgroundColor
                    border.color: Kirigami.Theme.disabledTextColor
                    border.width: 1
                    Rectangle {
                        width: parent.width * Math.min(root.opusWeeklyPercent / 100, 1)
                        height: parent.height
                        radius: 3
                        color: getUsageColor(root.opusWeeklyPercent)
                    }
                }
                PlasmaComponents.Label {
                    text: root.opusWeeklyPercent.toFixed(0) + "%"
                    Layout.preferredWidth: 40
                    horizontalAlignment: Text.AlignRight
                }
            }

            // No model data message
            PlasmaComponents.Label {
                visible: root.fableWeeklyPercent === 0 && root.sonnetWeeklyPercent === 0 && root.opusWeeklyPercent === 0
                text: i18n.tr("No model breakdown available")
                font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                color: Kirigami.Theme.disabledTextColor
                font.italic: true
            }

            Item { Layout.fillHeight: true }

            // Footer
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Kirigami.Theme.disabledTextColor
                opacity: 0.3
            }

            RowLayout {
                Layout.fillWidth: true
                PlasmaComponents.Label {
                    text: root.lastUpdate !== "" ? i18n.tr("Updated:") + " " + root.lastUpdate : i18n.tr("Loading...")
                    font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                    color: Kirigami.Theme.disabledTextColor
                }
                Item { Layout.fillWidth: true }
                PlasmaComponents.Button {
                    icon.name: "view-refresh"
                    text: i18n.tr("Refresh")
                    onClicked: refresh()
                }
            }
        }
    }

    Timer {
        id: refreshTimer
        interval: (Plasmoid.configuration.refreshInterval || 1) * 60000
        running: true
        repeat: true
        onTriggered: loadCredentials()
    }

    function getUsageColor(percent) {
        if (percent < 50) return Kirigami.Theme.positiveTextColor
        if (percent < 80) return Kirigami.Theme.neutralTextColor
        return Kirigami.Theme.negativeTextColor
    }

    function formatTimeRemaining(resetTime) {
        if (!resetTime) return ""
        var now = new Date()
        var diff = resetTime.getTime() - now.getTime()
        if (diff <= 0) return ""

        var hours = Math.floor(diff / (1000 * 60 * 60))
        var minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

        if (hours > 24) {
            var days = Math.floor(hours / 24)
            hours = hours % 24
            return days + i18n.tr("d") + " " + hours + i18n.tr("h")
        } else if (hours > 0) {
            return hours + i18n.tr("h") + " " + minutes + i18n.tr("m")
        } else {
            return minutes + i18n.tr("m")
        }
    }

    Component.onCompleted: {
        console.log("Claude Usage: Widget loaded")
        loadCredentials()
    }

    Plasmoid.icon: "claude-usage"
    toolTipMainText: i18n.tr("Claude Usage")
    toolTipSubText: i18n.tr("Session (5hr)") + ": " + Math.round(root.sessionUsagePercent) + "% | " + i18n.tr("Weekly (7day)") + ": " + Math.round(root.weeklyUsagePercent) + "%"
}
